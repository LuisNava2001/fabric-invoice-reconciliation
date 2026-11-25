"""Offline demo data (demo/data.js) built from the stored tables of a real local run.

Nothing here is hand-written: every number comes from the Delta tables and the validation
checks of the batches that were processed. If the pipeline fails, there is no data to show.
"""

from __future__ import annotations

import json
from pathlib import Path

from pyspark.sql import SparkSession

from .config import Lakehouse
from .report import build_report, package_versions
from .validate import validate_batch

TOTAL_KEYS = ("invoice_records", "ledger_records", "matched_pairs", "amount_mismatch_pairs", "currency_mismatch_pairs",
              "only_in_invoices", "only_in_ledger", "ambiguous_records", "duplicate_records", "invalid_records",
              "records_requiring_review", "records_with_dq_errors", "records_with_dq_warnings", "candidate_suggestions")


def build_demo_data(spark: SparkSession, lakehouse: Lakehouse, batch_ids: list[str]) -> dict:
    batches = []
    for batch_id in batch_ids:
        validation = validate_batch(spark, lakehouse, batch_id)
        batches.append(build_report(spark, lakehouse, batch_id, validation, include_delta_history=False))
    totals = {key: sum(int(b["metrics"][key]) for b in batches) for key in TOTAL_KEYS}
    return {
        "project": "fabric-invoice-reconciliation",
        "synthetic": True,
        "source": "Local PySpark + Delta Lake run of this repository on synthetic data (fictional companies).",
        "versions": package_versions(),
        "totals": totals,
        "all_checks_passed": all(b["validation"]["passed"] for b in batches),
        "batches": batches,
    }


def render(data: dict) -> str:
    return "window.RECON_DEMO = " + json.dumps(data, indent=1, sort_keys=True, ensure_ascii=False) + ";\n"


def write_or_check(data: dict, path: Path, check: bool) -> tuple[bool, str]:
    text = render(data)
    if check:
        if not path.exists():
            return False, f"{path} does not exist"
        current = path.read_text(encoding="utf-8").replace("\r\n", "\n")
        return (current == text, f"{path} is up to date" if current == text else f"{path} differs from a fresh run")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
    return True, f"wrote {path} ({len(text):,} bytes)"
