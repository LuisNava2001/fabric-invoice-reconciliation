"""CLI exit codes that are decided before any Spark session starts (no Java needed)."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

from invoice_recon import cli, generator
from invoice_recon.config import EXIT_ENVIRONMENT, EXIT_INPUT, EXIT_OK, EXIT_USAGE

REPO = Path(__file__).resolve().parents[1]


def _run(*args, env=None, cwd=None):
    return subprocess.run([sys.executable, "-m", "invoice_recon", *args], capture_output=True, text=True,
                          env=env, cwd=cwd or REPO, timeout=300)


def test_help_lists_commands_and_exit_codes():
    result = _run("--help")
    assert result.returncode == EXIT_OK
    for command in ("generate-data", "ingest", "normalize", "reconcile", "validate", "report", "demo", "run"):
        assert command in result.stdout
    assert "exit codes" in result.stdout and "5  environment error" in result.stdout


@pytest.mark.parametrize("args", [(), ("no-such-command",), ("generate-data", "--invoices", "many")])
def test_usage_errors_exit_2(args):
    assert _run(*args).returncode == EXIT_USAGE


def test_generate_data_then_refuse_overwrite(tmp_path):
    lake = tmp_path / "lake"
    first = _run("--lakehouse", str(lake), "generate-data", "--invoices", "100", "--batches", "1")
    assert first.returncode == EXIT_OK, first.stderr
    assert "batch-2026-03" in first.stdout
    again = _run("--lakehouse", str(lake), "generate-data", "--invoices", "100", "--batches", "1")
    assert again.returncode == EXIT_INPUT and "--force" in again.stderr
    assert _run("--lakehouse", str(lake), "generate-data", "--invoices", "100", "--batches", "1", "--force").returncode == EXIT_OK


def test_invalid_generation_arguments_exit_3(tmp_path):
    assert cli.main(["--lakehouse", str(tmp_path), "generate-data", "--invoices", "10"]) == EXIT_INPUT
    assert cli.main(["--lakehouse", str(tmp_path), "generate-data", "--start-period", "2026-13"]) == EXIT_INPUT


@pytest.mark.parametrize("command", ["ingest", "normalize", "reconcile", "validate", "report", "demo", "run"])
def test_missing_landing_data_exits_3_before_spark(tmp_path, command):
    assert cli.main(["--lakehouse", str(tmp_path / "empty"), command]) == EXIT_INPUT


@pytest.mark.parametrize("command", ["normalize", "reconcile", "validate", "report"])
def test_missing_upstream_tables_exit_3_before_spark(tmp_path, command):
    generator.generate(tmp_path, invoices=100, batches=1)
    assert cli.main(["--lakehouse", str(tmp_path), command]) == EXIT_INPUT


def test_missing_java_exits_5_without_starting_spark(tmp_path):
    generator.generate(tmp_path, invoices=100, batches=1)
    env = {k: v for k, v in os.environ.items() if k not in ("JAVA_HOME", "PYSPARK_PYTHON", "PYSPARK_DRIVER_PYTHON")}
    env["JAVA_HOME"] = str(tmp_path / "no-jdk-here")
    env["PATH"] = os.pathsep.join(p for p in env.get("PATH", "").split(os.pathsep)
                                  if p and not (Path(p) / ("java.exe" if os.name == "nt" else "java")).exists())
    result = _run("--lakehouse", str(tmp_path), "ingest", env=env)
    assert result.returncode == EXIT_ENVIRONMENT, result.stderr
    assert "Java not found" in result.stderr
