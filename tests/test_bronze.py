"""Bronze: raw strings with lineage, line numbers, malformed rows kept, schema checks."""

import json

import pytest
from pyspark.sql import functions as F

from invoice_recon import bronze
from invoice_recon.config import INVOICE_COLUMNS, InputError, Lakehouse

pytestmark = pytest.mark.spark

BATCH = "batch-unit"


def _landing(tmp_path, invoices: str | None = None, ledger: str | None = None, manifest: dict | None = None):
    lakehouse = Lakehouse.local(tmp_path)
    folder = tmp_path / "Files" / "landing" / BATCH
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "batch.json").write_text(json.dumps(manifest or {
        "batch_id": BATCH, "reconciliation_period": "2026-03",
        "sources": {"E_INVOICES": "invoices.csv", "ERP_LEDGER": "ledger.jsonl"}}), encoding="utf-8")
    if invoices is not None:
        (folder / "invoices.csv").write_bytes(invoices.encode("utf-8"))
    if ledger is not None:
        (folder / "ledger.jsonl").write_bytes(ledger.encode("utf-8"))
    return lakehouse


HEADER = ",".join(INVOICE_COLUMNS)
GOOD = 'EI-1,SUP-0001,"Halvorne Tooling, Inc",2026-03-02,USD,100.00,16.00,116.00,HAT-000001'


def _ledger_line(**overrides):
    values = {"transaction_id": "GL-1", "invoice_reference": "HAT-000001", "supplier_id": "SUP-0001",
              "supplier_name": "Halvorne Tooling, Inc", "posting_date": "2026-03-03", "currency": "USD",
              "recorded_amount": "116.00", "payment_status": "OPEN", "accounting_period": "2026-03"}
    values.update(overrides)
    return json.dumps(values)


def test_csv_rows_keep_raw_text_line_numbers_and_quoted_commas(spark, tmp_path):
    text = "\r\n".join([HEADER, GOOD, "", "  ei-2 ,sup0001, x ,2026-03-05,usd, 5 ,0,5,  ref-2", "EI-3,SUP-0001,short"]) + "\r\n"
    lakehouse = _landing(tmp_path, invoices=text)
    df, errors, problem = bronze.ingest_invoices(spark, lakehouse, BATCH, "invoices.csv")
    assert problem is None
    rows = {r._line_number: r for r in df.collect()}
    assert sorted(rows) == [2, 4, 5], "blank line 3 is not a record"
    assert rows[2].supplier_name == "Halvorne Tooling, Inc" and rows[2]._parse_error is None
    assert rows[4].invoice_id == "  ei-2 " and rows[4].currency == "usd", "Bronze keeps original values"
    assert rows[4]._raw_line.startswith("  ei-2 ") and not rows[4]._raw_line.endswith("\r")
    assert rows[5]._parse_error.startswith("MALFORMED_ROW") and rows[5].invoice_id is None
    assert rows[5]._raw_line == "EI-3,SUP-0001,short"
    assert rows[2]._source_file == f"Files/landing/{BATCH}/invoices.csv" and len(rows[2]._record_hash) == 64
    logged = {(r._line_number, r.error_type) for r in errors.collect()}
    assert logged == {(3, "BLANK_LINE"), (5, "MALFORMED_ROW")}


def test_csv_with_too_many_fields_is_malformed_not_truncated(spark, tmp_path):
    lakehouse = _landing(tmp_path, invoices=f"{HEADER}\n{GOOD},EXTRA\n")
    df, _, _ = bronze.ingest_invoices(spark, lakehouse, BATCH, "invoices.csv")
    row = df.collect()[0]
    assert row._parse_error and row.invoice_reference is None


@pytest.mark.parametrize("header", [
    HEADER.replace("total_amount", "total"),
    ",".join(reversed(INVOICE_COLUMNS)),
    ",".join(INVOICE_COLUMNS[:-1]),
])
def test_csv_header_must_match_the_contract(spark, tmp_path, header):
    lakehouse = _landing(tmp_path, invoices=f"{header}\n{GOOD}\n")
    df, errors, problem = bronze.ingest_invoices(spark, lakehouse, BATCH, "invoices.csv")
    assert df is None and "differs from contract" in problem
    error = errors.collect()[0]
    assert error.error_type == "SCHEMA_MISMATCH" and error._raw_line == header


def test_csv_header_with_bom_is_accepted(spark, tmp_path):
    lakehouse = _landing(tmp_path, invoices=f"﻿{HEADER}\n{GOOD}\n")
    assert bronze.ingest_invoices(spark, lakehouse, BATCH, "invoices.csv")[2] is None


def test_json_rows_malformed_and_schema_drift_are_kept(spark, tmp_path):
    lines = [
        _ledger_line(),
        '{"transaction_id": "GL-2", "invoice_reference": "HAT-0',
        _ledger_line(transaction_id="GL-3").replace('"recorded_amount"', '"amount"'),
        "[1, 2]",
        _ledger_line(transaction_id="GL-5")[:-1] + ', "extra": 1}',
        _ledger_line(transaction_id="GL-6"),
    ]
    lakehouse = _landing(tmp_path, ledger="\n".join(lines) + "\n")
    df, errors, problem = bronze.ingest_ledger(spark, lakehouse, BATCH, "ledger.jsonl")
    assert problem is None
    rows = {r._line_number: r for r in df.collect()}
    assert rows[1]._parse_error is None and rows[6]._parse_error is None
    assert rows[2]._parse_error.startswith("MALFORMED_ROW")
    assert rows[3]._parse_error.startswith("SCHEMA_DRIFT") and rows[3].transaction_id is None
    assert rows[4]._parse_error.startswith("MALFORMED_ROW")
    assert rows[5]._parse_error.startswith("SCHEMA_DRIFT")
    assert {(r._line_number, r.error_type) for r in errors.collect()} == {
        (2, "MALFORMED_ROW"), (3, "SCHEMA_DRIFT"), (4, "MALFORMED_ROW"), (5, "SCHEMA_DRIFT")}


def test_numeric_json_amounts_keep_their_literal_text(spark, tmp_path):
    lines = [_ledger_line(), _ledger_line(transaction_id="GL-2").replace('"116.00"', "1234.10"),
             _ledger_line(transaction_id="GL-3").replace('"116.00"', "12345678901.2345")]
    lakehouse = _landing(tmp_path, ledger="\n".join(lines))
    df, _, _ = bronze.ingest_ledger(spark, lakehouse, BATCH, "ledger.jsonl")
    amounts = {r._line_number: r.recorded_amount for r in df.collect()}
    assert amounts == {1: "116.00", 2: "1234.10", 3: "12345678901.2345"}, "no trip through a double"


def test_json_first_record_must_match_the_contract(spark, tmp_path):
    lakehouse = _landing(tmp_path, ledger=_ledger_line().replace('"payment_status"', '"status"') + "\n" + _ledger_line())
    df, errors, problem = bronze.ingest_ledger(spark, lakehouse, BATCH, "ledger.jsonl")
    assert df is None and "differ from contract" in problem
    assert errors.collect()[0].error_type == "SCHEMA_MISMATCH"


def test_missing_file_and_empty_file(spark, tmp_path):
    lakehouse = _landing(tmp_path, invoices="")
    with pytest.raises(InputError, match="not found"):
        bronze.ingest_ledger(spark, lakehouse, BATCH, "ledger.jsonl")
    assert bronze.ingest_invoices(spark, lakehouse, BATCH, "invoices.csv")[2] == "file is empty (no header)"


@pytest.mark.parametrize("manifest, message", [
    ({"batch_id": "other", "reconciliation_period": "2026-03", "sources": {"E_INVOICES": "a", "ERP_LEDGER": "b"}}, "does not declare"),
    ({"batch_id": BATCH, "reconciliation_period": "03/2026", "sources": {"E_INVOICES": "a", "ERP_LEDGER": "b"}}, "invalid period"),
    ({"batch_id": BATCH, "reconciliation_period": "2026-03", "sources": {"E_INVOICES": "a"}}, "exactly the sources"),
    ({"batch_id": BATCH, "reconciliation_period": "2026-03", "sources": {"E_INVOICES": "../x", "ERP_LEDGER": "b"}}, "invalid source file"),
])
def test_manifest_is_validated(spark, tmp_path, manifest, message):
    lakehouse = _landing(tmp_path, manifest=manifest)
    with pytest.raises(InputError, match=message):
        bronze.read_manifest(spark, lakehouse, BATCH)


def test_discover_batches_and_folder_mismatch(spark, tmp_path):
    lakehouse = _landing(tmp_path)
    assert bronze.discover_batches(spark, lakehouse) == [BATCH]
    assert bronze.discover_batches(spark, Lakehouse.local(tmp_path / "nothing")) == []
    wrong = tmp_path / "Files" / "landing" / "batch-other"
    wrong.mkdir()
    (wrong / "batch.json").write_text(json.dumps({"batch_id": BATCH}), encoding="utf-8")
    with pytest.raises(InputError, match="another folder"):
        bronze.discover_batches(spark, lakehouse)


def test_generated_landing_is_fully_represented(spark, pipeline_run):
    """Every non-blank landing line of the generated data is one Bronze row, by line number."""
    for batch_id in pipeline_run.batch_ids:
        for name, file_name, first in (("bronze_invoices", "invoices.csv", 2), ("bronze_ledger", "ledger.jsonl", 1)):
            path = pipeline_run.directory / "Files" / "landing" / batch_id / file_name
            expected = set(range(first, len(path.read_text(encoding="utf-8").splitlines()) + 1))
            df = spark.read.format("delta").load(pipeline_run.lakehouse.table(name)).filter(F.col("_batch_id") == batch_id)
            assert {r._line_number for r in df.select("_line_number").collect()} == expected
