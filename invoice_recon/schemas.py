"""Explicit schemas for every Delta table. Tables are created from these, never inferred."""

from __future__ import annotations

from pyspark.sql.types import (
    ArrayType,
    BooleanType,
    DateType,
    DecimalType,
    IntegerType,
    LongType,
    StringType,
    StructField,
    StructType,
    TimestampType,
)

from .config import INVOICE_COLUMNS, LEDGER_COLUMNS

AMOUNT = DecimalType(18, 4)
RATE = DecimalType(7, 4)
SCORE = DecimalType(4, 3)
STRINGS = ArrayType(StringType(), containsNull=True)


def _schema(*fields: tuple) -> StructType:
    # Every column is declared nullable; NOT NULL expectations are enforced by the validation
    # checks (validate.py) so that a violation is reported, not just rejected by the writer.
    return StructType([StructField(name, data_type, True) for name, data_type in fields])


_LINEAGE = (
    ("_batch_id", StringType()),
    ("_source_system", StringType()),
    ("_source_file", StringType()),
    ("_line_number", IntegerType()),
    ("_record_hash", StringType()),
)

BRONZE_INVOICES = _schema(
    *_LINEAGE, ("_raw_line", StringType()), ("_parse_error", StringType()),
    *[(column, StringType()) for column in INVOICE_COLUMNS],
)
BRONZE_LEDGER = _schema(
    *_LINEAGE, ("_raw_line", StringType()), ("_parse_error", StringType()),
    *[(column, StringType()) for column in LEDGER_COLUMNS],
)
BRONZE_INGESTION_ERRORS = _schema(
    ("_batch_id", StringType()),
    ("_source_system", StringType()),
    ("_source_file", StringType()),
    ("_line_number", IntegerType()),
    ("error_type", StringType()),
    ("error_detail", StringType()),
    ("_raw_line", StringType()),
)

_QUALITY = (
    ("dq_errors", STRINGS),
    ("dq_warnings", STRINGS),
    ("content_hash", StringType()),
    ("duplicate_group_size", IntegerType()),
    ("duplicate_type", StringType()),
    ("duplicate_of_line", IntegerType()),
    ("record_status", StringType()),
    ("status_reason", StringType()),
)

SILVER_INVOICES = _schema(
    *_LINEAGE,
    ("invoice_id", StringType()),
    ("supplier_id", StringType()),
    ("supplier_name", StringType()),
    ("supplier_name_key", StringType()),
    ("invoice_date", DateType()),
    ("invoice_period", StringType()),
    ("currency", StringType()),
    ("subtotal", AMOUNT),
    ("tax_amount", AMOUNT),
    ("total_amount", AMOUNT),
    ("invoice_reference", StringType()),
    ("reference_key", StringType()),
    ("match_key", StringType()),
    *_QUALITY,
)
SILVER_LEDGER = _schema(
    *_LINEAGE,
    ("transaction_id", StringType()),
    ("supplier_id", StringType()),
    ("supplier_name", StringType()),
    ("supplier_name_key", StringType()),
    ("invoice_reference", StringType()),
    ("reference_key", StringType()),
    ("match_key", StringType()),
    ("posting_date", DateType()),
    ("posting_date_text", StringType()),
    ("posting_date_basis", StringType()),
    ("posting_date_candidates", ArrayType(DateType(), containsNull=True)),
    ("accounting_period", StringType()),
    ("currency", StringType()),
    ("recorded_amount", AMOUNT),
    ("payment_status", StringType()),
    *_QUALITY,
)
SILVER_QUARANTINE = _schema(
    ("_batch_id", StringType()),
    ("_source_system", StringType()),
    ("_line_number", IntegerType()),
    ("record_id", StringType()),
    ("record_status", StringType()),
    ("status_reason", StringType()),
    ("dq_errors", STRINGS),
    ("dq_warnings", STRINGS),
    ("duplicate_of_line", IntegerType()),
    ("_raw_line", StringType()),
)
SILVER_DQ_METRICS = _schema(
    ("_batch_id", StringType()),
    ("_source_system", StringType()),
    ("rule_id", StringType()),
    ("severity", StringType()),
    ("description", StringType()),
    ("failed_records", LongType()),
    ("total_records", LongType()),
    ("failure_rate", RATE),
)

GOLD_RECONCILIATION = _schema(
    ("_batch_id", StringType()),
    ("side", StringType()),
    ("_source_system", StringType()),
    ("line_number", IntegerType()),
    ("record_id", StringType()),
    ("supplier_id", StringType()),
    ("reference_key", StringType()),
    ("match_key", StringType()),
    ("currency", StringType()),
    ("amount", AMOUNT),
    ("status", StringType()),
    ("reason_code", StringType()),
    ("counterpart_line_number", IntegerType()),
    ("counterpart_record_id", StringType()),
    ("candidates_on_other_side", IntegerType()),
    ("amount_difference", AMOUNT),
    ("tolerance", AMOUNT),
    ("flags", STRINGS),
    ("requires_review", BooleanType()),
    ("rules_version", StringType()),
)
GOLD_MATCH_EVIDENCE = _schema(
    ("_batch_id", StringType()),
    ("match_key", StringType()),
    ("rule_id", StringType()),
    ("decision", StringType()),
    ("reason_code", StringType()),
    ("invoice_line", IntegerType()),
    ("ledger_line", IntegerType()),
    ("invoice_id", StringType()),
    ("transaction_id", StringType()),
    ("supplier_id", StringType()),
    ("reference_key", StringType()),
    ("invoice_reference", StringType()),
    ("ledger_reference", StringType()),
    ("invoice_currency", StringType()),
    ("ledger_currency", StringType()),
    ("invoice_total", AMOUNT),
    ("ledger_amount", AMOUNT),
    ("amount_difference", AMOUNT),
    ("tolerance", AMOUNT),
    ("invoice_candidates", IntegerType()),
    ("ledger_candidates", IntegerType()),
    ("flags", STRINGS),
    ("explanation", StringType()),
)
GOLD_CANDIDATE_SUGGESTIONS = _schema(
    ("_batch_id", StringType()),
    ("invoice_line", IntegerType()),
    ("invoice_id", StringType()),
    ("invoice_supplier_id", StringType()),
    ("invoice_supplier_name", StringType()),
    ("invoice_reference", StringType()),
    ("ledger_line", IntegerType()),
    ("transaction_id", StringType()),
    ("ledger_supplier_id", StringType()),
    ("ledger_supplier_name", StringType()),
    ("ledger_reference", StringType()),
    ("criterion", StringType()),
    ("score", SCORE),
    ("name_similarity", SCORE),
    ("reference_similarity", SCORE),
    ("currency_equal", BooleanType()),
    ("amount_difference", AMOUNT),
    ("suggestion_rank", IntegerType()),
    ("auto_approved", BooleanType()),
    ("review_action", StringType()),
    ("explanation", StringType()),
)
GOLD_EXCEPTIONS = _schema(
    ("_batch_id", StringType()),
    ("side", StringType()),
    ("line_number", IntegerType()),
    ("record_id", StringType()),
    ("status", StringType()),
    ("reason_code", StringType()),
    ("flags", STRINGS),
    ("priority", StringType()),
    ("recommended_action", StringType()),
    ("suggestion_count", IntegerType()),
)
GOLD_BATCH_METRICS = _schema(
    ("_batch_id", StringType()),
    ("reconciliation_period", StringType()),
    ("invoice_records", LongType()),
    ("ledger_records", LongType()),
    ("matched_pairs", LongType()),
    ("amount_mismatch_pairs", LongType()),
    ("currency_mismatch_pairs", LongType()),
    ("only_in_invoices", LongType()),
    ("only_in_ledger", LongType()),
    ("ambiguous_records", LongType()),
    ("duplicate_records", LongType()),
    ("invalid_records", LongType()),
    ("records_requiring_review", LongType()),
    ("records_with_dq_errors", LongType()),
    ("records_with_dq_warnings", LongType()),
    ("candidate_suggestions", LongType()),
    ("reconciliation_rate", RATE),
    ("eligible_reconciliation_rate", RATE),
    ("rules_version", StringType()),
)
OPS_BATCH_RUNS = _schema(
    ("batch_id", StringType()),
    ("stage", StringType()),
    ("status", StringType()),
    ("rows_in", LongType()),
    ("rows_out", LongType()),
    ("details", StringType()),
    ("rules_version", StringType()),
    ("code_version", StringType()),
    ("updated_at", TimestampType()),
)

TABLE_SCHEMAS = {
    "bronze_invoices": BRONZE_INVOICES,
    "bronze_ledger": BRONZE_LEDGER,
    "bronze_ingestion_errors": BRONZE_INGESTION_ERRORS,
    "silver_invoices": SILVER_INVOICES,
    "silver_ledger": SILVER_LEDGER,
    "silver_quarantine": SILVER_QUARANTINE,
    "silver_dq_metrics": SILVER_DQ_METRICS,
    "gold_reconciliation": GOLD_RECONCILIATION,
    "gold_match_evidence": GOLD_MATCH_EVIDENCE,
    "gold_candidate_suggestions": GOLD_CANDIDATE_SUGGESTIONS,
    "gold_exceptions": GOLD_EXCEPTIONS,
    "gold_batch_metrics": GOLD_BATCH_METRICS,
    "ops_batch_runs": OPS_BATCH_RUNS,
}
