"""Stage orchestration shared by the CLI and the Fabric notebook.

Each stage reads its upstream layer for one batch, writes its own tables for that batch
(replaceWhere on ``_batch_id``) and upserts its status into ``ops_batch_runs``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from pyspark import StorageLevel
from pyspark.sql import SparkSession
from pyspark.sql import functions as F

from . import bronze, reconcile, silver
from .config import SOURCE_INVOICES, SOURCE_LEDGER, InputError, Lakehouse, Rules, ValidationFailed, load_rules
from .delta_io import read_batch, record_run, require_batch, write_batch
from .schemas import (
    BRONZE_INGESTION_ERRORS,
    BRONZE_INVOICES,
    BRONZE_LEDGER,
    GOLD_BATCH_METRICS,
    GOLD_CANDIDATE_SUGGESTIONS,
    GOLD_EXCEPTIONS,
    GOLD_MATCH_EVIDENCE,
    GOLD_RECONCILIATION,
    SILVER_DQ_METRICS,
    SILVER_INVOICES,
    SILVER_LEDGER,
    SILVER_QUARANTINE,
)


@dataclass
class StageResult:
    batch_id: str
    stage: str
    counts: dict = field(default_factory=dict)

    def summary(self) -> str:
        return f"[{self.stage}] {self.batch_id}: " + ", ".join(f"{k}={v:,}" for k, v in self.counts.items())


def _status_counts(df, column: str = "record_status") -> dict:
    return {row[column]: row["count"] for row in df.groupBy(column).count().collect()}


def ingest(spark: SparkSession, lakehouse: Lakehouse, batch_id: str, rules: Rules) -> StageResult:
    """Landing files -> bronze_invoices, bronze_ledger, bronze_ingestion_errors."""
    manifest = bronze.read_manifest(spark, lakehouse, batch_id)
    files = manifest["sources"]
    inv, inv_errors, inv_problem = bronze.ingest_invoices(spark, lakehouse, batch_id, files[SOURCE_INVOICES])
    led, led_errors, led_problem = bronze.ingest_ledger(spark, lakehouse, batch_id, files[SOURCE_LEDGER])
    errors = inv_errors.unionByName(led_errors).select(*BRONZE_INGESTION_ERRORS.fieldNames())
    problems = [f"{source}: {problem}" for source, problem in ((SOURCE_INVOICES, inv_problem), (SOURCE_LEDGER, led_problem)) if problem]
    errors_path = lakehouse.table("bronze_ingestion_errors")
    if problems:
        # Fail closed: record why, keep previously ingested data for this batch untouched.
        write_batch(errors, errors_path, batch_id, BRONZE_INGESTION_ERRORS)
        record_run(spark, lakehouse, batch_id, "bronze", "REJECTED", None, None, {"problems": problems}, rules.version)
        raise InputError(f"batch {batch_id} rejected: " + "; ".join(problems))
    counts = {
        "invoice_rows": write_batch(inv.select(*BRONZE_INVOICES.fieldNames()), lakehouse.table("bronze_invoices"),
                                    batch_id, BRONZE_INVOICES),
        "ledger_rows": write_batch(led.select(*BRONZE_LEDGER.fieldNames()), lakehouse.table("bronze_ledger"),
                                   batch_id, BRONZE_LEDGER),
        "ingestion_errors": write_batch(errors, errors_path, batch_id, BRONZE_INGESTION_ERRORS),
    }
    record_run(spark, lakehouse, batch_id, "bronze", "SUCCEEDED", None, counts["invoice_rows"] + counts["ledger_rows"],
               counts, rules.version)
    return StageResult(batch_id, "bronze", counts)


def normalize(spark: SparkSession, lakehouse: Lakehouse, batch_id: str, rules: Rules) -> StageResult:
    """Bronze -> silver_invoices, silver_ledger, silver_quarantine, silver_dq_metrics."""
    period = bronze.read_manifest(spark, lakehouse, batch_id)["reconciliation_period"]
    sources = {
        SOURCE_INVOICES: (require_batch(spark, lakehouse.table("bronze_invoices"), batch_id), silver.normalize_invoices,
                          "silver_invoices", SILVER_INVOICES),
        SOURCE_LEDGER: (require_batch(spark, lakehouse.table("bronze_ledger"), batch_id), silver.normalize_ledger,
                        "silver_ledger", SILVER_LEDGER),
    }
    frames, counts = {}, {}
    for source, (bronze_df, normalize_fn, table, schema) in sources.items():
        bronze_rows = bronze_df.count()
        frame = normalize_fn(bronze_df, rules, period).persist(StorageLevel.MEMORY_AND_DISK)
        written = write_batch(frame.select(*schema.fieldNames()), lakehouse.table(table), batch_id, schema)
        if written != bronze_rows:
            raise ValidationFailed(f"{table}: {bronze_rows} bronze rows became {written} silver rows")
        frames[source] = frame
        for status, value in sorted(_status_counts(frame).items()):
            counts[f"{table.split('_')[1]}_{status.lower()}"] = value
    try:
        counts["quarantined"] = write_batch(silver.quarantine(frames[SOURCE_INVOICES], frames[SOURCE_LEDGER]),
                                            lakehouse.table("silver_quarantine"), batch_id, SILVER_QUARANTINE)
        metrics = silver.dq_metrics(spark, frames[SOURCE_INVOICES], SOURCE_INVOICES, batch_id).unionByName(
            silver.dq_metrics(spark, frames[SOURCE_LEDGER], SOURCE_LEDGER, batch_id))
        write_batch(metrics, lakehouse.table("silver_dq_metrics"), batch_id, SILVER_DQ_METRICS)
    finally:
        for frame in frames.values():
            frame.unpersist()
    total = sum(v for k, v in counts.items() if k != "quarantined")
    record_run(spark, lakehouse, batch_id, "silver", "SUCCEEDED", total, total, counts, rules.version)
    return StageResult(batch_id, "silver", counts)


def reconcile_batch(spark: SparkSession, lakehouse: Lakehouse, batch_id: str, rules: Rules) -> StageResult:
    """Silver -> gold_reconciliation, gold_match_evidence, gold_candidate_suggestions, gold_exceptions, gold_batch_metrics."""
    period = bronze.read_manifest(spark, lakehouse, batch_id)["reconciliation_period"]
    invoices = require_batch(spark, lakehouse.table("silver_invoices"), batch_id).persist(StorageLevel.MEMORY_AND_DISK)
    ledger = require_batch(spark, lakehouse.table("silver_ledger"), batch_id).persist(StorageLevel.MEMORY_AND_DISK)
    try:
        frames = reconcile.reconcile(invoices, ledger, rules, batch_id)
        records = write_batch(frames.reconciliation, lakehouse.table("gold_reconciliation"), batch_id, GOLD_RECONCILIATION)
        stored = read_batch(spark, lakehouse.table("gold_reconciliation"), batch_id)
        evidence = write_batch(frames.evidence, lakehouse.table("gold_match_evidence"), batch_id, GOLD_MATCH_EVIDENCE)
        suggestions = reconcile.build_suggestions(stored, invoices, ledger, rules, batch_id)
        suggestion_rows = write_batch(suggestions, lakehouse.table("gold_candidate_suggestions"), batch_id,
                                      GOLD_CANDIDATE_SUGGESTIONS)
        stored_suggestions = read_batch(spark, lakehouse.table("gold_candidate_suggestions"), batch_id)
        exceptions = write_batch(reconcile.build_exceptions(stored, stored_suggestions),
                                 lakehouse.table("gold_exceptions"), batch_id, GOLD_EXCEPTIONS)
        metrics = reconcile.batch_metrics(spark, stored, invoices, ledger, stored_suggestions, batch_id, period, rules)
        write_batch(metrics, lakehouse.table("gold_batch_metrics"), batch_id, GOLD_BATCH_METRICS)
        statuses = _status_counts(stored, "status")
    finally:
        invoices.unpersist()
        ledger.unpersist()
    counts = {"records": records, "evidence_rows": evidence, "suggestions": suggestion_rows, "exceptions": exceptions}
    counts.update({status.lower(): value for status, value in sorted(statuses.items())})
    record_run(spark, lakehouse, batch_id, "gold", "SUCCEEDED", records, records, counts, rules.version)
    return StageResult(batch_id, "gold", counts)


STAGES = {"ingest": ingest, "normalize": normalize, "reconcile": reconcile_batch}


def resolve_batches(spark: SparkSession, lakehouse: Lakehouse, requested: list[str] | None) -> list[str]:
    available = bronze.discover_batches(spark, lakehouse)
    if requested:
        missing = [b for b in requested if b not in available]
        if missing:
            raise InputError(f"no landing data for batch(es) {', '.join(missing)} under {lakehouse.landing_root()}")
        return list(requested)
    if not available:
        raise InputError(f"no batches found under {lakehouse.landing_root()}; run generate-data first")
    return available


def run(spark: SparkSession, lakehouse: Lakehouse, batch_ids: list[str] | None = None, rules: Rules | None = None,
        log: Callable[[str], None] = print) -> list[StageResult]:
    """Bronze -> Silver -> Gold for each batch, in batch order."""
    rules = rules or load_rules()
    results = []
    for batch_id in resolve_batches(spark, lakehouse, batch_ids):
        for stage in STAGES.values():
            result = stage(spark, lakehouse, batch_id, rules)
            log(result.summary())
            results.append(result)
    return results


def table_counts(spark: SparkSession, lakehouse: Lakehouse, batch_id: str, names: list[str]) -> dict:
    return {name: read_batch(spark, lakehouse.table(name), batch_id).count() for name in names}


def matched_amounts(spark: SparkSession, lakehouse: Lakehouse, batch_id: str) -> list[dict]:
    """Matched invoice totals per currency (never summed across currencies)."""
    rows = (read_batch(spark, lakehouse.table("gold_reconciliation"), batch_id)
            .filter((F.col("side") == "INVOICE") & (F.col("status") == "MATCHED"))
            .groupBy("currency").agg(F.count(F.lit(1)).alias("records"), F.sum("amount").alias("amount"))
            .orderBy("currency").collect())
    return [{"currency": r.currency, "records": r.records, "amount": str(r.amount)} for r in rows]
