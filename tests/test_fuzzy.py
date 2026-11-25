"""Similarity suggestions: secondary, scored, explained, never applied, never replacing identifiers."""

from decimal import Decimal

import pytest
from pyspark.sql import functions as F

from invoice_recon import generator, reconcile

from .helpers import BATCH, gold

pytestmark = pytest.mark.spark

SIBLING = {"supplier_id": "SUP-0002", "supplier_name": "Amberlyn Casting Co"}


def _suggest(spark, rules, invoices, ledger):
    status, evidence, reconciliation, inv, led = gold(spark, rules, invoices, ledger)
    suggestions = reconcile.build_suggestions(reconciliation, inv, led, rules, BATCH)
    return status, evidence, suggestions.orderBy("invoice_line", "suggestion_rank").collect()


def test_same_reference_under_a_similarly_named_supplier_is_suggested(spark, rules):
    status, evidence, [s] = _suggest(spark, rules, [{}], [SIBLING])
    assert status[("INVOICE", 2)].status == "ONLY_IN_INVOICES" and status[("LEDGER", 1)].status == "ONLY_IN_LEDGER"
    assert evidence == [], "different supplier IDs never pair deterministically"
    assert s.criterion == "SAME_REFERENCE_DIFFERENT_SUPPLIER" and s.auto_approved is False
    assert s.review_action == "HUMAN_REVIEW_REQUIRED"
    assert s.score == s.name_similarity and s.name_similarity >= rules.name_similarity_threshold
    assert "Amberlyn Castings Ltd" in s.explanation and "Amberlyn Casting Co" in s.explanation
    assert "a person must decide" in s.explanation


def test_dissimilar_names_are_not_suggested(spark, rules):
    _, _, suggestions = _suggest(spark, rules, [{}], [{"supplier_id": "SUP-0009", "supplier_name": "Zelmont Logistics LLC"}])
    assert suggestions == []


def test_same_supplier_same_amount_similar_reference_is_suggested(spark, rules):
    _, _, [s] = _suggest(spark, rules, [{"invoice_reference": "AMC-004213"}], [{"invoice_reference": "AMC-4213"}])
    assert s.criterion == "SAME_SUPPLIER_AMOUNT_SIMILAR_REFERENCE"
    assert s.reference_similarity == Decimal("0.778") and s.amount_difference == Decimal("0")


def test_similar_reference_with_a_different_amount_is_not_suggested(spark, rules):
    _, _, suggestions = _suggest(spark, rules, [{"invoice_reference": "AMC-004213"}],
                                 [{"invoice_reference": "AMC-4213", "recorded_amount": "500.00"}])
    assert suggestions == []


def test_matched_records_are_never_suggested(spark, rules):
    status, _, suggestions = _suggest(spark, rules, [{}], [{}, dict(SIBLING, transaction_id="GL-2")])
    assert status[("INVOICE", 2)].status == "MATCHED"
    assert suggestions == [], "rule R1 matched the invoice; similarity does not reopen it"


def test_suggestions_are_capped_and_ranked(spark, rules):
    ledger = [{"transaction_id": f"GL-{i}", "invoice_reference": f"AMC-0042{i}"} for i in range(1, 6)]
    _, _, rows = _suggest(spark, rules, [{"invoice_reference": "AMC-004210"}], ledger)
    assert len(rows) == rules.max_suggestions_per_record
    assert [r.suggestion_rank for r in rows] == [1, 2, 3]
    assert [r.score for r in rows] == sorted((r.score for r in rows), reverse=True)


def test_spark_similarity_matches_the_python_reference(spark):
    pairs = [("QUILLBROOK FASTENERS", "QUILLBROOK FASTENING"), ("AMC004213", "AMC4213"), ("A", "A"), ("ABC", "XYZ")]
    df = spark.createDataFrame(pairs, "a STRING, b STRING")
    got = [r.s for r in df.select(reconcile.similarity(F.col("a"), F.col("b")).alias("s")).collect()]
    assert got == [generator.similarity(a, b) for a, b in pairs]


def test_designed_suggestions_appear_in_the_pipeline_run(spark, pipeline_run):
    df = spark.read.format("delta").load(pipeline_run.lakehouse.table("gold_candidate_suggestions"))
    assert df.count() > 0 and df.filter(F.col("auto_approved")).count() == 0
    assert {r.criterion for r in df.select("criterion").distinct().collect()} == {
        "SAME_REFERENCE_DIFFERENT_SUPPLIER", "SAME_SUPPLIER_AMOUNT_SIMILAR_REFERENCE"}
