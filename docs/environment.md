# Local environment

## Requirements

| Requirement | Notes |
| --- | --- |
| Python 3.10+ | developed with 3.11.9 |
| JDK 17 or 21 | `JAVA_HOME` must point to it; Java does not need to be on `PATH` |
| Windows only: Hadoop native helpers | `winutils.exe` and `hadoop.dll` in `%HADOOP_HOME%\bin` (developed with the Hadoop 3.3.5 helpers next to Spark's Hadoop 3.4.2 client) |
| Network on first run | Spark resolves the Delta jars from Maven Central into `~/.ivy2.5.2` (about 12 MB); later runs use the cache |

Nothing is installed globally. Before starting Spark, `invoice_recon/spark.py` checks the prerequisites
(exit code 5 with a message if one is missing) and then changes **only the current process**: it puts
`%JAVA_HOME%\bin` and `%HADOOP_HOME%\bin` at the front of `PATH`, and sets `PYSPARK_PYTHON`,
`PYSPARK_DRIVER_PYTHON` and `SPARK_HOME` (the PySpark package folder) if they are not already set.

## Setup

```bash
python -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"        # Windows: .venv\Scripts\python.exe
```

## Local Spark session

| Setting | Value | Reason |
| --- | --- | --- |
| master | `local[4]` (override with `INVOICE_RECON_SPARK_MASTER`) | one machine |
| `spark.sql.shuffle.partitions` | 8 (override with `INVOICE_RECON_SHUFFLE_PARTITIONS`) | small batches |
| `spark.sql.ansi.enabled` | true | bad values must fail rules, not become silent NULLs; conversions use `try_*` |
| `spark.sql.session.timeZone` | UTC | deterministic dates |
| `spark.databricks.delta.snapshotPartitions` | 2 | Delta state reconstruction defaults to 50 partitions |
| `spark.jars.excludes` | 22 artifacts PySpark already bundles | `delta-spark` 4.2 pulls duplicates through Maven, some older (jackson 2.13 vs 2.20) |
| `spark.driver.host` / `bindAddress` | 127.0.0.1 | avoids host-name resolution on corporate networks |
| Spark UI, console progress | off | quiet CLI output |

## Measured on the development machine

Windows 11, 12 logical CPUs, 16 GB RAM (about 3 GB free during the runs), JDK 17, corporate endpoint
protection:

| Measurement | Value |
| --- | --- |
| Session start with Delta, default Maven resolution | ~82 s |
| Session start with Delta and `spark.jars.excludes` | ~34 s |
| One Delta commit of 10 rows, steady state | ~5 s (Spark jobs inside it: ~1.5 s) |
| Reverse DNS of the host name | ~5 s (hence the loopback driver host) |

Commit overhead dominates local run time; the Spark processing of a 5,000-invoice batch is a small part
of it.

## Messages you can ignore on Windows

| Message | Cause |
| --- | --- |
| `ERROR: The process with PID ... could not be terminated` | PySpark's exit hook runs `taskkill` on a JVM that has already exited |
| `'-' is not recognized as an internal or external command` | Spark's `.cmd` launch scripts break on folder names containing ` - `; the launch still succeeds |
| leftover `spark-*` folders in `%TEMP%` | Windows cannot delete the jar copies the JVM still holds at shutdown; Spark's stack trace about it is silenced, the folders stay and can be deleted by hand |

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| exit code 5, "Java not found" | install a JDK 17 or 21 and set `JAVA_HOME` |
| exit code 5, "winutils.exe not found" | download the Hadoop native helpers for Hadoop 3.x and set `HADOOP_HOME` |
| first run hangs on `:: resolving dependencies ::` | Maven Central is not reachable; pre-populate `~/.ivy2.5.2` or use a proxy |
| `OutOfMemoryError: Java heap space` with much larger volumes | raise `spark.driver.memory` (default 1 GB) through `PYSPARK_SUBMIT_ARGS` |
