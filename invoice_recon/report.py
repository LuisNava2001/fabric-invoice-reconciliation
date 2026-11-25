"""Batch reports (JSON + Markdown) built from the stored Delta tables.

Only small aggregates and a handful of example rows are collected to the driver.
"""

from __future__ import annotations

import datetime as dt
import json
from decimal import Decimal
from importlib import metadata

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F

from . import __version__, bronze
from .config import SIDE_INVOICE, SIDE_LEDGER, SOURCE_INVOICES, SOURCE_LEDGER, STATUSES, Lakehouse
from .delta_io import read_batch, safe_history
from .pipeline import matched_amounts
from .validate import ValidationReport, _landing_records

EXAMPLE_TITLES = (
    "Exact match", "Reference written differently", "Rounding within tolerance", "Matched, posting date ambiguous",
    "Amount mismatch", "Currency mismatch", "Several candidates, not decided",
)


def _example_conditions() -> list:
    """Built lazily: Column expressions need an active Spark session."""
    matched = F.col("decision") == "MATCHED"
    return [
        matched & (F.col("reason_code") == "EXACT_AMOUNT") & (F.size("flags") == 0),
        matched & F.array_contains("flags", "REFERENCE_FORMAT_VARIANT"),
        matched & F.array_contains("flags", "ROUNDING_DIFFERENCE"),
        matched & F.array_contains("flags", "AMBIGUOUS_DATE"),
        F.col("decision") == "AMOUNT_MISMATCH",
        F.col("decision") == "CURRENCY_MISMATCH",
        F.col("decision") == "NOT_DECIDED_MULTIPLE_CANDIDATES",
    ]
EVIDENCE_FIELDS = ("decision", "reason_code", "invoice_line", "ledger_line", "invoice_id", "transaction_id", "supplier_id",
                   "invoice_reference", "ledger_reference", "reference_key", "invoice_currency", "ledger_currency",
                   "invoice_total", "ledger_amount", "amount_difference", "tolerance", "flags", "explanation")


def plain(value):
    """JSON-safe, deterministic representation (Decimal and dates as strings)."""
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (dt.date, dt.datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [plain(v) for v in value]
    return value


def _rows(df: DataFrame, fields=None) -> list[dict]:
    return [plain({k: v for k, v in row.asDict(recursive=True).items() if fields is None or k in fields}) for row in df.collect()]


def _counts(df: DataFrame, *columns: str) -> dict:
    result: dict = {}
    for row in df.groupBy(*columns).count().collect():
        target = result
        for column in columns[:-1]:
            target = target.setdefault(row[column], {})
        target[row[columns[-1]]] = row["count"]
    return result


def package_versions() -> dict:
    versions = {"fabric-invoice-reconciliation": __version__}
    for name in ("pyspark", "delta-spark"):
        try:
            versions[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            versions[name] = "unknown"
    return versions


def build_report(spark: SparkSession, lakehouse: Lakehouse, batch_id: str,
                 validation: ValidationReport | None = None, include_delta_history: bool = True) -> dict:
    manifest = bronze.read_manifest(spark, lakehouse, batch_id)
    t = {name: read_batch(spark, lakehouse.table(name), batch_id) for name in (
        "bronze_invoices", "bronze_ledger", "bronze_ingestion_errors", "silver_invoices", "silver_ledger",
        "silver_quarantine", "silver_dq_metrics", "gold_reconciliation", "gold_match_evidence",
        "gold_candidate_suggestions", "gold_exceptions", "gold_batch_metrics")}
    landing = {
        SOURCE_INVOICES: _landing_records(spark, f"{lakehouse.landing(batch_id)}/{manifest['sources'][SOURCE_INVOICES]}", 1),
        SOURCE_LEDGER: _landing_records(spark, f"{lakehouse.landing(batch_id)}/{manifest['sources'][SOURCE_LEDGER]}", 0),
    }
    bronze_layer = {}
    for source, name in ((SOURCE_INVOICES, "bronze_invoices"), (SOURCE_LEDGER, "bronze_ledger")):
        bronze_layer[source] = {"rows": t[name].count(), "parse_errors": t[name].filter(F.col("_parse_error").isNotNull()).count()}
    gold = t["gold_reconciliation"]
    status_by_side = _counts(gold, "side", "status")
    status_table = [{"status": s, "invoices": status_by_side.get(SIDE_INVOICE, {}).get(s, 0),
                     "ledger": status_by_side.get(SIDE_LEDGER, {}).get(s, 0)} for s in STATUSES]
    metrics = _rows(t["gold_batch_metrics"])[0]
    metrics.pop("_batch_id", None)

    evidence = t["gold_match_evidence"]
    examples = []
    for title, condition in zip(EXAMPLE_TITLES, _example_conditions()):
        first = evidence.filter(condition).orderBy("invoice_line", "ledger_line").limit(1).collect()
        if not first:
            continue
        rows = evidence.filter(F.col("match_key") == first[0].match_key).orderBy("invoice_line", "ledger_line")
        example = {"title": title, "rows": _rows(rows, EVIDENCE_FIELDS)}
        if "AMBIGUOUS_DATE" in (first[0].flags or []):
            ledger_row = (t["silver_ledger"].filter(F.col("_line_number") == first[0].ledger_line)
                          .select("posting_date_text", "posting_date_basis", "posting_date_candidates").collect()[0])
            example["ledger_posting_date"] = plain(ledger_row.asDict(recursive=True))
        examples.append(example)

    exceptions = t["gold_exceptions"]
    priority_order = F.when(F.col("priority") == "HIGH", 0).when(F.col("priority") == "MEDIUM", 1).otherwise(2)
    quarantine = t["silver_quarantine"]
    report = {
        "batch_id": batch_id,
        "reconciliation_period": manifest["reconciliation_period"],
        "synthetic": bool(manifest.get("synthetic")),
        "generator": manifest.get("generator"),
        "rules_version": metrics.get("rules_version"),
        "versions": package_versions(),
        "layers": {
            "landing_records": landing,
            "bronze": bronze_layer,
            "ingestion_errors": _counts(t["bronze_ingestion_errors"], "_source_system", "error_type"),
            "silver": _counts(t["silver_invoices"].select("_source_system", "record_status").unionByName(
                t["silver_ledger"].select("_source_system", "record_status")), "_source_system", "record_status"),
            "quarantined": quarantine.count(),
            "gold": status_by_side,
        },
        "metrics": metrics,
        "status_table": status_table,
        "matched_amounts_by_currency": matched_amounts(spark, lakehouse, batch_id),
        "dq_rules": _rows(t["silver_dq_metrics"].orderBy("_source_system", F.col("severity"), "rule_id"),
                          ("_source_system", "rule_id", "severity", "description", "failed_records", "total_records",
                           "failure_rate")),
        "evidence_examples": examples,
        "suggestions": _rows(t["gold_candidate_suggestions"].orderBy("invoice_line", "suggestion_rank").limit(8)),
        "exceptions": {
            "total": exceptions.count(),
            "by_priority": _counts(exceptions, "priority"),
            "by_status": _counts(exceptions, "status"),
            "sample": _rows(exceptions.orderBy(priority_order, "side", "line_number").limit(12)),
        },
        "quarantine_sample": _rows(quarantine.orderBy("_source_system", "_line_number").limit(8)),
        "validation": validation.to_dict() if validation else None,
    }
    for item in report["suggestions"] + report["exceptions"]["sample"] + report["quarantine_sample"]:
        item.pop("_batch_id", None)
    if include_delta_history:
        report["delta_versions"] = {
            name: (safe_history(spark, lakehouse.table(name)) or [{}])[-1] for name in t
        }
    return report


def render_markdown(report: dict) -> str:
    m = report["metrics"]
    lines = [
        f"# Reconciliation report: {report['batch_id']} ({report['reconciliation_period']})",
        "",
        "Synthetic data. Generated by a local Spark + Delta Lake run of this repository." if report["synthetic"] else "",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "| --- | --- |",
    ]
    for key in ("invoice_records", "ledger_records", "matched_pairs", "amount_mismatch_pairs", "currency_mismatch_pairs",
                "only_in_invoices", "only_in_ledger", "ambiguous_records", "duplicate_records", "invalid_records",
                "records_requiring_review", "candidate_suggestions", "reconciliation_rate", "eligible_reconciliation_rate"):
        lines.append(f"| {key} | {m[key]} |")
    layers = report["layers"]
    lines += ["", "## Layers", "", "| Source | Landing records | Bronze rows | Parse errors | Silver VALID / INVALID / DUPLICATE |",
              "| --- | --- | --- | --- | --- |"]
    for source in (SOURCE_INVOICES, SOURCE_LEDGER):
        silver = layers["silver"].get(source, {})
        lines.append(f"| {source} | {layers['landing_records'][source]} | {layers['bronze'][source]['rows']} | "
                     f"{layers['bronze'][source]['parse_errors']} | {silver.get('VALID', 0)} / {silver.get('INVALID', 0)} / "
                     f"{silver.get('DUPLICATE', 0)} |")
    lines += ["", "## Status by side", "", "| Status | Invoices | Ledger |", "| --- | --- | --- |"]
    lines += [f"| {row['status']} | {row['invoices']} | {row['ledger']} |" for row in report["status_table"]]
    lines += ["", "## Data-quality rules that fired", "", "| Source | Rule | Severity | Failed | Rate |", "| --- | --- | --- | --- | --- |"]
    fired = [r for r in report["dq_rules"] if r["failed_records"]]
    lines += [f"| {r['_source_system']} | {r['rule_id']} | {r['severity']} | {r['failed_records']} | {r['failure_rate']} |" for r in fired]
    lines += ["", f"{len(report['dq_rules']) - len(fired)} other rules found no failures.", "", "## Match evidence examples", ""]
    for example in report["evidence_examples"]:
        lines.append(f"### {example['title']}")
        lines.append("")
        for row in example["rows"]:
            lines.append(f"- `{row['decision']}` ({row['reason_code']}), invoice line {row['invoice_line']} / ledger line "
                         f"{row['ledger_line']}: {row['explanation']}")
        if "ledger_posting_date" in example:
            p = example["ledger_posting_date"]
            lines.append(f"- posting date `{p['posting_date_text']}` read as {p['posting_date_basis']}; candidates "
                         f"{', '.join(p['posting_date_candidates'] or [])} (not resolved)")
        lines.append("")
    lines += ["## Candidate suggestions (never auto-approved)", ""]
    if report["suggestions"]:
        lines += ["| Invoice line | Ledger line | Criterion | Score |", "| --- | --- | --- | --- |"]
        lines += [f"| {s['invoice_line']} | {s['ledger_line']} | {s['criterion']} | {s['score']} |" for s in report["suggestions"]]
    else:
        lines.append("No suggestions.")
    ex = report["exceptions"]
    lines += ["", "## Exceptions", "", f"{ex['total']} records require review: " +
              ", ".join(f"{k} {v}" for k, v in sorted(ex["by_priority"].items())) + ".", ""]
    if report.get("validation"):
        v = report["validation"]
        lines += ["## Validation", "", f"Overall: {'PASSED' if v['passed'] else 'FAILED'}", "", "| Check | Result | Detail |",
                  "| --- | --- | --- |"]
        lines += [f"| {c['check_id']} | {'pass' if c['passed'] else 'FAIL'} | {c['detail']} |" for c in v["checks"]]
    return "\n".join(lines).replace("\n\n\n", "\n\n") + "\n"


def to_json(report: dict) -> str:
    return json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
