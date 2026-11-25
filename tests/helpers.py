"""Test helpers: build Bronze-shaped DataFrames from dicts and fingerprint stored tables."""

from __future__ import annotations

import hashlib
import json

from pyspark.sql import functions as F

from invoice_recon.config import INVOICE_COLUMNS, LEDGER_COLUMNS, SOURCE_INVOICES, SOURCE_LEDGER
from invoice_recon.delta_io import read_batch
from invoice_recon.schemas import BRONZE_INVOICES, BRONZE_LEDGER

BATCH = "batch-test"
PERIOD = "2026-03"

INVOICE_DEFAULTS = {
    "invoice_id": "EI-T-1", "supplier_id": "SUP-0001", "supplier_name": "Amberlyn Castings Ltd",
    "invoice_date": "2026-03-10", "currency": "USD", "subtotal": "100.00", "tax_amount": "16.00",
    "total_amount": "116.00", "invoice_reference": "AMC-000100",
}
LEDGER_DEFAULTS = {
    "transaction_id": "GL-T-1", "invoice_reference": "AMC-000100", "supplier_id": "SUP-0001",
    "supplier_name": "Amberlyn Castings Ltd", "posting_date": "2026-03-12", "currency": "USD",
    "recorded_amount": "116.00", "payment_status": "OPEN", "accounting_period": "2026-03",
}


def _bronze(spark, rows, columns, defaults, schema, source, first_line):
    data = []
    for offset, row in enumerate(rows):
        line = row.get("_line_number", first_line + offset)
        values = {**defaults, **{k: v for k, v in row.items() if not k.startswith("_")}}
        raw = row.get("_raw_line", json.dumps(values, sort_keys=True))
        data.append(tuple([BATCH, source, f"Files/landing/{BATCH}/test", line, hashlib.sha256(raw.encode()).hexdigest(),
                           raw, row.get("_parse_error")] + [values.get(c) for c in columns]))
    return spark.createDataFrame(data, schema)


def bronze_invoices(spark, rows):
    """rows: dicts overriding INVOICE_DEFAULTS; optional _line_number, _parse_error, _raw_line."""
    return _bronze(spark, rows, INVOICE_COLUMNS, INVOICE_DEFAULTS, BRONZE_INVOICES, SOURCE_INVOICES, 2)


def bronze_ledger(spark, rows):
    return _bronze(spark, rows, LEDGER_COLUMNS, LEDGER_DEFAULTS, BRONZE_LEDGER, SOURCE_LEDGER, 1)


def silver_frames(spark, rules, invoices, ledger):
    """Silver frames for hand-written rows, checkpointed so later plans stay shallow (fast tests)."""
    from invoice_recon import silver

    inv = silver.normalize_invoices(bronze_invoices(spark, invoices), rules, PERIOD).localCheckpoint()
    led = silver.normalize_ledger(bronze_ledger(spark, ledger), rules, PERIOD).localCheckpoint()
    return inv, led


def gold(spark, rules, invoices, ledger):
    """(status by (side, line), evidence rows, checkpointed reconciliation, silver invoices, silver ledger)."""
    from invoice_recon import reconcile

    inv, led = silver_frames(spark, rules, invoices, ledger)
    frames = reconcile.reconcile(inv, led, rules, BATCH)
    reconciliation = frames.reconciliation.localCheckpoint()
    status = {(r.side, r.line_number): r for r in reconciliation.collect()}
    return status, frames.evidence.collect(), reconciliation, inv, led


def by_line(df, line_column: str = "_line_number") -> dict:
    return {row[line_column]: row for row in df.collect()}


def table_digest(spark, lakehouse, name: str, batch_id: str) -> tuple[int, str]:
    """(row count, SHA-256 over the sorted per-row JSON hashes) of one batch slice."""
    df = read_batch(spark, lakehouse.table(name), batch_id)
    hashes = sorted(r.h for r in df.select(F.sha2(F.to_json(F.struct(*df.columns)), 256).alias("h")).collect())
    return len(hashes), hashlib.sha256("".join(hashes).encode()).hexdigest()
