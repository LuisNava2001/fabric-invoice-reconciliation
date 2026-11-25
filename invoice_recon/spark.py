"""SparkSession for local runs; an already-active session (e.g. a Fabric notebook) is reused.

Local runs need Java 17+ and, on Windows, Hadoop's native helpers (winutils.exe and
hadoop.dll under %HADOOP_HOME%\\bin). Nothing is installed or changed system-wide: PATH and
PYSPARK_PYTHON are adjusted for the current process only.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from .config import EnvironmentProblem

# delta-spark 4.2 resolves, through Maven, artifacts that pyspark 4.1.1 already bundles (some
# at older versions, e.g. jackson 2.13 versus Spark's 2.20). Excluding them keeps Spark's own
# copies on the classpath and roughly halves session start-up on the development machine.
BUNDLED_BY_SPARK = (
    "org.apache.hadoop:hadoop-client-api",
    "org.apache.hadoop:hadoop-client-runtime",
    "org.apache.parquet:parquet-hadoop",
    "org.apache.parquet:parquet-column",
    "org.apache.parquet:parquet-common",
    "org.apache.parquet:parquet-encoding",
    "org.apache.parquet:parquet-format-structures",
    "org.apache.parquet:parquet-jackson",
    "com.fasterxml.jackson.core:jackson-databind",
    "com.fasterxml.jackson.core:jackson-core",
    "com.fasterxml.jackson.core:jackson-annotations",
    "org.apache.logging.log4j:log4j-api",
    "org.apache.logging.log4j:log4j-core",
    "org.apache.logging.log4j:log4j-slf4j2-impl",
    "org.slf4j:slf4j-api",
    "org.xerial.snappy:snappy-java",
    "com.github.luben:zstd-jni",
    "io.airlift:aircompressor",
    "org.roaringbitmap:RoaringBitmap",
    "org.locationtech.jts:jts-core",
    "commons-pool:commons-pool",
    "com.google.code.findbugs:jsr305",
)

# Loggers that only add noise to local runs (Windows cannot delete jars still held by the JVM
# at shutdown; the files stay in the temp directory and Spark logs a stack trace).
_QUIET_LOGGERS = (
    ("org.apache.spark.util.ShutdownHookManager", "OFF"),
    ("org.apache.spark.SparkEnv", "ERROR"),
    ("org.apache.hadoop.util.NativeCodeLoader", "ERROR"),
    # Glob reads (Files/landing/*/batch.json) log a stack trace while probing for a streaming sink.
    ("org.apache.spark.sql.execution.streaming.FileStreamSink", "ERROR"),
    ("org.apache.spark.sql.execution.streaming.sinks.FileStreamSink", "ERROR"),
    ("org.apache.spark.util.SparkStringUtils", "ERROR"),
    ("org.apache.spark.sql.catalyst.util.SparkStringUtils", "ERROR"),
    # Delta MERGE materializes its source with a local checkpoint and Spark warns about it.
    ("org.apache.spark.rdd.MapPartitionsRDD", "ERROR"),
)

IS_WINDOWS = os.name == "nt"


def find_java() -> Path | None:
    java_home = os.environ.get("JAVA_HOME")
    if java_home:
        candidate = Path(java_home) / "bin" / ("java.exe" if IS_WINDOWS else "java")
        if candidate.is_file():
            return candidate
    found = shutil.which("java")
    return Path(found) if found else None


def java_major_version(java: Path) -> int | None:
    try:
        completed = subprocess.run([str(java), "-version"], capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    match = re.search(r'version "(\d+)(?:\.(\d+))?', completed.stderr + completed.stdout)
    if not match:
        return None
    major = int(match.group(1))
    return int(match.group(2) or 0) if major == 1 else major


def environment_problems() -> list[str]:
    """Return human-readable problems that would stop a local Spark session from starting."""
    problems = []
    java = find_java()
    if java is None:
        problems.append("Java not found: set JAVA_HOME to a JDK 17 or 21 (Spark 4.1 requirement).")
    else:
        major = java_major_version(java)
        if major is None:
            problems.append(f"Could not run '{java} -version'.")
        elif major < 17:
            problems.append(f"Java {major} found at {java}; Spark 4.1 needs Java 17 or 21.")
    if IS_WINDOWS:
        hadoop_home = os.environ.get("HADOOP_HOME")
        if not hadoop_home:
            problems.append("HADOOP_HOME is not set: Spark on Windows needs winutils.exe and hadoop.dll "
                            "(see docs/environment.md).")
        else:
            for helper in ("winutils.exe", "hadoop.dll"):
                if not (Path(hadoop_home) / "bin" / helper).is_file():
                    problems.append(f"{helper} not found under {hadoop_home}\\bin (see docs/environment.md).")
    return problems


def _prepend_to_path(directory: Path) -> None:
    entries = os.environ.get("PATH", "").split(os.pathsep)
    if str(directory) not in entries:
        os.environ["PATH"] = os.pathsep.join([str(directory)] + entries)


def prepare_local_environment() -> None:
    """Fail fast with a clear message, then adjust this process's environment only."""
    problems = environment_problems()
    if problems:
        raise EnvironmentProblem(" ".join(problems))
    _prepend_to_path(find_java().parent)
    if IS_WINDOWS:
        _prepend_to_path(Path(os.environ["HADOOP_HOME"]) / "bin")
    os.environ.setdefault("PYSPARK_PYTHON", sys.executable)
    os.environ.setdefault("PYSPARK_DRIVER_PYTHON", sys.executable)
    # pip-installed PySpark is its own SPARK_HOME. Setting it skips spark-submit.cmd's
    # interpreter probe, which breaks on Windows paths that contain spaces.
    import pyspark

    os.environ.setdefault("SPARK_HOME", str(Path(pyspark.__file__).parent))


def configure_session(spark) -> None:
    """Session settings the pipeline relies on; safe to apply to an existing session."""
    spark.conf.set("spark.sql.ansi.enabled", "true")
    spark.conf.set("spark.sql.session.timeZone", "UTC")


def _quiet_local_logging(spark) -> None:
    try:
        jvm = spark.sparkContext._jvm
        configurator = jvm.org.apache.logging.log4j.core.config.Configurator
        for name, level in _QUIET_LOGGERS:
            configurator.setLevel(name, jvm.org.apache.logging.log4j.Level.getLevel(level))
    except Exception:  # noqa: BLE001 - logging tweaks must never break a run
        pass


def get_or_create_spark(app_name: str = "invoice-recon", master: str | None = None):
    """Return ``(spark, created)``; ``created`` is False when an active session was reused."""
    from pyspark.sql import SparkSession

    active = SparkSession.getActiveSession()
    if active is not None:
        configure_session(active)
        return active, False

    prepare_local_environment()
    from delta import configure_spark_with_delta_pip

    builder = (
        SparkSession.builder.appName(app_name)
        .master(master or os.environ.get("INVOICE_RECON_SPARK_MASTER", "local[4]"))
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
        .config("spark.jars.excludes", ",".join(BUNDLED_BY_SPARK))
        .config("spark.sql.shuffle.partitions", os.environ.get("INVOICE_RECON_SHUFFLE_PARTITIONS", "8"))
        # Delta rebuilds table state with 50 partitions by default; on one machine with small
        # tables that only adds task overhead (measured ~8.5 s -> ~5 s per commit locally).
        .config("spark.databricks.delta.snapshotPartitions", "2")
        .config("spark.sql.ansi.enabled", "true")
        .config("spark.sql.session.timeZone", "UTC")
        .config("spark.ui.enabled", "false")
        .config("spark.ui.showConsoleProgress", "false")
        .config("spark.driver.host", "127.0.0.1")
        .config("spark.driver.bindAddress", "127.0.0.1")
    )
    try:
        spark = configure_spark_with_delta_pip(builder).getOrCreate()
    except Exception as exc:  # noqa: BLE001 - any start-up failure is an environment problem
        raise EnvironmentProblem(f"Spark failed to start: {str(exc).splitlines()[0] if str(exc) else exc!r}") from exc
    _quiet_local_logging(spark)
    configure_session(spark)
    return spark, True
