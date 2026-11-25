# Testing

```bash
python -m pytest -v                       # all tests; needs Java 17/21 (and the Windows helpers on Windows)
python -m pytest -m "not spark" -v        # no JVM: generator, configuration, CLI pre-flight, notebook format, demo files
python -m pytest -m "spark and not slow"  # Spark tests without the separate-process CLI run
```

Spark tests share one local session (`local[2]`) and one end-to-end run of two synthetic batches of
100 base invoices each (the smallest volume that still contains every scenario). Tests that change data
work on their own temporary lakehouse. The `spark` fixture skips Spark tests with a message when Java or
the Windows helpers are missing; a skip is reported, it is not a pass.

## Inventory

| File | Tests | Covers |
| --- | --- | --- |
| `test_generator.py` | 19 | Byte-identical output for a seed, fingerprint stable across platforms, every scenario present at 100 and 1,000 invoices, layout and manifest, ground truth covering every line, contract shape except designed malformed rows, decimal and JSON-number amounts, similar-name supplier pairs above the threshold, fictional names only, overwrite protection, argument limits |
| `test_config.py` | 25 | Decimal tolerances, invalid rules rejected, batch IDs that could escape a path or a `replaceWhere` predicate, periods, local and Fabric-relative layout, explicit schema per table, DQ catalog |
| `test_cli_preflight.py` | 18 | Exit codes decided before Spark starts: 0 (`--help`), 2 (usage), 3 (missing landing data or upstream tables, invalid generation arguments, refused overwrite), 5 (no Java, run in a separate process with Java removed from `PATH`) |
| `test_bronze.py` | 16 | Raw strings and line numbers, CRLF, blank lines logged, quoted commas, malformed CSV rows kept, header contract (renamed, reordered, missing column, BOM), malformed JSON and schema drift kept, numeric JSON amounts keep their literal text, manifest validation, batch discovery, every generated landing line present in Bronze |
| `test_silver.py` | 24 | Text and identifier normalization, exact decimals and strict amount formats, total consistency at the tolerance boundary (USD and JPY), ISO invoice dates, 12 posting-date cases including the ambiguous one, accounting periods and period warnings, payment status, exact and conflicting duplicates, NULL IDs never grouped, INVALID before DUPLICATE, no row filtered, quarantine with raw lines, metrics for every rule, only catalog codes emitted |
| `test_reconcile.py` | 21 | Rule R1 and its evidence, reference variants, inclusive per-currency tolerance, no cross-currency comparison, one-sided records and their reasons, **two NULLs never match**, ambiguous keys listed but not decided, possible double posting, **duplicates do not multiply matches**, conflicting duplicates block a match, review flags, key classification partitions every key once, result independent of input order, invariants on two random data sets with many collisions |
| `test_fuzzy.py` | 8 | Same reference under a similarly named supplier, dissimilar names ignored, same supplier and amount with a similar reference, different amount ignored, matched records never suggested, cap and ranking, Spark similarity equals the Python reference, designed suggestions present in the run |
| `test_delta.py` | 8 | Delta round trip with declared schema and partitioning, idempotent and isolated batch rewrites, schema mismatch refused with no new version, Delta's own schema enforcement, rows from another batch refused, `replaceWhere` violation leaves no commit, missing tables and empty batches, MERGE upsert of the control table |
| `test_pipeline.py` | 7 | All validation checks pass for both batches including the synthetic ground truth, stage counts line up, metrics derived from stored tables, **re-running a batch leaves every table byte-identical and the other batch untouched**, corrected landing file replaces the Bronze slice, schema mismatch rejects the batch and keeps previous data, missing upstream data |
| `test_cli.py` | 5 | `validate`, `report`, `demo` and `demo --check` in-process (exit 0), drift detected (exit 4), tampered Gold table fails validation (exit 4), bad header (exit 3), unknown batch (exit 3) |
| `test_cli_process.py` | 1 | `generate-data` and `run` in a new process with its own JVM, reports written, validation passed |
| `test_notebook.py` | 2 | Notebook is valid nbformat, committed without outputs, says Fabric execution is not tested; every code cell except `%pip` runs locally against Spark |
| `test_report_demo.py` | 4 | Report content and Markdown sections, demo data deterministic with no timestamps or local paths, committed `demo/data.js` shape, demo page has no network access |

## Local results (2026-11-24, Windows 11, Python 3.11.9, Temurin 17, PySpark 4.1.1, delta-spark 4.2.0)

| Run | Result |
| --- | --- |
| `python -m pytest -v` | 158 passed, 0 skipped, 0 failed (47 min) |
| `python -m pytest -m "not spark"` in a fresh copy with a new virtual environment | 65 passed (8 s) |
| `python -m invoice_recon run --generate --force` (2 batches x 5,000 base invoices) | exit 0 in 631 s; 25/25 checks per batch; ground truth 10,142/10,142 and 10,162/10,162 |
| `python -m invoice_recon demo --check` in a new process | `demo/data.js is up to date` |

Slowest steps: the shared two-batch pipeline run (~390 s, fixture setup), `demo` + `demo --check` through
the CLI (~360 s), the separate-process CLI run with its own JVM (~340 s), the notebook cells (~285 s)
and the idempotency re-run of a batch (~160 s). Delta commit overhead dominates, see
[environment.md](environment.md).

## Continuous integration

The full suite is too expensive to repeat in every matrix cell, so the work is split by what each job
has to prove. Results are in the repository's Actions tab.

| Workflow / job | Trigger | Environment | What it verifies |
| --- | --- | --- | --- |
| `ci.yml` / `fast` | every push and pull request | Ubuntu and Windows × Python 3.11 and 3.13 | the 65 tests without a JVM: generator determinism and fingerprint, rules and configuration, data contracts, CLI exit codes decided before Spark (including exit 5 without Java), notebook format, committed demo files |
| `ci.yml` / `spark-full` | every push and pull request | Ubuntu, Python 3.11, Java 17 | all 158 tests: Spark start-up, Delta creation, reads and writes, `replaceWhere`, MERGE, idempotent re-run, conservation and invariants on generated data, ground truth, notebook cells, CLI in a separate process, demo build and drift detection (2 batches × 100 invoices) |
| `ci.yml` / `spark-smoke` | every push and pull request | Ubuntu, Python 3.13, Java 21 (closest to Fabric Runtime 2.0) | `test_delta.py`, `test_pipeline.py` and `test_reconcile.py` (Delta I/O and MERGE, end-to-end pipeline with ground truth, idempotency, batch rejection, NULL and multiplicity invariants), then `generate-data` + `run` from scratch on one 100-invoice batch and a demo build followed by `demo --check` |
| `full-volume.yml` | manual (`workflow_dispatch`) | Ubuntu, Python 3.11, Java 17 | the default 2 × 5,000-invoice run from scratch with every validation check, and `demo --check` against the committed `demo/data.js` |

The smoke job runs 36 of the 93 Spark tests on Python 3.13 + Java 21; the remaining Spark tests
(Bronze and Silver unit cases, similarity, CLI, notebook, reports) run on Python 3.11 + Java 17 only.
Spark tests are not run on Windows runners because they would need the Hadoop native helpers.

## What the tests do not cover

* Execution inside Microsoft Fabric, OneLake paths and the SQL analytics endpoint.
* Process crashes in the middle of a Delta commit, and concurrent writers.
* Volumes beyond a few batches of 5,000 invoices on one machine.
