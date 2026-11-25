# Microsoft Fabric compatibility

**Execution inside Microsoft Fabric has not been tested.** No Fabric capacity was used for this project.
Everything below the "Versions" table describes how the code is meant to run in Fabric and what was
verified locally instead.

## Versions

| Component | Local development (verified) | CI (`.github/workflows/ci.yml`) | Fabric Runtime 2.0 (documented) |
| --- | --- | --- | --- |
| Apache Spark | 4.1.1 (PyPI `pyspark`) | 4.1.1 | 4.1 |
| Delta Lake | 4.2.0 (`delta-spark`, Maven `io.delta:delta-spark_4.1_2.13:4.2.0`) | 4.2.0 | 4.2 |
| Scala | 2.13 (bundled with PySpark) | 2.13 | 2.13 (2.13.16 on the runtime overview page) |
| Java | Temurin 17.0.17 | Temurin 17 (full suite) and 21 (smoke) | 21 |
| Python | 3.11.9 | 3.11 (full suite) and 3.13 (smoke) | 3.13 |
| OS | Windows 11 with Hadoop 3.3.5 `winutils.exe` / `hadoop.dll` | Ubuntu | Azure Linux 3.0 (Mariner 3.0) |

Sources, checked on 2026-11-24:

* Fabric Runtime 2.0: <https://learn.microsoft.com/en-us/fabric/data-engineering/runtime-2-0> (GA, default
  runtime; components Spark 4.1, Java 21, Scala 2.13, Python 3.13, Delta Lake 4.2, R 4.5.2).
* Runtime overview: <https://learn.microsoft.com/en-us/fabric/data-engineering/runtime>.
* Delta Lake releases: <https://docs.delta.io/latest/releases.html> (Delta 4.1.x, 4.2.x and 4.3.x support
  Spark 4.0.x and 4.1.x).
* Spark 4.1.0 overview: <https://spark.apache.org/docs/4.1.0/> ("Java 17/21, Scala 2.13, Python 3.10+").

The project brief listed Delta Lake 4.1 for Runtime 2.0; the official page lists Delta Lake 4.2, so the
local pin follows the page. `delta-spark` 4.2.0 itself requires `pyspark <= 4.1.1`, which fixes the
PySpark version.

## Differences that have not been verified

| Area | Local | Fabric | Risk |
| --- | --- | --- | --- |
| Exact builds | Apache PySpark 4.1.1, open-source Delta 4.2.0 | Microsoft's Spark 4.1 and Delta 4.2 builds (patch levels not published on the page) | Behavior differences in the functions used (`try_cast`, `try_to_date`, `from_csv`, `from_json`, `json_object_keys`, `levenshtein`, `_metadata.file_path`) are possible but not expected. |
| Java / Python | 17 / 3.11 | 21 / 3.13 | Exercised by the CI smoke job (Delta, pipeline and matching tests on Java 21 + Python 3.13), not by Fabric itself. |
| Storage | local file system | OneLake (ABFS) | Relative `Files/` and `Tables/` paths with `Lakehouse("")` are untested. |
| Session defaults | built by `spark.py` | provided by the notebook | `configure_session()` sets ANSI mode and UTC explicitly; Fabric-specific defaults (for example V-Order) are neither set nor relied on. |
| Local-only settings | `spark.jars.excludes`, `snapshotPartitions=2`, loopback driver host | not applied (the existing session is reused) | none expected |
| Table registration | path-based Delta folders | folders under `Tables/` should appear as lakehouse tables | untested, including partitioned tables in the SQL analytics endpoint |
| Lakehouse schemas | n/a | schema-enabled lakehouses use `Tables/<schema>/<table>` | not supported by the current layout |
| Installing the package | `pip install -e .` | `%pip install` of the wheel from `Files/libs/` with `--no-deps` | untested |
| Synthetic data | written by the generator to a local folder | written through the `/lakehouse/default` file mount | untested |

## Running the notebook in Fabric (fictional names)

[`notebooks/fabric_invoice_reconciliation.ipynb`](../notebooks/fabric_invoice_reconciliation.ipynb) imports
the same package as the CLI; it contains no copy of the pipeline logic.

1. In a workspace with a Fabric capacity or trial (for example `ws-portfolio-sandbox`), create a Lakehouse
   `lh_invoice_recon` **without** lakehouse schemas.
2. Build the wheel: `python -m pip wheel . --no-deps -w dist`.
3. Upload `dist/fabric_invoice_reconciliation-0.1.0-py3-none-any.whl` to `Files/libs/` of the lakehouse.
4. Import the notebook, attach `lh_invoice_recon` as the default lakehouse, select Runtime 2.0.
5. Run the cells in order:

   | Cell | Effect |
   | --- | --- |
   | `%pip install ... --no-deps` | installs the package; Spark and Delta come from the runtime |
   | Parameters | `LAKEHOUSE_FILES_DIR="/lakehouse/default"`, `LAKEHOUSE_SPARK_ROOT=""`, volume |
   | 1. Synthetic landing data | writes `Files/landing/...` unless batches already exist |
   | 2. Bronze → Silver → Gold | `pipeline.run(spark, lakehouse)` |
   | 3. Conservation and invariants | `validate_batch` for every batch |
   | 4. Query the Delta tables | DataFrame and `delta.\`path\`` SQL queries, exceptions |
   | 5. Reading the results | report in Markdown and `DESCRIBE HISTORY` |

Expected tables after the run: the 13 tables listed in [data-model.md](data-model.md) under `Tables/`.

## What was verified locally instead

`tests/test_notebook.py` validates the notebook with `nbformat` and executes every code cell except the
`%pip` cell against a local Spark + Delta session, with the parameters pointed at a temporary directory.
That proves the notebook's API usage and logic, not its behavior inside Fabric.
