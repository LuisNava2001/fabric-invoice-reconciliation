"""Synthetic data: determinism, coverage of every scenario, contract shape, fictional content."""

import collections
import csv
import hashlib
import json
import random
from pathlib import Path

import pytest

from invoice_recon import generator
from invoice_recon.config import INVOICE_COLUMNS, LEDGER_COLUMNS, InputError, STATUSES, load_rules

# Byte-level fingerprint of generate(seed=4242, batches=1, invoices=100). It changes only if the
# generator changes; it must be identical across operating systems and Python versions.
EXPECTED_SMALL_DIGEST = "461655cbe02dc683a3c81ae0928fea6c10459f317446777dce2c1b0cefa54eff"


def _digest(root: Path) -> str:
    h = hashlib.sha256()
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        h.update(path.relative_to(root).as_posix().encode())
        h.update(path.read_bytes())
    return h.hexdigest()


def _truth(root: Path, batch: str) -> list[dict]:
    path = root / "Files" / "synthetic_ground_truth" / batch / "expected_outcomes.jsonl"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_same_seed_produces_identical_bytes(tmp_path):
    generator.generate(tmp_path / "a", invoices=300, batches=2)
    generator.generate(tmp_path / "b", invoices=300, batches=2)
    assert _digest(tmp_path / "a") == _digest(tmp_path / "b")


def test_different_seed_produces_different_data(tmp_path):
    generator.generate(tmp_path / "a", invoices=150, batches=1, seed=1)
    generator.generate(tmp_path / "b", invoices=150, batches=1, seed=2)
    assert _digest(tmp_path / "a") != _digest(tmp_path / "b")


def test_fingerprint_is_stable_across_platforms(tmp_path):
    generator.generate(tmp_path, invoices=100, batches=1)
    assert _digest(tmp_path) == EXPECTED_SMALL_DIGEST


@pytest.mark.parametrize("invoices", [100, 1000])
def test_every_scenario_is_present(tmp_path, invoices):
    generator.generate(tmp_path, invoices=invoices, batches=1)
    scenarios = {row["scenario"] for row in _truth(tmp_path, "batch-2026-03")}
    assert scenarios == set(generator.SCENARIO_NAMES)


def test_layout_manifest_and_ground_truth_cover_every_line(tmp_path):
    summaries = generator.generate(tmp_path, invoices=200, batches=2, start_period="2026-11")
    assert [s.batch_id for s in summaries] == ["batch-2026-11", "batch-2026-12"]
    batch = tmp_path / "Files" / "landing" / "batch-2026-12"
    manifest = json.loads((batch / "batch.json").read_text())
    assert manifest["reconciliation_period"] == "2026-12" and manifest["synthetic"] is True
    invoice_lines = (batch / "invoices.csv").read_text(encoding="utf-8").splitlines()
    ledger_lines = (batch / "ledger.jsonl").read_text(encoding="utf-8").splitlines()
    assert invoice_lines[0] == ",".join(INVOICE_COLUMNS)
    truth = _truth(tmp_path, "batch-2026-12")
    assert len(truth) == len(invoice_lines) - 1 + len(ledger_lines)
    keys = {(r["side"], r["line_number"]) for r in truth}
    assert keys == {("INVOICE", n) for n in range(2, len(invoice_lines) + 1)} | {("LEDGER", n) for n in range(1, len(ledger_lines) + 1)}
    assert {r["expected_status"] for r in truth} <= set(STATUSES)


def test_csv_and_jsonl_follow_the_contract_except_designed_malformed_rows(tmp_path):
    generator.generate(tmp_path, invoices=300, batches=1)
    batch = tmp_path / "Files" / "landing" / "batch-2026-03"
    truth = {(r["side"], r["line_number"]): r for r in _truth(tmp_path, "batch-2026-03")}
    with (batch / "invoices.csv").open(encoding="utf-8", newline="") as handle:
        for line, row in enumerate(csv.reader(handle), start=1):
            malformed = line > 1 and truth[("INVOICE", line)]["scenario"] == "malformed_invoice_row"
            assert (len(row) == len(INVOICE_COLUMNS)) != malformed
    for line, text in enumerate((batch / "ledger.jsonl").read_text(encoding="utf-8").splitlines(), start=1):
        malformed = truth[("LEDGER", line)]["scenario"] == "malformed_ledger_row"
        try:
            ok = sorted(json.loads(text)) == sorted(LEDGER_COLUMNS)
        except json.JSONDecodeError:
            ok = False
        assert ok != malformed, (line, text)
    first = json.loads((batch / "ledger.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert sorted(first) == sorted(LEDGER_COLUMNS), "first ledger record doubles as the schema probe"


def test_amounts_are_decimal_strings_and_some_json_numbers(tmp_path):
    generator.generate(tmp_path, invoices=500, batches=1)
    text = (tmp_path / "Files" / "landing" / "batch-2026-03" / "ledger.jsonl").read_text(encoding="utf-8")
    assert '"recorded_amount": "' in text  # quoted decimals
    numbers = [line for line in text.splitlines() if '"recorded_amount": ' in line and line.split('"recorded_amount": ')[1][0].isdigit()]
    assert numbers, "some amounts are written as bare JSON numbers"
    for line in numbers[:20]:
        literal = line.split('"recorded_amount": ')[1].split(",")[0]
        assert "e" not in literal.lower() and literal.count(".") <= 1


def test_similar_supplier_pairs_are_distinct_companies_above_threshold():
    rules = load_rules()
    suppliers = generator.make_suppliers(random.Random(generator.DEFAULT_SEED))
    pairs = [(s, s.sibling) for s in suppliers if s.sibling]
    assert pairs
    for base, sibling in pairs:
        assert base.supplier_id != sibling.supplier_id and base.prefix != sibling.prefix
        score = generator.similarity(generator.name_key(base.name, rules.legal_suffixes),
                                     generator.name_key(sibling.name, rules.legal_suffixes))
        assert score >= rules.name_similarity_threshold
    assert len({s.supplier_id for s in suppliers}) == len(suppliers)
    assert len({s.prefix for s in suppliers}) == len(suppliers)


def test_names_are_composed_from_invented_stems_only(tmp_path):
    suppliers = generator.make_suppliers(random.Random(7))
    for supplier in suppliers:
        stem = supplier.name.split(" ")[0]
        assert stem in generator.NAME_STEMS
    generator.generate(tmp_path, invoices=100, batches=1)
    text = "".join(p.read_text(encoding="utf-8") for p in tmp_path.rglob("*") if p.is_file()).lower()
    for forbidden in ("contoso", "northwind", "fabrikam", "@", "http"):  # well-known sample names, emails, URLs
        assert forbidden not in text


def test_scenario_mix_and_limits():
    counts = generator.scenario_counts(5000)
    assert counts["clean"] > 3000 and counts["only_ledger"] == 150
    assert all(counts[name] >= 1 for name in generator.SCENARIO_NAMES)
    with pytest.raises(InputError):
        generator.scenario_counts(40)


def test_refuses_to_overwrite_without_force(tmp_path):
    generator.generate(tmp_path, invoices=100, batches=1)
    with pytest.raises(InputError, match="already exists"):
        generator.generate(tmp_path, invoices=100, batches=1)
    generator.generate(tmp_path, invoices=100, batches=1, force=True)


@pytest.mark.parametrize("kwargs", [{"invoices": 99}, {"invoices": 300_000}, {"batches": 0}, {"batches": 13},
                                    {"start_period": "2026-13"}, {"start_period": "March"}])
def test_rejects_invalid_arguments(tmp_path, kwargs):
    with pytest.raises(InputError):
        generator.generate(tmp_path, **{"invoices": 100, "batches": 1, **kwargs})


def test_expected_outcomes_are_consistent(tmp_path):
    generator.generate(tmp_path, invoices=1000, batches=1)
    truth = _truth(tmp_path, "batch-2026-03")
    by_scenario = collections.defaultdict(set)
    for row in truth:
        by_scenario[row["scenario"]].add((row["side"], row["expected_status"]))
    assert by_scenario["clean"] == {("INVOICE", "MATCHED"), ("LEDGER", "MATCHED")}
    assert ("INVOICE", "DUPLICATE") in by_scenario["invoice_exact_duplicate"]
    assert ("INVOICE", "MATCHED") in by_scenario["invoice_exact_duplicate"]
    assert by_scenario["multiple_ledger_candidates"] == {("INVOICE", "AMBIGUOUS"), ("LEDGER", "AMBIGUOUS")}
    clean = [r for r in truth if r["scenario"] == "clean"]
    assert all(not r["expected_review"] and r["expected_flags"] == [] for r in clean)
    suggestions = (tmp_path / "Files/synthetic_ground_truth/batch-2026-03/expected_suggestions.jsonl").read_text().splitlines()
    criteria = {json.loads(s)["criterion"] for s in suggestions}
    assert criteria == {"SAME_REFERENCE_DIFFERENT_SUPPLIER", "SAME_SUPPLIER_AMOUNT_SIMILAR_REFERENCE"}
