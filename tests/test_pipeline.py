"""End to end on local Spark + Delta: conservation, ground truth, idempotency, isolation, rejection."""

import json
from decimal import ROUND_HALF_UP, Decimal

import pytest
from delta.tables import DeltaTable
from pyspark.sql import functions as F

from invoice_recon import generator, pipeline
from invoice_recon.config import BATCH_TABLES, InputError, Lakehouse
from invoice_recon.delta_io import read_batch
from invoice_recon.validate import validate_batch

from .helpers import table_digest

pytestmark = pytest.mark.spark


def test_every_validation_check_passes_including_ground_truth(spark, pipeline_run):
    for batch_id in pipeline_run.batch_ids:
        report = validate_batch(spark, pipeline_run.lakehouse, batch_id)
        failed = [(c.check_id, c.detail) for c in report.checks if not c.passed]
        assert failed == []
        checks = {c.check_id: c for c in report.checks}
        assert "SYNTHETIC_GROUND_TRUTH" in checks and "SYNTHETIC_SUGGESTIONS" in checks
        total = checks["SYNTHETIC_GROUND_TRUTH"].detail.split(" ")[0]
        assert total.split("/")[0] == total.split("/")[1], "every record has its designed status, reason, flags and review"


def test_stage_counts_line_up(pipeline_run):
    by_stage = {(r.batch_id, r.stage): r.counts for r in pipeline_run.results}
    assert len(by_stage) == 6
    for batch_id in pipeline_run.batch_ids:
        bronze, silver, gold = (by_stage[(batch_id, s)] for s in ("bronze", "silver", "gold"))
        assert sum(v for k, v in silver.items() if k.startswith("invoices_")) == bronze["invoice_rows"]
        assert sum(v for k, v in silver.items() if k.startswith("ledger_")) == bronze["ledger_rows"]
        assert gold["records"] == bronze["invoice_rows"] + bronze["ledger_rows"]
        assert silver["quarantined"] == sum(v for k, v in silver.items() if k.endswith(("_invalid", "_duplicate")))


def test_metrics_are_derived_from_stored_tables(spark, pipeline_run):
    batch_id = pipeline_run.batch_ids[0]
    lakehouse = pipeline_run.lakehouse
    m = read_batch(spark, lakehouse.table("gold_batch_metrics"), batch_id).collect()[0]
    gold = read_batch(spark, lakehouse.table("gold_reconciliation"), batch_id)
    matched = gold.filter((F.col("side") == "INVOICE") & (F.col("status") == "MATCHED")).count()
    assert m.matched_pairs == matched
    expected_rate = (Decimal(matched) / Decimal(m.invoice_records)).quantize(Decimal("0.0001"), ROUND_HALF_UP)
    assert m.reconciliation_rate == expected_rate
    amounts = pipeline.matched_amounts(spark, lakehouse, batch_id)
    assert sum(a["records"] for a in amounts) == matched and len({a["currency"] for a in amounts}) == len(amounts)


def test_rerunning_a_batch_changes_nothing_and_leaves_the_other_batch_alone(spark, rules, pipeline_run):
    lakehouse, first, second = pipeline_run.lakehouse, *pipeline_run.batch_ids
    version_before = DeltaTable.forPath(spark, lakehouse.table("gold_reconciliation")).history(1).collect()[0].version
    for stage in pipeline.STAGES.values():
        stage(spark, lakehouse, first, rules)
    for name in BATCH_TABLES:
        for batch_id in (first, second):
            assert table_digest(spark, lakehouse, name, batch_id) == pipeline_run.digests[(name, batch_id)], (name, batch_id)
    version_after = DeltaTable.forPath(spark, lakehouse.table("gold_reconciliation")).history(1).collect()[0].version
    assert version_after > version_before, "the batch was really rewritten, with identical content"
    runs = spark.read.format("delta").load(lakehouse.table("ops_batch_runs"))
    assert runs.count() == 6 and runs.filter(F.col("status") != "SUCCEEDED").count() == 0


@pytest.fixture()
def small_lake(spark, tmp_path):
    generator.generate(tmp_path, invoices=100, batches=1)
    return tmp_path, Lakehouse.local(tmp_path), "batch-2026-03"


def test_corrected_landing_file_replaces_the_bronze_slice(spark, rules, small_lake):
    directory, lakehouse, batch_id = small_lake
    pipeline.ingest(spark, lakehouse, batch_id, rules)
    path = directory / "Files" / "landing" / batch_id / "invoices.csv"
    lines = path.read_text(encoding="utf-8").splitlines()
    lines[1] = lines[1].replace(lines[1].split(",")[0], "EI-CORRECTED-1", 1)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="")
    pipeline.ingest(spark, lakehouse, batch_id, rules)
    bronze = read_batch(spark, lakehouse.table("bronze_invoices"), batch_id)
    assert bronze.count() == len(lines) - 1
    assert bronze.filter(F.col("_line_number") == 2).collect()[0].invoice_id == "EI-CORRECTED-1"


def test_schema_mismatch_rejects_the_batch_and_keeps_previous_data(spark, rules, small_lake):
    directory, lakehouse, batch_id = small_lake
    pipeline.ingest(spark, lakehouse, batch_id, rules)
    before = table_digest(spark, lakehouse, "bronze_invoices", batch_id)
    path = directory / "Files" / "landing" / batch_id / "invoices.csv"
    text = path.read_text(encoding="utf-8")
    path.write_text(text.replace("total_amount", "invoice_total", 1), encoding="utf-8", newline="")
    with pytest.raises(InputError, match="rejected"):
        pipeline.ingest(spark, lakehouse, batch_id, rules)
    assert table_digest(spark, lakehouse, "bronze_invoices", batch_id) == before, "fail closed"
    errors = (read_batch(spark, lakehouse.table("bronze_ingestion_errors"), batch_id)
              .filter(F.col("_source_system") == "E_INVOICES").collect())
    assert [e.error_type for e in errors] == ["SCHEMA_MISMATCH"] and "invoice_total" in errors[0].error_detail
    run = spark.read.format("delta").load(lakehouse.table("ops_batch_runs")).collect()[0]
    assert run.status == "REJECTED" and "invoice_total" in json.loads(run.details)["problems"][0]


def test_downstream_stage_without_upstream_data_is_an_input_error(spark, rules, small_lake):
    _, lakehouse, batch_id = small_lake
    with pytest.raises(InputError, match="run the upstream stage first"):
        pipeline.normalize(spark, lakehouse, batch_id, rules)
    with pytest.raises(InputError, match="no landing data"):
        pipeline.resolve_batches(spark, lakehouse, ["batch-1999-01"])
