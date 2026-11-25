"""Command-line interface. Exit codes: 0 ok, 1 internal error, 2 usage, 3 input, 4 validation, 5 environment."""

from __future__ import annotations

import argparse
import contextlib
import sys
import time
import traceback
from pathlib import Path

from . import __version__, generator
from .config import (
    EXIT_INTERNAL,
    EXIT_OK,
    EXIT_VALIDATION,
    InputError,
    Lakehouse,
    PipelineError,
    load_rules,
)

EXIT_CODES = """exit codes:
  0  success
  1  unexpected internal error
  2  usage error (invalid arguments)
  3  input error: missing landing data, manifest or upstream table; source schema mismatch
  4  validation failed: record conservation, invariants, ground truth or demo drift
  5  environment error: Java / Hadoop helpers missing or Spark failed to start"""


def _out(message: str) -> None:
    print(message, flush=True)


@contextlib.contextmanager
def _spark():
    from .spark import get_or_create_spark

    spark, created = get_or_create_spark()
    try:
        yield spark
    finally:
        if created:
            spark.stop()


def _lakehouse(args) -> Lakehouse:
    return Lakehouse.local(args.lakehouse)


def _require_landing(args) -> None:
    landing = Path(args.lakehouse) / "Files" / "landing"
    if not landing.is_dir():
        raise InputError(f"no landing data at {landing}; run 'generate-data' first")


def _require_tables(args, *names: str) -> None:
    for name in names:
        log = Path(args.lakehouse) / "Tables" / name / "_delta_log"
        if not log.is_dir():
            raise InputError(f"Delta table {name} not found under {Path(args.lakehouse) / 'Tables'}; run the upstream stage first")


def cmd_generate(args) -> int:
    started = time.time()
    summaries = generator.generate(args.lakehouse, seed=args.seed, batches=args.batches, invoices=args.invoices,
                                   start_period=args.start_period, force=args.force)
    for s in summaries:
        _out(f"[generate-data] {s.batch_id} ({s.period}): {s.invoice_rows:,} invoice rows, {s.ledger_rows:,} ledger rows")
    _out(f"[generate-data] seed {args.seed}, {time.time() - started:.1f}s, landing at "
         f"{Path(args.lakehouse) / 'Files' / 'landing'}")
    return EXIT_OK


def _stage(name: str, requires: tuple):
    def handler(args) -> int:
        from . import pipeline

        _require_landing(args)
        _require_tables(args, *requires)
        rules = load_rules(args.rules)
        with _spark() as spark:
            lakehouse = _lakehouse(args)
            for batch_id in pipeline.resolve_batches(spark, lakehouse, args.batch):
                _out(pipeline.STAGES[name](spark, lakehouse, batch_id, rules).summary())
        return EXIT_OK
    return handler


def _validate_batches(spark, lakehouse, batch_ids, ground_truth: bool) -> bool:
    from .validate import validate_batch

    ok = True
    for batch_id in batch_ids:
        report = validate_batch(spark, lakehouse, batch_id, ground_truth=ground_truth)
        failed = [c for c in report.checks if not c.passed]
        _out(f"[validate] {batch_id}: {len(report.checks) - len(failed)}/{len(report.checks)} checks passed")
        for check in failed:
            _out(f"  FAIL {check.check_id}: {check.detail}")
        ok = ok and report.passed
    return ok


GOLD_TABLES = ("gold_reconciliation", "gold_match_evidence", "gold_candidate_suggestions", "gold_exceptions",
               "gold_batch_metrics")


def cmd_validate(args) -> int:
    from . import pipeline

    _require_landing(args)
    _require_tables(args, "bronze_invoices", "silver_invoices", *GOLD_TABLES)
    with _spark() as spark:
        lakehouse = _lakehouse(args)
        ok = _validate_batches(spark, lakehouse, pipeline.resolve_batches(spark, lakehouse, args.batch), not args.no_ground_truth)
    return EXIT_OK if ok else EXIT_VALIDATION


def _write_reports(spark, lakehouse, batch_ids, root: Path) -> bool:
    from .report import build_report, render_markdown, to_json
    from .validate import validate_batch

    ok = True
    for batch_id in batch_ids:
        validation = validate_batch(spark, lakehouse, batch_id)
        report = build_report(spark, lakehouse, batch_id, validation)
        target = root / "Files" / "reports" / batch_id
        target.mkdir(parents=True, exist_ok=True)
        (target / "reconciliation_report.json").write_text(to_json(report), encoding="utf-8", newline="\n")
        (target / "reconciliation_report.md").write_text(render_markdown(report), encoding="utf-8", newline="\n")
        m = report["metrics"]
        _out(f"[report] {batch_id}: reconciliation rate {m['reconciliation_rate']}, {m['records_requiring_review']} "
             f"records to review, checks {'passed' if validation.passed else 'FAILED'} -> {target}")
        ok = ok and validation.passed
    return ok


def cmd_report(args) -> int:
    from . import pipeline

    _require_landing(args)
    _require_tables(args, *GOLD_TABLES)
    with _spark() as spark:
        lakehouse = _lakehouse(args)
        ok = _write_reports(spark, lakehouse, pipeline.resolve_batches(spark, lakehouse, args.batch), Path(args.lakehouse))
    return EXIT_OK if ok else EXIT_VALIDATION


def cmd_demo(args) -> int:
    from . import pipeline
    from .demo import build_demo_data, write_or_check

    _require_landing(args)
    _require_tables(args, *GOLD_TABLES)
    with _spark() as spark:
        lakehouse = _lakehouse(args)
        data = build_demo_data(spark, lakehouse, pipeline.resolve_batches(spark, lakehouse, args.batch))
    ok, message = write_or_check(data, Path(args.out), args.check)
    _out(f"[demo] {message}")
    if not data["all_checks_passed"]:
        _out("[demo] validation checks failed for at least one batch; see the report")
        return EXIT_VALIDATION
    return EXIT_OK if ok else EXIT_VALIDATION


def cmd_run(args) -> int:
    from . import pipeline

    if args.generate:
        cmd_generate(args)
    _require_landing(args)
    rules = load_rules(args.rules)
    started = time.time()
    with _spark() as spark:
        lakehouse = _lakehouse(args)
        batch_ids = pipeline.resolve_batches(spark, lakehouse, args.batch)
        pipeline.run(spark, lakehouse, batch_ids, rules, log=_out)
        ok = _write_reports(spark, lakehouse, batch_ids, Path(args.lakehouse))
    _out(f"[run] {len(batch_ids)} batch(es) in {time.time() - started:.0f}s; validation {'passed' if ok else 'FAILED'}")
    return EXIT_OK if ok else EXIT_VALIDATION


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m invoice_recon",
        description="Invoice reconciliation on PySpark + Delta Lake (synthetic data, Fabric-style lakehouse layout).",
        epilog=EXIT_CODES, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--lakehouse", default="lakehouse", help="local lakehouse directory (default: ./lakehouse)")
    parser.add_argument("--rules", default=None, help="alternative reconciliation_rules.json")
    sub = parser.add_subparsers(dest="command", required=True, metavar="command")

    def add(name: str, handler, help_text: str, batches: bool = True):
        p = sub.add_parser(name, help=help_text, description=help_text, epilog=EXIT_CODES,
                           formatter_class=argparse.RawDescriptionHelpFormatter)
        if batches:
            p.add_argument("--batch", action="append", help="batch id (repeatable; default: every landing batch)")
        p.set_defaults(handler=handler)
        return p

    def generation_options(p, prefix=""):
        p.add_argument("--seed", type=int, default=generator.DEFAULT_SEED)
        p.add_argument("--batches", type=int, default=generator.DEFAULT_BATCHES)
        p.add_argument("--invoices", type=int, default=generator.DEFAULT_INVOICES, help="base invoices per batch")
        p.add_argument("--start-period", default=generator.DEFAULT_START_PERIOD, help="first period, YYYY-MM")
        p.add_argument("--force", action="store_true", help="overwrite existing landing batches")

    generation_options(add("generate-data", cmd_generate, "Write deterministic synthetic landing files.", batches=False))
    add("ingest", _stage("ingest", ()), "Landing files -> Bronze Delta tables.")
    add("normalize", _stage("normalize", ("bronze_invoices", "bronze_ledger")), "Bronze -> Silver (normalization, data quality).")
    add("reconcile", _stage("reconcile", ("silver_invoices", "silver_ledger")), "Silver -> Gold (matching, evidence, exceptions).")
    v = add("validate", cmd_validate, "Record-conservation and invariant checks (exit 4 on failure).")
    v.add_argument("--no-ground-truth", action="store_true", help="skip the synthetic ground-truth comparison")
    add("report", cmd_report, "Write JSON and Markdown reports under Files/reports/.")
    d = add("demo", cmd_demo, "Build demo/data.js for the offline demo page from the stored tables.")
    d.add_argument("--out", default="demo/data.js")
    d.add_argument("--check", action="store_true", help="compare with the existing file instead of writing (exit 4 on drift)")
    r = add("run", cmd_run, "ingest + normalize + reconcile + validate + report for every batch.")
    r.add_argument("--generate", action="store_true", help="generate synthetic data first")
    generation_options(r)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:  # argparse: 0 for --help/--version, 2 for usage errors
        return int(exc.code or 0)
    try:
        return args.handler(args)
    except PipelineError as exc:
        print(f"error: {exc}", file=sys.stderr, flush=True)
        return exc.exit_code
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        return EXIT_INTERNAL
    except Exception:  # noqa: BLE001 - last-resort guard; prints the traceback
        traceback.print_exc()
        return EXIT_INTERNAL
