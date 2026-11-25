"""Gold matching: rule R1, tolerances, currencies, NULLs, multiplicity, determinism, invariants."""

import random
from decimal import Decimal

import pytest
from pyspark.sql import functions as F

from invoice_recon import reconcile
from invoice_recon.config import STATUSES

from .helpers import BATCH, gold, silver_frames

pytestmark = pytest.mark.spark


def _silver(spark, rules, invoices, ledger):
    return silver_frames(spark, rules, invoices, ledger)


def _gold(spark, rules, invoices, ledger):
    """(status by (side, line), evidence rows, reconciliation DataFrame)."""
    return gold(spark, rules, invoices, ledger)[:3]


def test_exact_match_with_evidence(spark, rules):
    status, evidence, _ = _gold(spark, rules, [{}], [{}])
    inv, led = status[("INVOICE", 2)], status[("LEDGER", 1)]
    assert (inv.status, inv.reason_code, led.status) == ("MATCHED", "EXACT_AMOUNT", "MATCHED")
    assert (inv.counterpart_line_number, led.counterpart_line_number) == (1, 2)
    assert inv.counterpart_record_id == "GL-T-1" and led.counterpart_record_id == "EI-T-1"
    assert not inv.requires_review and inv.flags == []
    [row] = evidence
    assert row.rule_id == reconcile.RULE_ID and row.decision == "MATCHED"
    assert "supplier_id SUP-0001 on both sides" in row.explanation
    assert "normalize to AMC000100" in row.explanation and "tolerance 0.0100" in row.explanation


def test_reference_variant_matches_with_an_informational_flag(spark, rules):
    status, _, _ = _gold(spark, rules, [{}], [{"invoice_reference": "amc 000100"}])
    row = status[("INVOICE", 2)]
    assert row.status == "MATCHED" and row.flags == ["REFERENCE_FORMAT_VARIANT"] and not row.requires_review


@pytest.mark.parametrize("currency, invoice_total, ledger_amount, expected, flags", [
    ("USD", "116.00", "116.01", "MATCHED", ["ROUNDING_DIFFERENCE"]),
    ("USD", "116.00", "115.99", "MATCHED", ["ROUNDING_DIFFERENCE"]),
    ("USD", "116.00", "116.0101", "AMOUNT_MISMATCH", []),
    ("USD", "116.00", "116.02", "AMOUNT_MISMATCH", []),
    ("JPY", "1160", "1161", "MATCHED", ["ROUNDING_DIFFERENCE"]),
    ("JPY", "1160", "1162", "AMOUNT_MISMATCH", []),
])
def test_tolerance_is_inclusive_and_per_currency(spark, rules, currency, invoice_total, ledger_amount, expected, flags):
    subtotal = invoice_total
    status, evidence, _ = _gold(spark, rules,
                                [{"currency": currency, "subtotal": subtotal, "tax_amount": "0", "total_amount": invoice_total}],
                                [{"currency": currency, "recorded_amount": ledger_amount}])
    row = status[("INVOICE", 2)]
    assert row.status == expected and row.flags == flags
    assert row.amount_difference == abs(Decimal(invoice_total) - Decimal(ledger_amount))
    assert row.tolerance == rules.tolerance(currency)
    assert row.requires_review == (expected != "MATCHED")


def test_different_currencies_are_never_compared(spark, rules):
    status, evidence, _ = _gold(spark, rules, [{}], [{"currency": "MXN"}])
    row = status[("INVOICE", 2)]
    assert row.status == "CURRENCY_MISMATCH" and row.reason_code == "CURRENCY_DIFFERS_NO_CONVERSION"
    assert row.amount_difference is None and row.tolerance is None
    assert "amounts not compared" in evidence[0].explanation


def test_only_in_one_source_and_why(spark, rules):
    status, evidence, _ = _gold(
        spark, rules,
        [{"invoice_id": "EI-1", "invoice_reference": "AMC-1"}, {"invoice_id": "EI-2", "invoice_reference": "AMC-2"}],
        [{"transaction_id": "GL-1", "invoice_reference": "AMC-3"},
         {"transaction_id": "GL-2", "invoice_reference": "AMC-2", "posting_date": "2026-02-30"}])
    assert status[("INVOICE", 2)].status == "ONLY_IN_INVOICES" and status[("INVOICE", 2)].reason_code == "NO_COUNTERPART"
    assert status[("INVOICE", 3)].reason_code == "COUNTERPART_NOT_ELIGIBLE", "the ledger row for AMC-2 is invalid"
    assert status[("LEDGER", 1)].status == "ONLY_IN_LEDGER"
    assert status[("LEDGER", 2)].status == "INVALID_RECORD" and status[("LEDGER", 2)].reason_code == "INVALID_DATE"
    assert evidence == []


def test_two_nulls_never_match(spark, rules):
    """Records without supplier or reference on both sides must not pair up on NULL = NULL."""
    status, evidence, reconciliation = _gold(
        spark, rules,
        [{"invoice_id": "EI-1", "invoice_reference": None}, {"invoice_id": "EI-2", "supplier_id": None},
         {"invoice_id": "EI-3", "supplier_id": None, "invoice_reference": None}],
        [{"transaction_id": "GL-1", "invoice_reference": None}, {"transaction_id": "GL-2", "supplier_id": None},
         {"transaction_id": "GL-3", "supplier_id": None, "invoice_reference": None}])
    assert {r.status for r in status.values()} == {"INVALID_RECORD"}
    assert evidence == [] and reconciliation.filter(F.col("match_key").isNotNull()).count() == 0


def test_null_ids_with_valid_keys_still_do_not_match(spark, rules):
    status, _, _ = _gold(spark, rules, [{"invoice_id": None}], [{"transaction_id": None}])
    assert status[("INVOICE", 2)].status == status[("LEDGER", 1)].status == "INVALID_RECORD"


def test_multiple_candidates_are_ambiguous_and_listed(spark, rules):
    status, evidence, _ = _gold(spark, rules, [{"invoice_id": "EI-1"}, {"invoice_id": "EI-2"}],
                                [{"transaction_id": "GL-1"}, {"transaction_id": "GL-2"}])
    assert {r.status for r in status.values()} == {"AMBIGUOUS"}
    assert {r.reason_code for r in status.values()} == {"MULTIPLE_CANDIDATES_BOTH_SIDES"}
    assert len(evidence) == 4 and {e.decision for e in evidence} == {"NOT_DECIDED_MULTIPLE_CANDIDATES"}
    assert all(r.requires_review and r.counterpart_line_number is None for r in status.values())


def test_one_invoice_two_postings_is_a_possible_double_posting(spark, rules):
    status, evidence, _ = _gold(spark, rules, [{}], [{"transaction_id": "GL-1"}, {"transaction_id": "GL-2"}])
    assert status[("INVOICE", 2)].status == "AMBIGUOUS"
    assert status[("INVOICE", 2)].reason_code == "MULTIPLE_LEDGER_ENTRIES_FOR_KEY"
    assert status[("INVOICE", 2)].candidates_on_other_side == 2 and len(evidence) == 2


def test_duplicates_do_not_multiply_matches(spark, rules):
    status, evidence, _ = _gold(spark, rules, [{}, {}, {}], [{}, {}])
    statuses = sorted((k, r.status) for k, r in status.items())
    assert statuses == [(("INVOICE", 2), "MATCHED"), (("INVOICE", 3), "DUPLICATE"), (("INVOICE", 4), "DUPLICATE"),
                        (("LEDGER", 1), "MATCHED"), (("LEDGER", 2), "DUPLICATE")]
    assert len(evidence) == 1


def test_conflicting_duplicates_block_the_match(spark, rules):
    status, evidence, _ = _gold(spark, rules, [{}, {"subtotal": "50.00", "tax_amount": "0", "total_amount": "50.00"}], [{}])
    assert [status[("INVOICE", i)].reason_code for i in (2, 3)] == ["DUPLICATE_CONFLICT"] * 2
    assert status[("LEDGER", 1)].status == "ONLY_IN_LEDGER"
    assert status[("LEDGER", 1)].reason_code == "COUNTERPART_NOT_ELIGIBLE" and evidence == []


def test_review_flags_send_matches_to_review(spark, rules):
    status, _, reconciliation, inv, led = gold(spark, rules, [{}], [{"posting_date": "04/03/2026"}])
    row = status[("INVOICE", 2)]
    assert row.status == "MATCHED" and row.flags == ["AMBIGUOUS_DATE"] and row.requires_review
    suggestions = reconcile.build_suggestions(reconciliation, inv, led, rules, BATCH)
    exceptions = reconcile.build_exceptions(reconciliation, suggestions).collect()
    assert {e.priority for e in exceptions} == {"LOW"} and "AMBIGUOUS_DATE" in exceptions[0].recommended_action


def test_key_classes_partition_every_key_once(spark, rules):
    invoices = [{"invoice_id": f"EI-{i}", "invoice_reference": f"R-{i % 7}"} for i in range(20)]
    ledger = [{"transaction_id": f"GL-{i}", "invoice_reference": f"R-{i % 9}"} for i in range(15)]
    inv, led = _silver(spark, rules, invoices, ledger)
    keys = reconcile.classify_keys(inv, led).collect()
    assert len(keys) == len({k.match_key for k in keys}) == len({f"R{i}" for i in range(9)})
    assert sum(k.n_inv for k in keys) == 20 and sum(k.n_led for k in keys) == 15
    for k in keys:
        expected = ("PAIR" if (k.n_inv, k.n_led) == (1, 1) else "AMBIGUOUS" if max(k.n_inv, k.n_led) > 1
                    else "ONLY_IN_INVOICES" if k.n_led == 0 else "ONLY_IN_LEDGER")
        assert k.key_class == expected


def test_results_do_not_depend_on_input_order(spark, rules):
    invoices = [{"invoice_id": f"EI-{i}", "invoice_reference": f"R-{i % 11}", "_line_number": i + 2} for i in range(40)]
    ledger = [{"transaction_id": f"GL-{i}", "invoice_reference": f"R-{i % 13}", "_line_number": i + 1} for i in range(30)]
    def snapshot(result):
        _, evidence, reconciliation = result
        return sorted(map(tuple, reconciliation.collect())), sorted(map(tuple, evidence))

    first = snapshot(_gold(spark, rules, invoices, ledger))
    shuffled_inv, shuffled_led = list(invoices), list(ledger)
    random.Random(3).shuffle(shuffled_inv)
    random.Random(4).shuffle(shuffled_led)
    assert snapshot(_gold(spark, rules, shuffled_inv, shuffled_led)) == first


@pytest.mark.parametrize("seed", [11, 29])
def test_invariants_hold_on_random_collisions(spark, rules, seed):
    """Random records with many shared keys, NULLs, duplicates and mixed currencies."""
    rng = random.Random(seed)

    def pick(options):
        return rng.choice(options)

    invoices = [{"invoice_id": pick([f"EI-{rng.randrange(60)}", None]), "supplier_id": pick(["SUP-0001", "SUP-0002", None]),
                 "invoice_reference": pick([f"R-{rng.randrange(25)}", None]), "currency": pick(["USD", "USD", "EUR"]),
                 "subtotal": "100.00", "tax_amount": "0", "total_amount": "100.00"} for _ in range(120)]
    ledger = [{"transaction_id": pick([f"GL-{rng.randrange(60)}", None]), "supplier_id": pick(["SUP-0001", "SUP-0002", None]),
               "invoice_reference": pick([f"R-{rng.randrange(25)}", None]), "currency": pick(["USD", "USD", "EUR"]),
               "recorded_amount": pick(["100.00", "100.01", "100.50"])} for _ in range(120)]
    status, evidence, _ = _gold(spark, rules, invoices, ledger)
    assert len(status) == 240, "one status per record"
    assert {r.status for r in status.values()} <= set(STATUSES)
    matched = [e for e in evidence if e.decision == "MATCHED"]
    assert len({e.invoice_line for e in matched}) == len({e.ledger_line for e in matched}) == len(matched)
    assert sum(1 for (side, _), r in status.items() if side == "INVOICE" and r.status == "MATCHED") == len(matched)
    assert sum(1 for (side, _), r in status.items() if side == "LEDGER" and r.status == "MATCHED") == len(matched)
    for e in matched:
        assert e.invoice_currency == e.ledger_currency and e.amount_difference <= e.tolerance
        assert e.invoice_candidates == e.ledger_candidates == 1
    for r in status.values():
        if r.status == "MATCHED":
            assert r.match_key is not None and r.record_id is not None
        if r.status in ("MATCHED", "AMOUNT_MISMATCH", "CURRENCY_MISMATCH"):
            other = status[("LEDGER" if r.side == "INVOICE" else "INVOICE", r.counterpart_line_number)]
            assert other.counterpart_line_number == r.line_number and other.status == r.status
