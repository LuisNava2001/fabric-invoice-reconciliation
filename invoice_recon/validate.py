"""Record-conservation and invariant checks over the stored Delta tables of one batch.

The checks read what was actually written, not the in-memory DataFrames that produced it.
Landing counts are re-derived with a different reader (line mode) than the one Bronze
used (whole-file mode), so the first check is not circular.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

from pyspark.errors import AnalysisException
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import ArrayType, BooleanType, IntegerType, StringType, StructField, StructType

from . import bronze
from .config import (
    GROUND_TRUTH_FILE,
    GROUND_TRUTH_SUGGESTIONS_FILE,
    SIDE_INVOICE,
    SIDE_LEDGER,
    SOURCE_INVOICES,
    SOURCE_LEDGER,
    STATUSES,
    Lakehouse,
)
from .delta_io import read_batch

DECIDED = ("MATCHED", "AMOUNT_MISMATCH", "CURRENCY_MISMATCH")
TRUTH_SCHEMA = StructType([
    StructField("side", StringType()), StructField("line_number", IntegerType()), StructField("scenario", StringType()),
    StructField("expected_status", StringType()), StructField("expected_reason", StringType()),
    StructField("expected_flags", ArrayType(StringType())), StructField("expected_review", BooleanType()),
])
SUGGESTION_TRUTH_SCHEMA = "invoice_line INT, ledger_line INT, criterion STRING"


@dataclass
class Check:
    check_id: str
    passed: bool
    detail: str


@dataclass
class ValidationReport:
    batch_id: str
    checks: list = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(check.passed for check in self.checks)

    def add(self, check_id: str, passed: bool, detail: str) -> None:
        self.checks.append(Check(check_id, bool(passed), detail))

    def to_dict(self) -> dict:
        return {"batch_id": self.batch_id, "passed": self.passed, "checks": [asdict(c) for c in self.checks]}


def _landing_records(spark: SparkSession, path: str, header_lines: int) -> int:
    lines = spark.read.text(path)  # line mode: independent of Bronze's whole-file reader
    return lines.filter(F.trim(F.col("value")) != "").count() - header_lines


def _same_lines(left: DataFrame, right: DataFrame) -> tuple[int, int]:
    """Rows present on one side only (by line number): (missing on right, extra on right)."""
    return left.exceptAll(right).count(), right.exceptAll(left).count()


def _zero(report: ValidationReport, check_id: str, count: int, what: str) -> None:
    report.add(check_id, count == 0, f"{count} {what}")


def validate_batch(spark: SparkSession, lakehouse: Lakehouse, batch_id: str, ground_truth: bool = True) -> ValidationReport:
    report = ValidationReport(batch_id)
    manifest = bronze.read_manifest(spark, lakehouse, batch_id)
    table = {name: read_batch(spark, lakehouse.table(name), batch_id) for name in (
        "bronze_invoices", "bronze_ledger", "silver_invoices", "silver_ledger", "silver_quarantine",
        "gold_reconciliation", "gold_match_evidence", "gold_candidate_suggestions", "gold_exceptions",
        "gold_batch_metrics")}
    gold = table["gold_reconciliation"]

    # 1. Record conservation, layer by layer, by line number.
    sources = ((SOURCE_INVOICES, SIDE_INVOICE, "bronze_invoices", "silver_invoices", 1),
               (SOURCE_LEDGER, SIDE_LEDGER, "bronze_ledger", "silver_ledger", 0))
    for source, side, bronze_name, silver_name, header in sources:
        landing = _landing_records(spark, f"{lakehouse.landing(batch_id)}/{manifest['sources'][source]}", header)
        bronze_rows = table[bronze_name].count()
        report.add(f"LANDING_TO_BRONZE[{source}]", landing == bronze_rows,
                   f"{landing} non-blank landing records, {bronze_rows} bronze rows")
        b_lines = table[bronze_name].select(F.col("_line_number").alias("line"))
        s_lines = table[silver_name].select(F.col("_line_number").alias("line"))
        g_lines = gold.filter(F.col("side") == side).select(F.col("line_number").alias("line"))
        missing, extra = _same_lines(b_lines, s_lines)
        report.add(f"BRONZE_TO_SILVER[{source}]", missing == extra == 0, f"{missing} lost, {extra} added")
        missing, extra = _same_lines(s_lines, g_lines)
        report.add(f"SILVER_TO_GOLD[{side}]", missing == extra == 0, f"{missing} lost, {extra} added")
        statuses = {r.record_status: r["count"] for r in table[silver_name].groupBy("record_status").count().collect()}
        unknown = set(statuses) - {"VALID", "INVALID", "DUPLICATE"}
        report.add(f"SILVER_STATUS_PARTITION[{source}]", not unknown, f"statuses {dict(sorted(statuses.items()))}")
        quarantined = table["silver_quarantine"].filter(F.col("_source_system") == source).count()
        not_valid = sum(v for k, v in statuses.items() if k != "VALID")
        report.add(f"QUARANTINE_COMPLETE[{source}]", quarantined == not_valid,
                   f"{quarantined} quarantined, {not_valid} non-VALID silver rows")

    _zero(report, "QUARANTINE_HAS_REASON",
          table["silver_quarantine"].filter(F.col("status_reason").isNull() | (F.col("status_reason") == "")).count(),
          "quarantined rows without a reason")

    # 2. Gold invariants.
    _zero(report, "GOLD_ONE_ROW_PER_RECORD",
          gold.groupBy("side", "line_number").count().filter(F.col("count") > 1).count(), "records with more than one status")
    _zero(report, "STATUS_IN_CATALOG", gold.filter(~F.col("status").isin(*STATUSES)).count(), "rows with an unknown status")
    matched = gold.filter(F.col("status") == "MATCHED")
    _zero(report, "NO_NULL_KEY_MATCH",
          matched.filter(F.col("match_key").isNull() | F.col("record_id").isNull()).count(),
          "MATCHED rows with a NULL key or record ID")
    evidence_matched = table["gold_match_evidence"].filter(F.col("decision") == "MATCHED")
    counts = (matched.filter(F.col("side") == SIDE_INVOICE).count(), matched.filter(F.col("side") == SIDE_LEDGER).count(),
              evidence_matched.count(), evidence_matched.select("invoice_line").distinct().count(),
              evidence_matched.select("ledger_line").distinct().count())
    report.add("ONE_TO_ONE_MATCHES", len(set(counts)) == 1,
               "matched invoices, matched ledger rows, evidence rows, distinct invoice lines, distinct ledger lines = "
               + ", ".join(str(c) for c in counts))
    inv = gold.filter((F.col("side") == SIDE_INVOICE) & F.col("status").isin(*DECIDED)).alias("i")
    led = gold.filter((F.col("side") == SIDE_LEDGER) & F.col("status").isin(*DECIDED)).alias("l")
    asymmetric = inv.join(led, F.col("i.counterpart_line_number") == F.col("l.line_number"), "full_outer").filter(
        F.col("i.line_number").isNull() | F.col("l.line_number").isNull()
        | (F.col("l.counterpart_line_number") != F.col("i.line_number")) | (F.col("i.status") != F.col("l.status"))).count()
    _zero(report, "COUNTERPARTS_SYMMETRIC", asymmetric, "decided pairs whose two sides disagree")
    evidence = table["gold_match_evidence"]
    _zero(report, "MATCHED_SAME_CURRENCY",
          evidence_matched.filter(F.col("invoice_currency") != F.col("ledger_currency")).count(),
          "MATCHED pairs with different currencies")
    _zero(report, "MATCHED_WITHIN_TOLERANCE",
          evidence_matched.filter(F.col("amount_difference").isNull() | (F.col("amount_difference") > F.col("tolerance"))).count(),
          "MATCHED pairs outside tolerance")
    _zero(report, "NO_CROSS_CURRENCY_COMPARISON",
          evidence.filter((F.col("decision") == "CURRENCY_MISMATCH") & F.col("amount_difference").isNotNull()).count(),
          "currency mismatches with a computed amount difference")
    silver_status = (table["silver_invoices"].select(F.lit(SIDE_INVOICE).alias("side"), F.col("_line_number").alias("line_number"), "record_status")
                     .unionByName(table["silver_ledger"].select(F.lit(SIDE_LEDGER).alias("side"), F.col("_line_number").alias("line_number"), "record_status")))
    _zero(report, "ONLY_VALID_RECORDS_DECIDED",
          gold.filter(~F.col("status").isin("INVALID_RECORD", "DUPLICATE")).join(silver_status, ["side", "line_number"])
          .filter(F.col("record_status") != "VALID").count(), "non-VALID records that reached a matching status")

    suggestions = table["gold_candidate_suggestions"]
    open_inv = gold.filter(F.col("status") == "ONLY_IN_INVOICES").select(F.col("line_number").alias("invoice_line"))
    open_led = gold.filter(F.col("status") == "ONLY_IN_LEDGER").select(F.col("line_number").alias("ledger_line"))
    _zero(report, "SUGGESTIONS_NEVER_APPROVED",
          suggestions.filter(F.col("auto_approved")).count()
          + suggestions.join(open_inv, "invoice_line", "left_anti").count()
          + suggestions.join(open_led, "ledger_line", "left_anti").count(),
          "suggestions auto-approved or attached to a record that is not ONLY_IN_*")
    exceptions = table["gold_exceptions"].count()
    review = gold.filter(F.col("requires_review")).count()
    report.add("EXCEPTIONS_MATCH_REVIEW_FLAG", exceptions == review, f"{exceptions} exceptions, {review} records requiring review")
    metrics = table["gold_batch_metrics"].collect()
    if len(metrics) != 1:
        report.add("METRICS_CONSISTENT", False, f"{len(metrics)} metrics rows (expected 1)")
    else:
        m = metrics[0]
        expected = (gold.filter(F.col("side") == SIDE_INVOICE).count(), gold.filter(F.col("side") == SIDE_LEDGER).count(),
                    counts[0], review, suggestions.count())
        stored = (m.invoice_records, m.ledger_records, m.matched_pairs, m.records_requiring_review, m.candidate_suggestions)
        report.add("METRICS_CONSISTENT", expected == stored, f"recomputed {expected}, stored {stored}")

    if ground_truth:
        _check_ground_truth(spark, lakehouse, batch_id, gold, suggestions, report)
    return report


def _check_ground_truth(spark: SparkSession, lakehouse: Lakehouse, batch_id: str, gold: DataFrame,
                        suggestions: DataFrame, report: ValidationReport) -> None:
    """Synthetic data only: compare every record with the outcome the generator designed."""
    base = lakehouse.ground_truth(batch_id)
    try:
        truth = spark.read.schema(TRUTH_SCHEMA).json(f"{base}/{GROUND_TRUTH_FILE}")
        expected_suggestions = spark.read.schema(SUGGESTION_TRUTH_SCHEMA).json(f"{base}/{GROUND_TRUTH_SUGGESTIONS_FILE}")
        total = truth.count()
    except AnalysisException:
        return  # no ground truth: not synthetic data generated by this project
    joined = truth.join(gold, ["side", "line_number"], "left")
    wrong = joined.filter(
        F.col("status").isNull() | (F.col("status") != F.col("expected_status"))
        | (F.col("expected_reason").isNotNull() & (F.col("reason_code") != F.col("expected_reason")))
        | (F.size(F.array_except(F.col("expected_flags"), F.coalesce(F.col("flags"), F.array().cast("array<string>")))) > 0)
        | (F.col("requires_review") != F.col("expected_review")))
    mismatches = wrong.count()
    sample = [f"{r.side}:{r.line_number} {r.scenario} expected {r.expected_status} got {r.status}"
              for r in wrong.orderBy("side", "line_number").limit(3).collect()]
    report.add("SYNTHETIC_GROUND_TRUTH", mismatches == 0,
               f"{total - mismatches}/{total} records match their designed outcome" + (f"; e.g. {sample}" if sample else ""))
    missing = expected_suggestions.join(suggestions, ["invoice_line", "ledger_line", "criterion"], "left_anti").count()
    report.add("SYNTHETIC_SUGGESTIONS", missing == 0,
               f"{expected_suggestions.count() - missing}/{expected_suggestions.count()} designed suggestions produced")
