"""Delta Lake reads and writes: explicit schemas, per-batch idempotent overwrites, count checks.

Every batch table is partitioned by ``_batch_id`` and written with ``replaceWhere`` on that
column: re-running a batch replaces exactly its slice in one Delta commit and leaves other
batches untouched. The control table ``ops_batch_runs`` is upserted with MERGE.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from delta.tables import DeltaTable
from pyspark import StorageLevel
from pyspark.errors import AnalysisException
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import StructType

from . import __version__
from .config import InputError, Lakehouse, ValidationFailed, validate_batch_id
from .schemas import OPS_BATCH_RUNS, TABLE_SCHEMAS


def schema_problems(actual: StructType, expected: StructType) -> list[str]:
    """Compare column names, order and types; nullability is deliberately ignored."""
    problems = []
    actual_fields = [(f.name, f.dataType.simpleString()) for f in actual.fields]
    expected_fields = [(f.name, f.dataType.simpleString()) for f in expected.fields]
    if [n for n, _ in actual_fields] != [n for n, _ in expected_fields]:
        missing = sorted(set(n for n, _ in expected_fields) - set(n for n, _ in actual_fields))
        extra = sorted(set(n for n, _ in actual_fields) - set(n for n, _ in expected_fields))
        problems.append(f"columns differ (missing={missing}, unexpected={extra}, or order differs)")
    for (name, actual_type), (_, expected_type) in zip(actual_fields, expected_fields):
        if actual_type != expected_type:
            problems.append(f"{name}: {actual_type} != {expected_type}")
    return problems


def table_exists(spark: SparkSession, path: str) -> bool:
    return DeltaTable.isDeltaTable(spark, path)


_VERIFIED: set = set()  # (session id, path) pairs already checked in this process


def ensure_table(spark: SparkSession, path: str, schema: StructType, partitioned: bool = True) -> None:
    """Create the table from its explicit schema the first time; afterwards check it still matches."""
    key = (id(spark), path)
    if key in _VERIFIED and table_exists(spark, path):
        return
    if not table_exists(spark, path):
        builder = DeltaTable.createIfNotExists(spark).location(path).addColumns(schema)
        if partitioned:
            builder = builder.partitionedBy("_batch_id")
        builder.execute()
    problems = schema_problems(spark.read.format("delta").load(path).schema, schema)
    if problems:
        raise ValidationFailed(f"Delta table at {path} does not match its declared schema: {'; '.join(problems)}")
    _VERIFIED.add(key)


def write_batch(df: DataFrame, path: str, batch_id: str, schema: StructType) -> int:
    """Replace one batch slice; return the row count after reading it back from Delta."""
    validate_batch_id(batch_id)
    problems = schema_problems(df.schema, schema)
    if problems:
        raise ValidationFailed(f"refusing to write {path}: {'; '.join(problems)}")
    spark = df.sparkSession
    ensure_table(spark, path, schema)
    df = df.persist(StorageLevel.MEMORY_AND_DISK)
    try:
        expected = df.count()
        foreign = df.filter(F.col("_batch_id").isNull() | (F.col("_batch_id") != batch_id)).count()
        if foreign:
            raise ValidationFailed(f"refusing to write {path}: {foreign} rows do not belong to batch {batch_id}")
        (df.write.format("delta").mode("overwrite")
         .option("replaceWhere", f"_batch_id = '{batch_id}'")
         .save(path))
    finally:
        df.unpersist()
    written = read_batch(spark, path, batch_id).count()
    if written != expected:
        raise ValidationFailed(f"{path}: wrote {expected} rows for {batch_id} but read back {written}")
    return written


def read_table(spark: SparkSession, path: str) -> DataFrame:
    if not table_exists(spark, path):
        raise InputError(f"Delta table not found at {path}; run the upstream stage first")
    return spark.read.format("delta").load(path)


def read_batch(spark: SparkSession, path: str, batch_id: str) -> DataFrame:
    validate_batch_id(batch_id)
    return read_table(spark, path).filter(F.col("_batch_id") == batch_id)


def require_batch(spark: SparkSession, path: str, batch_id: str) -> DataFrame:
    df = read_batch(spark, path, batch_id)
    if df.limit(1).count() == 0:
        raise InputError(f"batch {batch_id} has no rows in {path}; run the upstream stage first")
    return df


def record_run(spark: SparkSession, lakehouse: Lakehouse, batch_id: str, stage: str, status: str,
               rows_in: int | None, rows_out: int | None, details: dict, rules_version: str) -> None:
    """Upsert one row per (batch, stage) into the control table with a Delta MERGE."""
    path = lakehouse.table("ops_batch_runs")
    ensure_table(spark, path, OPS_BATCH_RUNS, partitioned=False)
    source = spark.createDataFrame(
        [(batch_id, stage, status, rows_in, rows_out, json.dumps(details, sort_keys=True, default=str),
          rules_version, __version__, datetime.now(timezone.utc))],
        OPS_BATCH_RUNS,
    )
    (DeltaTable.forPath(spark, path).alias("t")
     .merge(source.alias("s"), "t.batch_id = s.batch_id AND t.stage = s.stage")
     .whenMatchedUpdateAll()
     .whenNotMatchedInsertAll()
     .execute())


def table_schema(name: str) -> StructType:
    return TABLE_SCHEMAS[name]


def safe_history(spark: SparkSession, path: str) -> list[dict]:
    """Delta commit history (version, operation) for reports; empty if the table is missing."""
    try:
        rows = DeltaTable.forPath(spark, path).history().select("version", "operation").collect()
    except AnalysisException:
        return []
    return sorted(({"version": r.version, "operation": r.operation} for r in rows), key=lambda r: r["version"])
