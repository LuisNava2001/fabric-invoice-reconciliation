"""Shared fixtures: one local Spark session and one full pipeline run reused by many tests."""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from invoice_recon import generator, pipeline
from invoice_recon.config import BATCH_TABLES, Lakehouse, load_rules

from .helpers import table_digest

SMALL_INVOICES = 100  # smallest volume that still contains every scenario at least once


@pytest.fixture(scope="session")
def spark():
    from invoice_recon.spark import environment_problems, get_or_create_spark

    problems = environment_problems()
    if problems:
        pytest.skip("local Spark is not available: " + " ".join(problems))
    session, created = get_or_create_spark(app_name="invoice-recon-tests", master="local[2]")
    yield session
    if created:
        session.stop()


@pytest.fixture(scope="session")
def rules():
    return load_rules()


@dataclass
class PipelineRun:
    lakehouse: Lakehouse
    directory: object
    batch_ids: list
    results: list
    digests: dict = field(default_factory=dict)


@pytest.fixture(scope="session")
def pipeline_run(spark, rules, tmp_path_factory) -> PipelineRun:
    """Two synthetic batches processed end to end once; tests read the stored tables."""
    directory = tmp_path_factory.mktemp("lakehouse")
    generator.generate(directory, invoices=SMALL_INVOICES, batches=2)
    lakehouse = Lakehouse.local(directory)
    results = pipeline.run(spark, lakehouse, rules=rules, log=lambda _: None)
    batch_ids = sorted({r.batch_id for r in results})
    digests = {(name, b): table_digest(spark, lakehouse, name, b) for name in BATCH_TABLES for b in batch_ids}
    return PipelineRun(lakehouse, directory, batch_ids, results, digests)
