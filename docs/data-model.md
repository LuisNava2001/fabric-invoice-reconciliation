# Data model

All schemas are declared in [`invoice_recon/schemas.py`](../invoice_recon/schemas.py); tables are created
from them and every write is checked against them (names, order and types).

## Sources (synthetic)

**Source A, electronic invoices** (`invoices.csv`, header required):

| Column | Meaning |
| --- | --- |
| `invoice_id` | Unique document ID issued with the e-invoice (for example `EI-202603-00042`). |
| `supplier_id` | Supplier identifier, `SUP-####`. |
| `supplier_name` | Free text. Added to the brief's column list; used only by similarity suggestions. |
| `invoice_date` | ISO date `YYYY-MM-DD`. |
| `currency` | ISO 4217 code. |
| `subtotal`, `tax_amount`, `total_amount` | Decimal text, up to 4 decimals. |
| `invoice_reference` | The supplier's own invoice number (for example `AMC-004213`). |

**Source B, ERP ledger** (`ledger.jsonl`, one JSON object per line):

| Column | Meaning |
| --- | --- |
| `transaction_id` | Ledger posting ID. |
| `invoice_reference` | Invoice number as typed by whoever posted it (formats vary). |
| `supplier_id`, `supplier_name` | As in source A. |
| `posting_date` | Mixed formats: `YYYY-MM-DD`, `YYYY/MM/DD`, `D-Mon-YYYY`, `DD/MM/YYYY` or `MM/DD/YYYY`. |
| `currency` | ISO 4217 code. |
| `recorded_amount` | JSON string, or a bare JSON number in some rows. |
| `payment_status` | `OPEN`, `PAID`, `PARTIALLY_PAID`. |
| `accounting_period` | `YYYY-MM` or `YYYYMM`. |

The match key is `supplier_id | normalized invoice_reference`. `invoice_id` and `transaction_id` identify
records inside their own source and drive duplicate detection.

## Tables

| Table | Grain | Key columns |
| --- | --- | --- |
| `bronze_invoices`, `bronze_ledger` | one row per non-blank landing line | `_batch_id`, `_line_number`, `_raw_line`, `_record_hash`, `_parse_error`, source columns as strings |
| `bronze_ingestion_errors` | one row per malformed row, blank line or rejected file | `error_type` (`MALFORMED_ROW`, `SCHEMA_DRIFT`, `BLANK_LINE`, `SCHEMA_MISMATCH`) |
| `silver_invoices`, `silver_ledger` | one row per Bronze row | typed columns, `reference_key`, `match_key`, `dq_errors`, `dq_warnings`, `record_status`, `status_reason` |
| `silver_quarantine` | one row per non-VALID Silver row | `record_status`, `status_reason`, `dq_errors`, `_raw_line` |
| `silver_dq_metrics` | one row per catalog rule per source per batch | `failed_records`, `total_records`, `failure_rate` |
| `gold_reconciliation` | one row per source record | `side`, `line_number`, `status`, `reason_code`, counterpart, `amount_difference`, `tolerance`, `flags`, `requires_review` |
| `gold_match_evidence` | one row per compared pair, and per candidate pair of an ambiguous key | `decision`, criteria columns, `explanation` |
| `gold_candidate_suggestions` | one row per similarity suggestion (top 3 per invoice) | `criterion`, `score`, `auto_approved` (always false) |
| `gold_exceptions` | one row per record that requires review | `priority`, `recommended_action`, `suggestion_count` |
| `gold_batch_metrics` | one row per batch | counts per status, `reconciliation_rate`, `eligible_reconciliation_rate` |
| `ops_batch_runs` | one row per batch and stage (MERGE) | `status`, row counts, `details`, `updated_at` |

Every batch table is partitioned by `_batch_id`. `ops_batch_runs` is the only table with a timestamp;
it is excluded from the idempotency comparisons for that reason.

## Lineage

`_source_file` (relative, for example `Files/landing/batch-2026-03/invoices.csv`) and `_line_number`
identify the physical line of every record from Bronze to Gold (`line_number`). `_record_hash` is the
SHA-256 of the raw line.

## Types

* Amounts: `DECIMAL(18,4)`, parsed from text with `try_cast`; never through a float.
* Rates: `DECIMAL(7,4)`; similarity scores: `DECIMAL(4,3)`.
* Dates: `DATE`; the original posting-date text and its parsing basis are kept next to it.
