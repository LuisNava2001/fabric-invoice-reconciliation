"""Silver: normalization, safe conversions, date handling without guessing, DQ rules, duplicates."""

import datetime as dt
from decimal import Decimal

import pytest
from pyspark.sql import functions as F

from invoice_recon import dq, silver
from invoice_recon.config import SOURCE_INVOICES, SOURCE_LEDGER

from .helpers import BATCH, PERIOD, bronze_invoices, bronze_ledger, by_line

pytestmark = pytest.mark.spark


def _invoices(spark, rules, rows):
    return by_line(silver.normalize_invoices(bronze_invoices(spark, rows), rules, PERIOD))


def _ledger(spark, rules, rows):
    return by_line(silver.normalize_ledger(bronze_ledger(spark, rows), rules, PERIOD))


def test_identifier_and_text_normalization(spark, rules):
    rows = _invoices(spark, rules, [
        {"invoice_id": " ei-7 ", "supplier_id": "sup0001", "supplier_name": "Amberlyn  Castings\tLtd",
         "invoice_reference": " amc/000100​ ", "currency": " usd"},
        {"invoice_id": "EI-8", "supplier_id": "SUP-0001 ", "invoice_reference": "AMC 000100"},
        {"invoice_id": "EI-9", "supplier_id": "SUPPLIER-1", "invoice_reference": "---"},
        {"invoice_id": "   ", "supplier_id": "", "invoice_reference": None},
    ])
    first = rows[2]
    assert (first.invoice_id, first.supplier_id, first.currency) == ("EI-7", "SUP-0001", "USD")
    assert first.supplier_name == "Amberlyn Castings Ltd" and first.supplier_name_key == "AMBERLYN CASTINGS"
    assert first.invoice_reference == "amc/000100" and first.reference_key == "AMC000100"
    assert first.match_key == "SUP-0001|AMC000100" and first.record_status == "VALID"
    assert rows[3].match_key == first.match_key, "format variants share one key"
    assert rows[4].dq_errors == ["MALFORMED_SUPPLIER_ID", "MISSING_REFERENCE"] and rows[4].match_key is None
    assert rows[5].dq_errors[:3] == ["MISSING_INVOICE_ID", "MISSING_SUPPLIER_ID", "MISSING_REFERENCE"]
    assert rows[5].status_reason == "MISSING_INVOICE_ID", "reason is the highest-priority error"


def test_amounts_are_exact_decimals_with_strict_formats(spark, rules):
    cases = {
        2: ("1234.5678", "0", "1234.5678", Decimal("1234.5678"), []),
        3: ("1,234.50", "0", "1,234.50", Decimal("1234.50"), []),
        4: ("0.10", "0.20", "0.30", Decimal("0.10"), []),  # 0.1 + 0.2 == 0.3 exactly: no float involved
        5: ("12O5.00", "0", "1205.00", None, ["INVALID_AMOUNT"]),
        6: ("1,23.00", "0", "123.00", None, ["INVALID_AMOUNT"]),
        7: ("1.23456", "0", "1.23456", None, ["INVALID_AMOUNT"]),
        8: ("100.00", "16.00", "", Decimal("100.00"), ["MISSING_AMOUNT"]),
        9: ("-100.00", "0", "-100.00", Decimal("-100.00"), ["AMOUNT_OUT_OF_RANGE"]),
        10: ("20000000.00", "0", "20000000.00", Decimal("20000000.00"), ["AMOUNT_OUT_OF_RANGE"]),
        11: ("1e3", "0", "1000", None, ["INVALID_AMOUNT"]),
    }
    rows = _invoices(spark, rules, [{"_line_number": line, "invoice_id": f"EI-{line}", "subtotal": s, "tax_amount": t,
                                     "total_amount": total} for line, (s, t, total, _, _) in cases.items()])
    for line, (_, _, _, subtotal, errors) in cases.items():
        assert rows[line].subtotal == subtotal, line
        assert rows[line].dq_errors == errors, (line, rows[line].dq_errors)


def test_total_consistency_uses_the_currency_tolerance(spark, rules):
    rows = _invoices(spark, rules, [
        {"invoice_id": "EI-1", "subtotal": "100.00", "tax_amount": "16.00", "total_amount": "116.01"},
        {"invoice_id": "EI-2", "subtotal": "100.00", "tax_amount": "16.00", "total_amount": "116.0101"},
        {"invoice_id": "EI-3", "currency": "JPY", "subtotal": "1000", "tax_amount": "80", "total_amount": "1081"},
        {"invoice_id": "EI-4", "currency": "JPY", "subtotal": "1000", "tax_amount": "80", "total_amount": "1082"},
        {"invoice_id": "EI-5", "currency": "US$", "total_amount": "999.00"},
    ])
    assert rows[2].dq_errors == [] and rows[3].dq_errors == ["TOTAL_INCONSISTENT"]
    assert rows[4].dq_errors == [] and rows[5].dq_errors == ["TOTAL_INCONSISTENT"]
    assert rows[6].dq_errors == ["INVALID_CURRENCY"], "no tolerance to apply without a valid currency"


def test_invoice_dates_must_be_iso_calendar_dates(spark, rules):
    rows = _invoices(spark, rules, [{"invoice_id": f"EI-{i}", "invoice_date": d} for i, d in enumerate(
        ["2026-03-04", "2026-02-30", "2026-13-01", "04/03/2026", "", "2026-02-11"])])
    assert rows[2].invoice_date == dt.date(2026, 3, 4) and rows[2].dq_warnings == []
    assert [rows[i].dq_errors for i in (3, 4, 5)] == [["INVALID_DATE"]] * 3
    assert rows[6].dq_errors == ["MISSING_DATE"]
    assert rows[7].dq_warnings == ["OUT_OF_PERIOD"] and rows[7].record_status == "VALID"


@pytest.mark.parametrize("text, value, basis, candidates, errors, warnings", [
    ("2026-03-04", dt.date(2026, 3, 4), "YYYY-MM-DD", None, [], []),
    ("2026/03/04", dt.date(2026, 3, 4), "YYYY/MM/DD", None, [], []),
    ("04-MAR-2026", dt.date(2026, 3, 4), "D-MON-YYYY", None, [], []),
    ("4-mar-2026", dt.date(2026, 3, 4), "D-MON-YYYY", None, [], []),
    ("14/03/2026", dt.date(2026, 3, 14), "D/M/YYYY_ONLY_VALID_READING", None, [], []),
    ("03/14/2026", dt.date(2026, 3, 14), "M/D/YYYY_ONLY_VALID_READING", None, [], []),
    ("03/03/2026", dt.date(2026, 3, 3), "D/M_EQUALS_M/D", None, [], []),
    ("04/03/2026", None, "AMBIGUOUS_D/M_OR_M/D", [dt.date(2026, 3, 4), dt.date(2026, 4, 3)], [], ["AMBIGUOUS_DATE"]),
    ("31/02/2026", None, None, None, ["INVALID_DATE"], []),
    ("2026-02-30", None, None, None, ["INVALID_DATE"], []),
    ("March 4, 2026", None, None, None, ["INVALID_DATE"], []),
    (None, None, None, None, ["MISSING_DATE"], []),
])
def test_posting_dates_are_validated_not_guessed(spark, rules, text, value, basis, candidates, errors, warnings):
    row = _ledger(spark, rules, [{"posting_date": text}])[1]
    assert (row.posting_date, row.posting_date_basis, row.posting_date_candidates) == (value, basis, candidates)
    assert row.dq_errors == errors and row.dq_warnings == warnings


def test_accounting_periods_and_period_warnings(spark, rules):
    rows = _ledger(spark, rules, [{"transaction_id": f"GL-{i}", "accounting_period": p, "posting_date": d} for i, (p, d) in enumerate([
        ("2026-03", "2026-03-10"), ("202603", "2026-03-10"), ("2026-3", "2026-03-10"), ("2026-13", "2026-03-10"),
        ("2026/03", "2026-03-10"), ("", "2026-03-10"), ("2026-02", "2026-03-10"), ("2026-02", "2026-02-27")])])
    assert [rows[i].accounting_period for i in (1, 2, 3)] == ["2026-03"] * 3
    assert rows[4].dq_errors == ["INVALID_PERIOD"] and rows[5].dq_errors == ["INVALID_PERIOD"]
    assert rows[6].dq_errors == ["MISSING_PERIOD"]
    assert rows[7].dq_warnings == ["PERIOD_INCONSISTENT", "OUT_OF_PERIOD"] and rows[7].record_status == "VALID"
    assert rows[8].dq_warnings == ["OUT_OF_PERIOD"]


def test_payment_status_and_currency_on_ledger(spark, rules):
    rows = _ledger(spark, rules, [{"transaction_id": "GL-1", "payment_status": " paid "},
                                  {"transaction_id": "GL-2", "payment_status": "REVERSED"},
                                  {"transaction_id": "GL-3", "payment_status": None},
                                  {"transaction_id": "GL-4", "currency": "EURO"}])
    assert rows[1].payment_status == "PAID" and rows[1].dq_warnings == []
    assert rows[2].dq_warnings == ["UNKNOWN_PAYMENT_STATUS"] and rows[3].dq_warnings == ["MISSING_PAYMENT_STATUS"]
    assert rows[4].dq_errors == ["INVALID_CURRENCY"]


def test_duplicates_exact_conflicting_and_null_ids(spark, rules):
    rows = _invoices(spark, rules, [
        {"_line_number": 10, "invoice_id": "EI-1"},
        {"_line_number": 4, "invoice_id": "ei-1 ", "supplier_name": "Amberlyn  Castings Ltd"},  # same after normalization
        {"_line_number": 12, "invoice_id": "EI-1"},
        {"_line_number": 5, "invoice_id": "EI-2", "total_amount": "116.00"},
        {"_line_number": 6, "invoice_id": "EI-2", "subtotal": "200.00", "tax_amount": "32.00", "total_amount": "232.00"},
        {"_line_number": 7, "invoice_id": "", "invoice_reference": "A-1"},
        {"_line_number": 8, "invoice_id": "", "invoice_reference": "A-1"},
        {"_line_number": 9, "invoice_id": "EI-3", "_parse_error": "MALFORMED_ROW: x"},
        {"_line_number": 11, "invoice_id": "EI-3", "_parse_error": "MALFORMED_ROW: x"},
    ])
    assert rows[4].record_status == "VALID" and rows[4].duplicate_type == "EXACT"
    assert [(rows[i].record_status, rows[i].duplicate_of_line) for i in (10, 12)] == [("DUPLICATE", 4)] * 2
    assert rows[10].status_reason == "DUPLICATE_EXACT"
    assert [rows[i].status_reason for i in (5, 6)] == ["DUPLICATE_CONFLICT"] * 2
    assert [rows[i].record_status for i in (7, 8)] == ["INVALID"] * 2, "NULL IDs are never grouped"
    assert rows[7].duplicate_group_size is None
    assert [rows[i].status_reason for i in (9, 11)] == ["MALFORMED_ROW"] * 2


def test_invalid_beats_duplicate(spark, rules):
    rows = _ledger(spark, rules, [{"transaction_id": "GL-1", "currency": "XXX"}, {"transaction_id": "GL-1"}])
    assert rows[1].record_status == "INVALID" and rows[2].record_status == "DUPLICATE"
    assert rows[2].status_reason == "DUPLICATE_CONFLICT"


def test_malformed_rows_only_report_malformed(spark, rules):
    rows = _ledger(spark, rules, [{"transaction_id": None, "supplier_id": None, "_parse_error": "MALFORMED_ROW: y"}])
    assert rows[1].dq_errors == ["MALFORMED_ROW"] and rows[1].dq_warnings == [] and rows[1].match_key is None


def test_no_row_is_filtered_and_quarantine_keeps_raw_lines(spark, rules):
    inv = silver.normalize_invoices(bronze_invoices(spark, [{"invoice_id": f"EI-{i}", "currency": "X" if i % 3 == 0 else "USD"}
                                                            for i in range(30)]), rules, PERIOD)
    led = silver.normalize_ledger(bronze_ledger(spark, [{"transaction_id": "GL-1"}, {"transaction_id": "GL-1"}]), rules, PERIOD)
    assert inv.count() == 30 and led.count() == 2
    q = silver.quarantine(inv, led).collect()
    assert len(q) == 10 + 1
    assert all(r.status_reason and r._raw_line for r in q)


def test_dq_metrics_report_every_rule_including_zero(spark, rules):
    inv = silver.normalize_invoices(bronze_invoices(spark, [{"invoice_id": "EI-1"}, {"invoice_id": "EI-2", "currency": "BAD"},
                                                            {"invoice_id": "EI-2", "currency": "BAD"}]), rules, PERIOD)
    metrics = {r.rule_id: r for r in silver.dq_metrics(spark, inv, SOURCE_INVOICES, BATCH).collect()}
    assert set(metrics) == set(dq.rule_ids(SOURCE_INVOICES))
    assert metrics["INVALID_CURRENCY"].failed_records == 2 and metrics["INVALID_CURRENCY"].total_records == 3
    assert metrics["INVALID_CURRENCY"].failure_rate == Decimal("0.6667")
    assert metrics["MISSING_INVOICE_ID"].failed_records == 0


def test_generated_data_emits_only_catalog_codes(spark, pipeline_run):
    for table, source in (("silver_invoices", SOURCE_INVOICES), ("silver_ledger", SOURCE_LEDGER)):
        df = spark.read.format("delta").load(pipeline_run.lakehouse.table(table))
        codes = {r.code for r in df.select(F.explode(F.array_union("dq_errors", "dq_warnings")).alias("code")).distinct().collect()}
        assert codes and codes <= set(dq.rule_ids(source)), codes - set(dq.rule_ids(source))
