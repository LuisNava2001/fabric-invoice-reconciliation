"""Silver: typed, normalized and quality-checked records. Rows are never filtered out.

Each Bronze row becomes exactly one Silver row with ``record_status``:

* ``INVALID``   - at least one ERROR rule failed (reason = highest-priority error);
* ``DUPLICATE`` - repeated record ID: later copies of an exact duplicate, or every copy of
  a conflicting one;
* ``VALID``     - eligible for matching (WARNING rules may still have fired).

All conversions use ``try_*`` functions under ANSI mode, so a bad value becomes a rule
failure instead of an exception or a silent NULL.
"""

from __future__ import annotations

from pyspark.sql import Column, DataFrame, SparkSession, Window
from pyspark.sql import functions as F

from . import dq
from .config import Rules
from .schemas import AMOUNT, SILVER_DQ_METRICS, SILVER_INVOICES, SILVER_LEDGER, SILVER_QUARANTINE

_ZERO_WIDTH = r"[​‌‍⁠﻿]"
_SPACE_LIKE = r"[   \t\r\n]"
_SUPPLIER_ID = r"^SUP-?\d{4}$"
_PLAIN_AMOUNT = r"^-?\d+(\.\d{1,4})?$"
_GROUPED_AMOUNT = r"^-?\d{1,3}(,\d{3})+(\.\d{1,4})?$"
_MONTHS = r"(?i)^(\d{1,2})-(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)-(\d{4})$"


def clean_text(column: Column) -> Column:
    """Drop zero-width characters, turn NBSP/tabs into spaces, collapse runs, trim; '' -> NULL."""
    text = F.regexp_replace(column, _ZERO_WIDTH, "")
    text = F.regexp_replace(text, _SPACE_LIKE, " ")
    text = F.trim(F.regexp_replace(text, " {2,}", " "))
    return F.when(F.length(text) > 0, text)


def compact_upper(column: Column) -> Column:
    return F.upper(F.regexp_replace(clean_text(column), r"\s", ""))


def supplier_id(column: Column) -> tuple[Column, Column]:
    """``(compact text, canonical SUP-#### or NULL)``."""
    compact = compact_upper(column)
    return compact, F.when(compact.rlike(_SUPPLIER_ID), F.concat(F.lit("SUP-"), F.substring(compact, -4, 4)))


def reference_key(cleaned: Column) -> Column:
    key = F.upper(F.regexp_replace(cleaned, r"[^A-Za-z0-9]", ""))
    return F.when(F.length(key) > 0, key)


def parse_amount(column: Column) -> tuple[Column, Column]:
    """``(compact text, decimal(18,4) or NULL)``; thousands separators only in valid groups."""
    text = F.regexp_replace(clean_text(column), r"\s", "")
    numeric = F.when(text.rlike(_PLAIN_AMOUNT), text).when(text.rlike(_GROUPED_AMOUNT), F.regexp_replace(text, ",", ""))
    return text, numeric.try_cast(AMOUNT)


def supplier_name_key(cleaned: Column, legal_suffixes: tuple) -> Column:
    text = F.regexp_replace(F.upper(cleaned), r"[^A-Z0-9 ]", " ")
    if legal_suffixes:
        text = F.regexp_replace(text, r"\b(" + "|".join(legal_suffixes) + r")\b", " ")
    text = F.trim(F.regexp_replace(text, " {2,}", " "))
    return F.when(F.length(text) > 0, text)


def iso_date(text: Column) -> Column:
    return F.when(text.rlike(r"^\d{4}-\d{2}-\d{2}$"), F.try_to_date(text, "yyyy-MM-dd"))


def posting_date(text: Column) -> dict:
    """Parse ledger posting dates without guessing.

    Accepted: YYYY-MM-DD, YYYY/MM/DD, D-Mon-YYYY, and D/M/YYYY or M/D/YYYY. A slash date is
    accepted only when its two readings agree or exactly one of them is a calendar date;
    when both are valid and differ it is AMBIGUOUS: the date stays NULL and both candidates
    are kept for review.
    """
    iso = text.rlike(r"^\d{4}-\d{2}-\d{2}$")
    ymd = text.rlike(r"^\d{4}/\d{2}/\d{2}$")
    named = text.rlike(_MONTHS)
    slash = text.rlike(r"^\d{1,2}/\d{1,2}/\d{4}$")
    named_text = F.concat_ws("-", F.regexp_extract(text, _MONTHS, 1),
                             F.initcap(F.lower(F.regexp_extract(text, _MONTHS, 2))), F.regexp_extract(text, _MONTHS, 3))
    d_iso = F.when(iso, F.try_to_date(text, "yyyy-MM-dd"))
    d_ymd = F.when(ymd, F.try_to_date(text, "yyyy/MM/dd"))
    d_named = F.when(named, F.try_to_date(named_text, "d-MMM-yyyy"))
    d_dm = F.when(slash, F.try_to_date(text, "d/M/yyyy"))
    d_md = F.when(slash, F.try_to_date(text, "M/d/yyyy"))
    both = d_dm.isNotNull() & d_md.isNotNull()
    ambiguous = slash & both & (d_dm != d_md)
    value = (F.when(iso, d_iso).when(ymd, d_ymd).when(named, d_named)
             .when(ambiguous, F.lit(None).cast("date")).when(slash, F.coalesce(d_dm, d_md)))
    basis = (F.when(iso & d_iso.isNotNull(), "YYYY-MM-DD")
             .when(ymd & d_ymd.isNotNull(), "YYYY/MM/DD")
             .when(named & d_named.isNotNull(), "D-MON-YYYY")
             .when(ambiguous, "AMBIGUOUS_D/M_OR_M/D")
             .when(slash & both, "D/M_EQUALS_M/D")
             .when(slash & d_dm.isNotNull(), "D/M/YYYY_ONLY_VALID_READING")
             .when(slash & d_md.isNotNull(), "M/D/YYYY_ONLY_VALID_READING"))
    candidates = F.when(ambiguous, F.array(d_dm, d_md))
    return {"value": value, "basis": basis, "ambiguous": F.coalesce(ambiguous, F.lit(False)), "candidates": candidates}


def accounting_period(column: Column) -> tuple[Column, Column]:
    text = F.regexp_replace(clean_text(column), r"\s", "")
    shaped = text.rlike(r"^\d{4}-\d{1,2}$") | text.rlike(r"^\d{6}$")
    year = F.when(shaped, F.regexp_extract(text, r"^(\d{4})-?(\d{1,2})$", 1)).try_cast("int")
    month = F.when(shaped, F.regexp_extract(text, r"^(\d{4})-?(\d{1,2})$", 2)).try_cast("int")
    valid = shaped & month.between(1, 12) & year.between(2000, 2099)
    return text, F.when(valid, F.format_string("%04d-%02d", year, month))


def _tolerance_map(rules: Rules) -> Column:
    pairs = []
    for code, rule in sorted(rules.currencies.items()):
        pairs += [F.lit(code), F.lit(str(rule.tolerance)).cast(AMOUNT)]
    return F.create_map(*pairs)


def _codes(checks: list[tuple[str, Column]]) -> Column:
    return F.array_compact(F.array(*[F.when(condition, F.lit(code)) for code, condition in checks]))


def _content_hash(columns: list[Column]) -> Column:
    return F.sha2(F.concat_ws("\u0001", *[F.coalesce(c, F.lit("\u0000")) for c in columns]), 256)


def _with_duplicates_and_status(df: DataFrame, id_column: str) -> DataFrame:
    """Duplicate detection on the normalized record ID; NULL IDs never form a group."""
    df = df.withColumn("_dup_key", F.when(F.col("_parse_error").isNull(), F.col(id_column)))
    window = Window.partitionBy("_dup_key")
    known = F.col("_dup_key").isNotNull()
    df = (df.withColumn("duplicate_group_size", F.when(known, F.count(F.lit(1)).over(window)).cast("int"))
          .withColumn("_distinct", F.when(known, F.size(F.collect_set("content_hash").over(window))))
          .withColumn("_first_line", F.when(known, F.min("_line_number").over(window))))
    kind = F.when(F.col("duplicate_group_size") > 1, F.when(F.col("_distinct") == 1, "EXACT").otherwise("CONFLICT"))
    df = df.withColumn("duplicate_type", kind)
    later_copy = (F.col("duplicate_type") == "EXACT") & (F.col("_line_number") != F.col("_first_line"))
    is_duplicate = F.coalesce(later_copy | (F.col("duplicate_type") == "CONFLICT"), F.lit(False))
    df = df.withColumn("duplicate_of_line", F.when(later_copy, F.col("_first_line")).cast("int"))
    status = (F.when(F.size("dq_errors") > 0, "INVALID").when(is_duplicate, "DUPLICATE").otherwise("VALID"))
    df = df.withColumn("record_status", status)
    return df.withColumn("status_reason", F.when(F.col("record_status") == "INVALID", F.try_element_at("dq_errors", F.lit(1)))
                         .when(F.col("record_status") == "DUPLICATE", F.concat(F.lit("DUPLICATE_"), F.col("duplicate_type"))))


def normalize_invoices(bronze: DataFrame, rules: Rules, period: str) -> DataFrame:
    """Bronze invoices -> Silver invoices (plus ``_raw_line`` kept for the quarantine table)."""
    tolerance = F.try_element_at(_tolerance_map(rules), F.col("currency"))
    sid_compact, sid = supplier_id(F.col("supplier_id"))
    ref_clean = clean_text(F.col("invoice_reference"))
    date_text = clean_text(F.col("invoice_date"))
    amounts = {c: parse_amount(F.col(c)) for c in ("subtotal", "tax_amount", "total_amount")}
    df = bronze.select(
        "_batch_id", "_source_system", "_source_file", "_line_number", "_record_hash", "_raw_line", "_parse_error",
        compact_upper(F.col("invoice_id")).alias("invoice_id"),
        sid_compact.alias("_supplier_compact"),
        sid.alias("supplier_id"),
        clean_text(F.col("supplier_name")).alias("supplier_name"),
        date_text.alias("_date_text"),
        iso_date(date_text).alias("invoice_date"),
        compact_upper(F.col("currency")).alias("currency"),
        *[amounts[c][0].alias(f"_{c}_text") for c in amounts],
        *[amounts[c][1].alias(c) for c in amounts],
        ref_clean.alias("invoice_reference"),
        reference_key(ref_clean).alias("reference_key"),
    )
    df = df.withColumn("supplier_name_key", supplier_name_key(F.col("supplier_name"), rules.legal_suffixes))
    df = df.withColumn("invoice_period", F.date_format("invoice_date", "yyyy-MM"))
    valid_currency = F.col("currency").isin(*rules.currencies)
    texts = [F.col(f"_{c}_text") for c in amounts]
    values = [F.col(c) for c in amounts]
    checks = [
        ("MISSING_INVOICE_ID", F.col("invoice_id").isNull()),
        ("MISSING_SUPPLIER_ID", F.col("_supplier_compact").isNull()),
        ("MALFORMED_SUPPLIER_ID", F.col("_supplier_compact").isNotNull() & F.col("supplier_id").isNull()),
        ("MISSING_REFERENCE", F.col("reference_key").isNull()),
        ("MISSING_DATE", F.col("_date_text").isNull()),
        ("INVALID_DATE", F.col("_date_text").isNotNull() & F.col("invoice_date").isNull()),
        ("MISSING_CURRENCY", F.col("currency").isNull()),
        ("INVALID_CURRENCY", F.col("currency").isNotNull() & ~valid_currency),
        ("MISSING_AMOUNT", F.greatest(*[t.isNull() for t in texts])),
        ("INVALID_AMOUNT", F.greatest(*[t.isNotNull() & v.isNull() for t, v in zip(texts, values)])),
        ("AMOUNT_OUT_OF_RANGE", (F.col("subtotal") <= 0) | (F.col("tax_amount") < 0) | (F.col("total_amount") <= 0)
         | F.greatest(*[v > F.lit(str(rules.amount_max)).cast(AMOUNT) for v in values])),
        ("TOTAL_INCONSISTENT", valid_currency
         & (F.abs(F.col("subtotal") + F.col("tax_amount") - F.col("total_amount")) > tolerance)),
    ]
    malformed = F.col("_parse_error").isNotNull()
    df = df.withColumn("dq_errors", F.when(malformed, F.array(F.lit("MALFORMED_ROW"))).otherwise(_codes(checks)))
    df = df.withColumn("dq_warnings", F.when(malformed, F.array().cast("array<string>")).otherwise(
        _codes([("OUT_OF_PERIOD", F.col("invoice_period").isNotNull() & (F.col("invoice_period") != period))])))
    keyed = F.col("supplier_id").isNotNull() & F.col("reference_key").isNotNull() & ~malformed
    df = df.withColumn("match_key", F.when(keyed, F.concat_ws("|", "supplier_id", "reference_key")))
    df = df.withColumn("content_hash", _content_hash([
        F.col("invoice_id"), F.col("_supplier_compact"), F.col("supplier_name"), F.col("_date_text"), F.col("currency"),
        *texts, F.col("invoice_reference")]))
    df = _with_duplicates_and_status(df, "invoice_id")
    return df.select(*SILVER_INVOICES.fieldNames(), "_raw_line")


def normalize_ledger(bronze: DataFrame, rules: Rules, period: str) -> DataFrame:
    """Bronze ledger -> Silver ledger (plus ``_raw_line`` kept for the quarantine table)."""
    sid_compact, sid = supplier_id(F.col("supplier_id"))
    ref_clean = clean_text(F.col("invoice_reference"))
    date_text = clean_text(F.col("posting_date"))
    parsed_date = posting_date(date_text)
    period_text, period_value = accounting_period(F.col("accounting_period"))
    amount_text, amount = parse_amount(F.col("recorded_amount"))
    df = bronze.select(
        "_batch_id", "_source_system", "_source_file", "_line_number", "_record_hash", "_raw_line", "_parse_error",
        compact_upper(F.col("transaction_id")).alias("transaction_id"),
        sid_compact.alias("_supplier_compact"),
        sid.alias("supplier_id"),
        clean_text(F.col("supplier_name")).alias("supplier_name"),
        ref_clean.alias("invoice_reference"),
        reference_key(ref_clean).alias("reference_key"),
        parsed_date["value"].alias("posting_date"),
        date_text.alias("posting_date_text"),
        parsed_date["basis"].alias("posting_date_basis"),
        parsed_date["candidates"].alias("posting_date_candidates"),
        parsed_date["ambiguous"].alias("_ambiguous"),
        period_text.alias("_period_text"),
        period_value.alias("accounting_period"),
        compact_upper(F.col("currency")).alias("currency"),
        amount_text.alias("_amount_text"),
        amount.alias("recorded_amount"),
        compact_upper(F.col("payment_status")).alias("payment_status"),
    )
    df = df.withColumn("supplier_name_key", supplier_name_key(F.col("supplier_name"), rules.legal_suffixes))
    valid_currency = F.col("currency").isin(*rules.currencies)
    checks = [
        ("MISSING_TRANSACTION_ID", F.col("transaction_id").isNull()),
        ("MISSING_SUPPLIER_ID", F.col("_supplier_compact").isNull()),
        ("MALFORMED_SUPPLIER_ID", F.col("_supplier_compact").isNotNull() & F.col("supplier_id").isNull()),
        ("MISSING_REFERENCE", F.col("reference_key").isNull()),
        ("MISSING_DATE", F.col("posting_date_text").isNull()),
        ("INVALID_DATE", F.col("posting_date_text").isNotNull() & F.col("posting_date").isNull() & ~F.col("_ambiguous")),
        ("MISSING_CURRENCY", F.col("currency").isNull()),
        ("INVALID_CURRENCY", F.col("currency").isNotNull() & ~valid_currency),
        ("MISSING_AMOUNT", F.col("_amount_text").isNull()),
        ("INVALID_AMOUNT", F.col("_amount_text").isNotNull() & F.col("recorded_amount").isNull()),
        ("AMOUNT_OUT_OF_RANGE", (F.col("recorded_amount") <= 0)
         | (F.col("recorded_amount") > F.lit(str(rules.amount_max)).cast(AMOUNT))),
        ("MISSING_PERIOD", F.col("_period_text").isNull()),
        ("INVALID_PERIOD", F.col("_period_text").isNotNull() & F.col("accounting_period").isNull()),
    ]
    warnings = [
        ("AMBIGUOUS_DATE", F.col("_ambiguous")),
        ("PERIOD_INCONSISTENT", F.col("posting_date").isNotNull() & F.col("accounting_period").isNotNull()
         & (F.date_format("posting_date", "yyyy-MM") != F.col("accounting_period"))),
        ("OUT_OF_PERIOD", F.col("accounting_period").isNotNull() & (F.col("accounting_period") != period)),
        ("MISSING_PAYMENT_STATUS", F.col("payment_status").isNull()),
        ("UNKNOWN_PAYMENT_STATUS", F.col("payment_status").isNotNull() & ~F.col("payment_status").isin(*rules.payment_statuses)),
    ]
    malformed = F.col("_parse_error").isNotNull()
    df = df.withColumn("dq_errors", F.when(malformed, F.array(F.lit("MALFORMED_ROW"))).otherwise(_codes(checks)))
    df = df.withColumn("dq_warnings", F.when(malformed, F.array().cast("array<string>")).otherwise(_codes(warnings)))
    keyed = F.col("supplier_id").isNotNull() & F.col("reference_key").isNotNull() & ~malformed
    df = df.withColumn("match_key", F.when(keyed, F.concat_ws("|", "supplier_id", "reference_key")))
    df = df.withColumn("content_hash", _content_hash([
        F.col("transaction_id"), F.col("_supplier_compact"), F.col("supplier_name"), F.col("invoice_reference"),
        F.col("posting_date_text"), F.col("currency"), F.col("_amount_text"), F.col("payment_status"), F.col("_period_text")]))
    df = _with_duplicates_and_status(df, "transaction_id")
    return df.select(*SILVER_LEDGER.fieldNames(), "_raw_line")


def quarantine(invoices: DataFrame, ledger: DataFrame) -> DataFrame:
    """Every non-VALID Silver row, with its reason and the original raw line."""
    def side(df: DataFrame, id_column: str) -> DataFrame:
        return df.filter(F.col("record_status") != "VALID").select(
            "_batch_id", "_source_system", "_line_number", F.col(id_column).alias("record_id"), "record_status",
            "status_reason", "dq_errors", "dq_warnings", "duplicate_of_line", "_raw_line")
    return side(invoices, "invoice_id").unionByName(side(ledger, "transaction_id")).select(*SILVER_QUARANTINE.fieldNames())


def dq_metrics(spark: SparkSession, silver: DataFrame, source: str, batch_id: str) -> DataFrame:
    """One row per catalog rule (zero failures included) for this batch and source."""
    total = silver.count()
    failures = (silver.select(F.explode("dq_errors").alias("rule_id"))
                .unionByName(silver.select(F.explode("dq_warnings").alias("rule_id")))
                .unionByName(silver.filter(F.col("record_status") == "DUPLICATE").select(F.col("status_reason").alias("rule_id")))
                .groupBy("rule_id").agg(F.count(F.lit(1)).alias("failed_records")))
    catalog = spark.createDataFrame(
        [(rule, severity, description) for rule, severity, description in dq.RULES[source]],
        "rule_id STRING, severity STRING, description STRING")
    failed = F.coalesce(F.col("failed_records"), F.lit(0)).cast("long")
    rate = F.when(F.lit(total) > 0, F.round(failed / F.lit(total), 4)).otherwise(F.lit(0)).cast("decimal(7,4)")
    return catalog.join(failures, "rule_id", "left").select(
        F.lit(batch_id).alias("_batch_id"), F.lit(source).alias("_source_system"), "rule_id", "severity", "description",
        failed.alias("failed_records"), F.lit(total).cast("long").alias("total_records"), rate.alias("failure_rate"),
    ).select(*SILVER_DQ_METRICS.fieldNames())
