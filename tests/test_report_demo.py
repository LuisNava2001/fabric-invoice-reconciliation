"""Reports and offline demo: built from stored tables, deterministic, self-contained."""

import json
import re
from pathlib import Path

import pytest

from invoice_recon.config import STATUSES
from invoice_recon.demo import build_demo_data, render
from invoice_recon.report import EXAMPLE_TITLES, build_report, render_markdown, to_json
from invoice_recon.validate import validate_batch

REPO = Path(__file__).resolve().parents[1]


@pytest.mark.spark
def test_report_contents(spark, pipeline_run):
    batch_id = pipeline_run.batch_ids[0]
    report = build_report(spark, pipeline_run.lakehouse, batch_id, validate_batch(spark, pipeline_run.lakehouse, batch_id))
    json.loads(to_json(report))
    assert report["synthetic"] is True and report["reconciliation_period"] == "2026-03"
    assert [row["status"] for row in report["status_table"]] == list(STATUSES)
    assert [e["title"] for e in report["evidence_examples"]] == list(EXAMPLE_TITLES)
    ambiguous_date = next(e for e in report["evidence_examples"] if "ambiguous" in e["title"])
    assert len(ambiguous_date["ledger_posting_date"]["posting_date_candidates"]) == 2
    assert report["validation"]["passed"] is True
    assert set(report["delta_versions"]) >= {"gold_reconciliation", "bronze_invoices"}
    markdown = render_markdown(report)
    for heading in ("## Summary", "## Layers", "## Status by side", "## Match evidence examples",
                    "## Candidate suggestions", "## Exceptions", "## Validation"):
        assert heading in markdown


@pytest.mark.spark
def test_demo_data_is_deterministic_and_free_of_local_details(spark, pipeline_run):
    batch = pipeline_run.batch_ids[:1]
    first = render(build_demo_data(spark, pipeline_run.lakehouse, batch))
    second = render(build_demo_data(spark, pipeline_run.lakehouse, batch))
    assert first == second
    assert str(pipeline_run.directory.as_posix()) not in first and "C:\\\\" not in first
    assert not re.search(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}", first), "no timestamps"
    data = json.loads(first[len("window.RECON_DEMO = "):-2])
    assert data["all_checks_passed"] is True and [b["batch_id"] for b in data["batches"]] == batch


def test_committed_demo_data_has_the_expected_shape():
    text = (REPO / "demo" / "data.js").read_text(encoding="utf-8")
    assert text.startswith("window.RECON_DEMO = ") and text.endswith(";\n")
    data = json.loads(text[len("window.RECON_DEMO = "):-2])
    assert data["synthetic"] is True and data["all_checks_passed"] is True
    assert data["versions"]["pyspark"] == "4.1.1" and data["versions"]["delta-spark"] == "4.2.0"
    for batch in data["batches"]:
        assert batch["metrics"]["invoice_records"] == sum(r["invoices"] for r in batch["status_table"])
        assert all(c["passed"] for c in batch["validation"]["checks"])


def test_demo_page_is_offline():
    for name in ("index.html", "app.js", "styles.css"):
        text = (REPO / "demo" / name).read_text(encoding="utf-8")
        assert "http://" not in text and "https://" not in text, name
        assert "fetch(" not in text and "XMLHttpRequest" not in text, name
    html = (REPO / "demo" / "index.html").read_text(encoding="utf-8")
    assert '<script src="data.js"></script>' in html and '<script src="app.js"></script>' in html
