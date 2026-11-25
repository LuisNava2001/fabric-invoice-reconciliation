"""Rules loading, identifiers that reach paths and predicates, lakehouse layout, catalogs."""

import json
from decimal import Decimal

import pytest

from invoice_recon import dq
from invoice_recon.config import (
    BATCH_TABLES,
    SOURCE_INVOICES,
    SOURCE_LEDGER,
    InputError,
    Lakehouse,
    load_rules,
    shift_period,
    validate_batch_id,
    validate_period,
)
from invoice_recon.schemas import TABLE_SCHEMAS


def test_default_rules_are_decimal_and_documented():
    rules = load_rules()
    assert rules.tolerance("USD") == Decimal("0.01")
    assert rules.tolerance("JPY") == Decimal("1")
    assert isinstance(rules.amount_max, Decimal) and rules.amount_max == Decimal("10000000")
    assert set(rules.currencies) == {"USD", "EUR", "MXN", "CAD", "JPY"}
    assert rules.max_suggestions_per_record >= 1


@pytest.mark.parametrize("change, message", [
    (lambda r: r["currencies"].update({"usd": {"minor_units": 2, "tolerance": "0.01"}}), "currency code"),
    (lambda r: r["currencies"]["USD"].update({"tolerance": "-0.01"}), "tolerance"),
    (lambda r: r["currencies"]["USD"].update({"tolerance": "abc"}), "not a decimal"),
    (lambda r: r["currencies"]["USD"].update({"tolerance": "0.00001"}), "tolerance"),
    (lambda r: r["currencies"]["USD"].update({"minor_units": 9}), "minor_units"),
    (lambda r: r.update({"amount_max": "0"}), "amount_max"),
    (lambda r: r["fuzzy"].update({"name_similarity_threshold": "1.5"}), "name_similarity_threshold"),
    (lambda r: r.update({"rules_version": ""}), "rules_version"),
])
def test_invalid_rules_are_rejected(tmp_path, change, message):
    raw = json.loads(_default_rules_path().read_text(encoding="utf-8"))
    change(raw)
    path = tmp_path / "rules.json"
    path.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(InputError, match=message):
        load_rules(path)


def _default_rules_path():
    from importlib import resources

    return resources.files("invoice_recon").joinpath("data/reconciliation_rules.json")


@pytest.mark.parametrize("batch_id", ["batch-2026-03", "B1", "a.b_c-d"])
def test_valid_batch_ids(batch_id):
    assert validate_batch_id(batch_id) == batch_id


@pytest.mark.parametrize("batch_id", ["", "x' OR '1'='1", "../etc", "a/b", "a b", "-lead", "x" * 65, None, 7])
def test_batch_ids_that_could_escape_paths_or_predicates_are_rejected(batch_id):
    with pytest.raises(InputError):
        validate_batch_id(batch_id)


def test_periods():
    assert validate_period("2026-03") == "2026-03"
    assert shift_period("2026-01", -1) == "2025-12"
    assert shift_period("2026-12", 1) == "2027-01"
    for bad in ("2026-3", "2026-13", "2026-00", "202603", None):
        with pytest.raises(InputError):
            validate_period(bad)


def test_lakehouse_layout_local_and_fabric_relative(tmp_path):
    local = Lakehouse.local(tmp_path)
    assert local.table("gold_reconciliation").endswith("/Tables/gold_reconciliation")
    assert local.landing("batch-1").endswith("/Files/landing/batch-1")
    fabric = Lakehouse("")
    assert fabric.table("silver_ledger") == "Tables/silver_ledger"
    assert fabric.landing_root() == "Files/landing"
    assert Lakehouse.relative_landing_file("b1", "x.csv") == "Files/landing/b1/x.csv"
    with pytest.raises(KeyError):
        local.table("not_a_table")
    with pytest.raises(InputError):
        local.landing("../outside")


def test_every_table_has_an_explicit_schema_and_batch_tables_are_partitionable():
    assert set(TABLE_SCHEMAS) == set(BATCH_TABLES) | {"ops_batch_runs"}
    for name in BATCH_TABLES:
        assert TABLE_SCHEMAS[name].fieldNames()[0] == "_batch_id", name


def test_dq_catalog_is_unique_per_source():
    for source in (SOURCE_INVOICES, SOURCE_LEDGER):
        ids = dq.rule_ids(source)
        assert len(ids) == len(set(ids))
        assert "MALFORMED_ROW" in ids and "DUPLICATE_CONFLICT" in ids
    assert "AMBIGUOUS_DATE" in dq.rule_ids(SOURCE_LEDGER, dq.WARNING)
    assert "TOTAL_INCONSISTENT" in dq.rule_ids(SOURCE_INVOICES, dq.ERROR)
