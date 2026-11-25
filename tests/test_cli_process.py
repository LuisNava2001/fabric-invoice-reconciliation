"""The real entry point in a separate process: generate-data + run, with its own Spark JVM."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from invoice_recon.config import EXIT_OK

REPO = Path(__file__).resolve().parents[1]

pytestmark = [pytest.mark.spark, pytest.mark.slow]


def test_generate_and_run_end_to_end_in_a_new_process(spark, tmp_path):
    # `spark` only makes sure the environment can run Spark; the CLI starts its own JVM.
    def run(*args):
        return subprocess.run([sys.executable, "-m", "invoice_recon", "--lakehouse", str(tmp_path), *args],
                              capture_output=True, text=True, cwd=REPO, timeout=1800)

    generated = run("generate-data", "--invoices", "100", "--batches", "1", "--seed", "7")
    assert generated.returncode == EXIT_OK, generated.stderr
    result = run("run")
    assert result.returncode == EXIT_OK, result.stdout + result.stderr
    assert "[bronze] batch-2026-03" in result.stdout and "[gold] batch-2026-03" in result.stdout
    assert "validation passed" in result.stdout
    report = json.loads((tmp_path / "Files" / "reports" / "batch-2026-03" / "reconciliation_report.json").read_text())
    assert report["validation"]["passed"] and report["generator"]["seed"] == 7
    assert (tmp_path / "Tables" / "gold_reconciliation" / "_delta_log").is_dir()
