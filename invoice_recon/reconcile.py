"""Gold: deterministic reconciliation, match evidence, suggestions, exceptions and metrics.

Matching rule R1 (the only rule that can produce MATCHED):

    same canonical supplier_id  AND  same normalized invoice reference
    AND same currency           AND  |invoice total - ledger amount| <= currency tolerance

Only Silver rows with record_status = VALID take part. Their match key is never NULL
(VALID requires both parts), so NULLs cannot pair up. Keys are first counted per side and
the two count tables are FULL OUTER JOINed: every key lands in exactly one class (one-to-one,
one side only, or several candidates) without multiplying rows. Records are joined back
only for one-to-one keys, so no record can be matched twice.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from pyspark.sql import Column, DataFrame, Window
from pyspark.sql import functions as F

from .config import REVIEW_FLAGS, SIDE_INVOICE, SIDE_LEDGER, Rules
from .schemas import (
    AMOUNT,
    GOLD_BATCH_METRICS,
    GOLD_CANDIDATE_SUGGESTIONS,
    GOLD_EXCEPTIONS,
    GOLD_MATCH_EVIDENCE,
    GOLD_RECONCILIATION,
    SCORE,
)

RULE_ID = "R1_SUPPLIER_REFERENCE_CURRENCY_AMOUNT"

ACTIONS = {
    "AMOUNT_MISMATCH": "Compare the invoice total with the ledger amount; correct the posting or request a credit note.",
    "CURRENCY_MISMATCH": "Confirm the document currency; amounts in different currencies are never compared.",
    "ONLY_IN_INVOICES": "Check whether the invoice was posted; review candidate suggestions if any.",
    "ONLY_IN_LEDGER": "Find the source invoice for this posting; review candidate suggestions if any.",
    "AMBIGUOUS": "Several records share supplier and reference (possible double posting); decide which belong together.",
    "DUPLICATE_EXACT": "Exact repeat of an earlier line; confirm and discard the copy.",
    "DUPLICATE_CONFLICT": "Same record ID with different content; ask the source owner which version is valid.",
    "INVALID_RECORD": "Fix the source record and resend it in a corrected batch.",
    "MATCHED": "Matched by rule R1; validate the flagged attribute before closing.",
}


@dataclass
class GoldFrames:
    """Suggestions and exceptions are built from the *stored* reconciliation table (see pipeline.py):
    PySpark analyzes every DataFrame eagerly, so deriving them from this deep in-memory plan is slow."""

    reconciliation: DataFrame
    evidence: DataFrame


def _tolerance(rules: Rules, currency: Column) -> Column:
    pairs = []
    for code, rule in sorted(rules.currencies.items()):
        pairs += [F.lit(code), F.lit(str(rule.tolerance)).cast(AMOUNT)]
    return F.try_element_at(F.create_map(*pairs), currency)


def similarity(a: Column, b: Column) -> Column:
    """1 - Levenshtein distance / longer length, rounded to 3 decimals (NULL if either is NULL)."""
    longest = F.greatest(F.length(a), F.length(b))
    ratio = F.lit(1) - F.levenshtein(a, b) / longest
    return F.when(a.isNotNull() & b.isNotNull() & (longest > 0), F.round(ratio, 3)).cast(SCORE)


def classify_keys(invoices: DataFrame, ledger: DataFrame) -> DataFrame:
    """One row per match key of VALID records: counts per side and the key class."""
    inv = invoices.filter(F.col("record_status") == "VALID").groupBy("match_key").agg(F.count(F.lit(1)).alias("n_inv"))
    led = ledger.filter(F.col("record_status") == "VALID").groupBy("match_key").agg(F.count(F.lit(1)).alias("n_led"))
    keys = inv.join(led, on="match_key", how="full_outer").select(
        "match_key", F.coalesce("n_inv", F.lit(0)).cast("int").alias("n_inv"),
        F.coalesce("n_led", F.lit(0)).cast("int").alias("n_led"))
    key_class = (F.when((F.col("n_inv") == 1) & (F.col("n_led") == 1), "PAIR")
                 .when((F.col("n_inv") > 1) | (F.col("n_led") > 1), "AMBIGUOUS")
                 .when(F.col("n_led") == 0, "ONLY_IN_INVOICES")
                 .otherwise("ONLY_IN_LEDGER"))
    return keys.withColumn("key_class", key_class)


def _candidates(invoices: DataFrame, ledger: DataFrame, keys: DataFrame, key_class: str) -> DataFrame:
    """Invoice x ledger rows sharing a key of the given class (one row per PAIR key)."""
    selected = keys.filter(F.col("key_class") == key_class).select("match_key", "n_inv", "n_led")
    inv = invoices.filter(F.col("record_status") == "VALID").join(selected, "match_key").select(
        "match_key", "n_inv", "n_led",
        F.col("_line_number").alias("invoice_line"), "invoice_id", "supplier_id", "reference_key",
        F.col("invoice_reference").alias("invoice_reference"), F.col("currency").alias("invoice_currency"),
        F.col("total_amount").alias("invoice_total"), F.col("dq_warnings").alias("invoice_warnings"))
    led = ledger.filter(F.col("record_status") == "VALID").select(
        "match_key", F.col("_line_number").alias("ledger_line"), "transaction_id",
        F.col("invoice_reference").alias("ledger_reference"), F.col("currency").alias("ledger_currency"),
        F.col("recorded_amount").alias("ledger_amount"), F.col("dq_warnings").alias("ledger_warnings"))
    return inv.join(led, "match_key")


def _compare(pairs: DataFrame, rules: Rules, decided: bool) -> DataFrame:
    currency_equal = F.col("invoice_currency") == F.col("ledger_currency")
    tolerance = F.when(currency_equal, _tolerance(rules, F.col("invoice_currency")))
    difference = F.when(currency_equal, F.abs(F.col("invoice_total") - F.col("ledger_amount"))).cast(AMOUNT)
    df = pairs.withColumn("tolerance", tolerance).withColumn("amount_difference", difference)
    if decided:
        decision = (F.when(~currency_equal, "CURRENCY_MISMATCH")
                    .when(F.col("amount_difference") <= F.col("tolerance"), "MATCHED")
                    .otherwise("AMOUNT_MISMATCH"))
        reason = (F.when(F.col("decision") == "CURRENCY_MISMATCH", "CURRENCY_DIFFERS_NO_CONVERSION")
                  .when(F.col("decision") == "AMOUNT_MISMATCH", "DIFFERENCE_ABOVE_TOLERANCE")
                  .when(F.col("amount_difference") == 0, "EXACT_AMOUNT")
                  .otherwise("WITHIN_TOLERANCE"))
    else:
        decision = F.lit("NOT_DECIDED_MULTIPLE_CANDIDATES")
        reason = (F.when((F.col("n_inv") > 1) & (F.col("n_led") > 1), "MULTIPLE_CANDIDATES_BOTH_SIDES")
                  .when(F.col("n_inv") > 1, "MULTIPLE_INVOICES_FOR_KEY")
                  .otherwise("MULTIPLE_LEDGER_ENTRIES_FOR_KEY"))
    df = df.withColumn("decision", decision).withColumn("reason_code", reason)
    pair_flags = F.array_compact(F.array(
        F.when(F.col("invoice_reference") != F.col("ledger_reference"), F.lit("REFERENCE_FORMAT_VARIANT")),
        F.when((F.col("decision") == "MATCHED") & (F.col("amount_difference") > 0), F.lit("ROUNDING_DIFFERENCE")),
    ))
    flags = F.array_sort(F.array_distinct(F.concat(pair_flags, F.col("invoice_warnings"), F.col("ledger_warnings"))))
    explanation = F.concat_ws(
        "; ",
        F.format_string("supplier_id %s on both sides", F.col("supplier_id")),
        F.format_string("reference '%s' vs '%s' normalize to %s", F.col("invoice_reference"), F.col("ledger_reference"),
                        F.col("reference_key")),
        F.when(currency_equal, F.format_string("currency %s on both sides", F.col("invoice_currency"))).otherwise(
            F.format_string("currency %s vs %s: amounts not compared (no conversion rule)",
                            F.col("invoice_currency"), F.col("ledger_currency"))),
        F.when(currency_equal, F.format_string("|%s - %s| = %s vs tolerance %s", F.col("invoice_total"),
                                               F.col("ledger_amount"), F.col("amount_difference"), F.col("tolerance"))),
        F.when(~F.lit(decided), F.format_string("%d invoice(s) and %d ledger record(s) share this key: not decided",
                                                F.col("n_inv"), F.col("n_led"))),
    )
    return df.withColumn("flags", flags).withColumn("explanation", explanation)


def build_evidence(pairs: DataFrame, ambiguous: DataFrame, batch_id: str) -> DataFrame:
    columns = [
        F.lit(batch_id).alias("_batch_id"), "match_key", F.lit(RULE_ID).alias("rule_id"), "decision", "reason_code",
        "invoice_line", "ledger_line", "invoice_id", "transaction_id", "supplier_id", "reference_key",
        "invoice_reference", "ledger_reference", "invoice_currency", "ledger_currency", "invoice_total",
        "ledger_amount", "amount_difference", "tolerance", F.col("n_inv").alias("invoice_candidates"),
        F.col("n_led").alias("ledger_candidates"), "flags", "explanation",
    ]
    return pairs.select(*columns).unionByName(ambiguous.select(*columns)).select(*GOLD_MATCH_EVIDENCE.fieldNames())


def _side_status(silver: DataFrame, side: str, keys: DataFrame, pairs: DataFrame, other: DataFrame,
                 rules: Rules, batch_id: str) -> DataFrame:
    is_invoice = side == SIDE_INVOICE
    own_line, other_line = ("invoice_line", "ledger_line") if is_invoice else ("ledger_line", "invoice_line")
    counterpart_id = "transaction_id" if is_invoice else "invoice_id"
    pair_info = pairs.select(
        F.col(own_line).alias("_line_number"), F.col("decision").alias("_decision"), F.col("reason_code").alias("_pair_reason"),
        F.col(other_line).alias("counterpart_line_number"), F.col(counterpart_id).alias("counterpart_record_id"),
        F.col("amount_difference").alias("_difference"), F.col("tolerance").alias("_tolerance"), F.col("flags").alias("_pair_flags"))
    blocked = other.filter((F.col("record_status") != "VALID") & F.col("match_key").isNotNull()).select(
        "match_key").distinct().withColumn("_other_blocked", F.lit(True))
    only_class = "ONLY_IN_INVOICES" if is_invoice else "ONLY_IN_LEDGER"
    other_count = "n_led" if is_invoice else "n_inv"
    valid = F.col("record_status") == "VALID"
    df = (silver.join(keys.select("match_key", "n_inv", "n_led", "key_class"), "match_key", "left")
          .join(pair_info, "_line_number", "left")
          .join(blocked, "match_key", "left"))
    status = (F.when(F.col("record_status") == "INVALID", "INVALID_RECORD")
              .when(F.col("record_status") == "DUPLICATE", "DUPLICATE")
              .when(F.col("key_class") == "PAIR", F.col("_decision"))
              .when(F.col("key_class") == "AMBIGUOUS", "AMBIGUOUS")
              .when(F.col("key_class") == only_class, only_class)
              .otherwise("UNCLASSIFIED"))  # never expected; validate.py fails the batch if it appears
    ambiguous_reason = (F.when((F.col("n_inv") > 1) & (F.col("n_led") > 1), "MULTIPLE_CANDIDATES_BOTH_SIDES")
                        .when(F.col("n_inv") > 1, "MULTIPLE_INVOICES_FOR_KEY")
                        .otherwise("MULTIPLE_LEDGER_ENTRIES_FOR_KEY"))
    reason = (F.when(~valid, F.col("status_reason"))
              .when(F.col("key_class") == "PAIR", F.col("_pair_reason"))
              .when(F.col("key_class") == "AMBIGUOUS", ambiguous_reason)
              .when(F.coalesce(F.col("_other_blocked"), F.lit(False)), "COUNTERPART_NOT_ELIGIBLE")
              .otherwise("NO_COUNTERPART"))
    df = df.withColumn("status", status).withColumn("reason_code", reason)
    flags = F.when(F.col("key_class") == "PAIR", F.col("_pair_flags")).otherwise(F.array_sort(F.col("dq_warnings")))
    review = F.array(*[F.lit(flag) for flag in REVIEW_FLAGS])
    requires_review = (F.col("status") != "MATCHED") | F.coalesce(F.arrays_overlap(F.col("flags"), review), F.lit(False))
    df = df.withColumn("flags", flags).withColumn("requires_review", requires_review)
    return df.select(
        F.lit(batch_id).alias("_batch_id"), F.lit(side).alias("side"), "_source_system",
        F.col("_line_number").alias("line_number"),
        F.col("invoice_id" if is_invoice else "transaction_id").alias("record_id"),
        "supplier_id", "reference_key", "match_key", "currency",
        F.col("total_amount" if is_invoice else "recorded_amount").alias("amount"),
        "status", "reason_code", "counterpart_line_number", "counterpart_record_id",
        F.when(valid, F.col(other_count)).cast("int").alias("candidates_on_other_side"),
        F.col("_difference").alias("amount_difference"), F.col("_tolerance").alias("tolerance"),
        "flags", "requires_review", F.lit(rules.version).alias("rules_version"),
    )


def build_suggestions(reconciliation: DataFrame, invoices: DataFrame, ledger: DataFrame, rules: Rules,
                      batch_id: str) -> DataFrame:
    """Secondary, similarity-based candidates for records left ONLY_IN_*. Never auto-approved."""
    open_inv = reconciliation.filter((F.col("side") == SIDE_INVOICE) & (F.col("status") == "ONLY_IN_INVOICES")).select(
        F.col("line_number").alias("_line_number"))
    open_led = reconciliation.filter((F.col("side") == SIDE_LEDGER) & (F.col("status") == "ONLY_IN_LEDGER")).select(
        F.col("line_number").alias("_line_number"))
    inv = invoices.join(open_inv, "_line_number").select(
        F.col("_line_number").alias("invoice_line"), "invoice_id", F.col("supplier_id").alias("i_supplier"),
        F.col("supplier_name").alias("invoice_supplier_name"), F.col("supplier_name_key").alias("i_name"),
        F.col("invoice_reference"), F.col("reference_key").alias("i_ref"), F.col("currency").alias("i_currency"),
        F.col("total_amount").alias("i_amount"))
    led = ledger.join(open_led, "_line_number").select(
        F.col("_line_number").alias("ledger_line"), "transaction_id", F.col("supplier_id").alias("l_supplier"),
        F.col("supplier_name").alias("ledger_supplier_name"), F.col("supplier_name_key").alias("l_name"),
        F.col("invoice_reference").alias("ledger_reference"), F.col("reference_key").alias("l_ref"),
        F.col("currency").alias("l_currency"), F.col("recorded_amount").alias("l_amount"))
    name_threshold = F.lit(str(rules.name_similarity_threshold)).cast(SCORE)
    reference_threshold = F.lit(str(rules.reference_similarity_threshold)).cast(SCORE)
    currency_equal = F.col("i_currency") == F.col("l_currency")
    difference = F.when(currency_equal, F.abs(F.col("i_amount") - F.col("l_amount"))).cast(AMOUNT)

    same_reference = (inv.join(led, (F.col("i_ref") == F.col("l_ref")) & (F.col("i_supplier") != F.col("l_supplier")))
                      .withColumn("name_similarity", similarity(F.col("i_name"), F.col("l_name")))
                      .filter(F.col("name_similarity") >= name_threshold)
                      .withColumn("reference_similarity", F.lit(1).cast(SCORE))
                      .withColumn("criterion", F.lit("SAME_REFERENCE_DIFFERENT_SUPPLIER"))
                      .withColumn("score", F.col("name_similarity")))
    same_supplier = (inv.join(led, (F.col("i_supplier") == F.col("l_supplier")) & currency_equal)
                     .withColumn("_difference", difference)
                     .filter(F.col("_difference") <= _tolerance(rules, F.col("i_currency")))
                     .withColumn("reference_similarity", similarity(F.col("i_ref"), F.col("l_ref")))
                     .filter(F.col("reference_similarity") >= reference_threshold)
                     .withColumn("name_similarity", similarity(F.col("i_name"), F.col("l_name")))
                     .withColumn("criterion", F.lit("SAME_SUPPLIER_AMOUNT_SIMILAR_REFERENCE"))
                     .withColumn("score", F.col("reference_similarity"))
                     .drop("_difference"))
    candidates = same_reference.unionByName(same_supplier)
    rank = F.row_number().over(Window.partitionBy("invoice_line").orderBy(F.col("score").desc(), F.col("ledger_line")))
    explanation = F.concat_ws(
        "; ",
        F.format_string("criterion %s, score %s", F.col("criterion"), F.col("score")),
        F.format_string("supplier %s '%s' vs %s '%s' (name similarity %s)", F.col("i_supplier"),
                        F.col("invoice_supplier_name"), F.col("l_supplier"), F.col("ledger_supplier_name"),
                        F.col("name_similarity")),
        F.format_string("reference '%s' vs '%s' (similarity %s)", F.col("invoice_reference"),
                        F.col("ledger_reference"), F.col("reference_similarity")),
        F.lit("suggestion only: deterministic identifiers disagree, a person must decide"),
    )
    return (candidates.withColumn("suggestion_rank", rank)
            .filter(F.col("suggestion_rank") <= rules.max_suggestions_per_record)
            .select(
                F.lit(batch_id).alias("_batch_id"), "invoice_line", "invoice_id",
                F.col("i_supplier").alias("invoice_supplier_id"), "invoice_supplier_name", "invoice_reference",
                "ledger_line", "transaction_id", F.col("l_supplier").alias("ledger_supplier_id"),
                "ledger_supplier_name", "ledger_reference", "criterion", "score", "name_similarity",
                "reference_similarity", currency_equal.alias("currency_equal"), difference.alias("amount_difference"),
                F.col("suggestion_rank").cast("int").alias("suggestion_rank"), F.lit(False).alias("auto_approved"),
                F.lit("HUMAN_REVIEW_REQUIRED").alias("review_action"), explanation.alias("explanation"))
            .select(*GOLD_CANDIDATE_SUGGESTIONS.fieldNames()))


def build_exceptions(reconciliation: DataFrame, suggestions: DataFrame) -> DataFrame:
    counts = (suggestions.select(F.lit(SIDE_INVOICE).alias("side"), F.col("invoice_line").alias("line_number"))
              .unionByName(suggestions.select(F.lit(SIDE_LEDGER).alias("side"), F.col("ledger_line").alias("line_number")))
              .groupBy("side", "line_number").agg(F.count(F.lit(1)).cast("int").alias("suggestion_count")))
    action_key = F.when(F.col("status") == "DUPLICATE", F.col("reason_code")).otherwise(F.col("status"))
    actions = F.create_map(*[part for key, text in ACTIONS.items() for part in (F.lit(key), F.lit(text))])
    action = F.try_element_at(actions, action_key)
    action = F.when(F.col("status") == "INVALID_RECORD",
                    F.concat(action, F.lit(" Rule: "), F.col("reason_code"), F.lit("."))).otherwise(action)
    action = F.when(F.col("status") == "MATCHED",
                    F.concat(action, F.lit(" Flags: "), F.array_join(F.col("flags"), ", "), F.lit("."))).otherwise(action)
    priority = (F.when(F.col("status").isin("AMOUNT_MISMATCH", "CURRENCY_MISMATCH", "AMBIGUOUS")
                       | (F.col("reason_code") == "DUPLICATE_CONFLICT"), "HIGH")
                .when(F.col("status") == "MATCHED", "LOW")
                .otherwise("MEDIUM"))
    return (reconciliation.filter(F.col("requires_review"))
            .join(counts, ["side", "line_number"], "left")
            .select("_batch_id", "side", "line_number", "record_id", "status", "reason_code", "flags",
                    priority.alias("priority"), action.alias("recommended_action"),
                    F.coalesce(F.col("suggestion_count"), F.lit(0)).cast("int").alias("suggestion_count"))
            .select(*GOLD_EXCEPTIONS.fieldNames()))


def reconcile(invoices: DataFrame, ledger: DataFrame, rules: Rules, batch_id: str) -> GoldFrames:
    keys = classify_keys(invoices, ledger)
    pairs = _compare(_candidates(invoices, ledger, keys, "PAIR"), rules, decided=True)
    ambiguous = _compare(_candidates(invoices, ledger, keys, "AMBIGUOUS"), rules, decided=False)
    reconciliation = (_side_status(invoices, SIDE_INVOICE, keys, pairs, ledger, rules, batch_id)
                      .unionByName(_side_status(ledger, SIDE_LEDGER, keys, pairs, invoices, rules, batch_id))
                      .select(*GOLD_RECONCILIATION.fieldNames()))
    return GoldFrames(reconciliation, build_evidence(pairs, ambiguous, batch_id))


def _rate(numerator: int, denominator: int) -> Decimal:
    if not denominator:
        return Decimal("0.0000")
    return (Decimal(numerator) / Decimal(denominator)).quantize(Decimal("0.0001"), ROUND_HALF_UP)


def batch_metrics(spark, reconciliation: DataFrame, invoices: DataFrame, ledger: DataFrame, suggestions: DataFrame,
                  batch_id: str, period: str, rules: Rules) -> DataFrame:
    """One summary row per batch, computed from Spark aggregates (collected only as counts)."""
    by_status = {(r.side, r.status): r["count"] for r in reconciliation.groupBy("side", "status").count().collect()}
    review = reconciliation.filter(F.col("requires_review")).count()
    silver = invoices.select("dq_errors", "dq_warnings", "record_status").unionByName(
        ledger.select("dq_errors", "dq_warnings", "record_status"))
    quality = silver.agg(
        F.sum(F.when(F.size("dq_errors") > 0, 1).otherwise(0)).alias("errors"),
        F.sum(F.when(F.size("dq_warnings") > 0, 1).otherwise(0)).alias("warnings")).first()
    valid_invoices = invoices.filter(F.col("record_status") == "VALID").count()

    def count(side=None, status=None) -> int:
        return sum(v for (s, st), v in by_status.items() if (side is None or s == side) and (status is None or st == status))

    invoice_records, ledger_records = count(SIDE_INVOICE), count(SIDE_LEDGER)
    matched = count(SIDE_INVOICE, "MATCHED")
    row = (
        batch_id, period, invoice_records, ledger_records, matched,
        count(SIDE_INVOICE, "AMOUNT_MISMATCH"), count(SIDE_INVOICE, "CURRENCY_MISMATCH"),
        count(SIDE_INVOICE, "ONLY_IN_INVOICES"), count(SIDE_LEDGER, "ONLY_IN_LEDGER"),
        count(status="AMBIGUOUS"), count(status="DUPLICATE"), count(status="INVALID_RECORD"),
        review, int(quality.errors or 0), int(quality.warnings or 0), suggestions.count(),
        _rate(matched, invoice_records), _rate(matched, valid_invoices), rules.version,
    )
    return spark.createDataFrame([row], GOLD_BATCH_METRICS)
