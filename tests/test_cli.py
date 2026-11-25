"""CLI commands in-process against the shared Spark session (exit codes 0, 3 and 4)."""

import json
import shutil

import pytest
from pyspark.sql import functions as F

from invoice_recon import cli, generator
from invoice_recon.config import EXIT_INPUT, EXIT_OK, EXIT_VALIDATION, Lakehouse
from invoice_recon.delta_io import read_batch

pytestmark = pytest.mark.spark


def test_validate_and_report_on_a_processed_lakehouse(spark, pipeline_run, capsys):
    lake = str(pipeline_run.directory)
    assert cli.main(["--lakehouse", lake, "validate"]) == EXIT_OK
    out = capsys.readouterr().out
    assert out.count("checks passed") == 2 and "FAIL" not in out
    assert cli.main(["--lakehouse", lake, "report", "--batch", pipeline_run.batch_ids[0]]) == EXIT_OK
    folder = pipeline_run.directory / "Files" / "reports" / pipeline_run.batch_ids[0]
    report = json.loads((folder / "reconciliation_report.json").read_text(encoding="utf-8"))
    assert report["validation"]["passed"] and (folder / "reconciliation_report.md").exists()


def test_demo_write_check_and_drift(spark, pipeline_run, tmp_path):
    lake, out = str(pipeline_run.directory), tmp_path / "data.js"
    assert cli.main(["--lakehouse", lake, "demo", "--out", str(out)]) == EXIT_OK
    assert cli.main(["--lakehouse", lake, "demo", "--out", str(out), "--check"]) == EXIT_OK
    out.write_text(out.read_text(encoding="utf-8").replace('"synthetic": true', '"synthetic": false', 1), encoding="utf-8")
    assert cli.main(["--lakehouse", lake, "demo", "--out", str(out), "--check"]) == EXIT_VALIDATION


def test_tampered_gold_table_fails_validation(spark, pipeline_run, tmp_path, capsys):
    copy = tmp_path / "tampered"
    shutil.copytree(pipeline_run.directory, copy)
    lakehouse = Lakehouse.local(copy)
    batch_id = pipeline_run.batch_ids[0]
    gold = read_batch(spark, lakehouse.table("gold_reconciliation"), batch_id)
    gold.filter(F.col("status") == "MATCHED").limit(1).write.format("delta").mode("append").save(lakehouse.table("gold_reconciliation"))
    assert cli.main(["--lakehouse", str(copy), "validate", "--batch", batch_id]) == EXIT_VALIDATION
    out = capsys.readouterr().out
    assert "FAIL GOLD_ONE_ROW_PER_RECORD" in out and "FAIL ONE_TO_ONE_MATCHES" in out


def test_ingest_of_a_bad_header_exits_3(spark, tmp_path, capsys):
    generator.generate(tmp_path, invoices=100, batches=1)
    path = tmp_path / "Files" / "landing" / "batch-2026-03" / "invoices.csv"
    path.write_text(path.read_text(encoding="utf-8").replace("currency", "ccy", 1), encoding="utf-8", newline="")
    assert cli.main(["--lakehouse", str(tmp_path), "ingest"]) == EXIT_INPUT
    assert "rejected" in capsys.readouterr().err


def test_unknown_batch_exits_3(spark, pipeline_run):
    assert cli.main(["--lakehouse", str(pipeline_run.directory), "validate", "--batch", "batch-1999-01"]) == EXIT_INPUT
