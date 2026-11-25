"""Delta Lake: explicit schemas, per-batch idempotent overwrites, isolation, MERGE, count checks."""

import pytest
from delta.tables import DeltaTable
from pyspark.errors import AnalysisException
from pyspark.sql import functions as F
from pyspark.sql.types import IntegerType, StringType, StructField, StructType

from invoice_recon.config import InputError, Lakehouse, ValidationFailed
from invoice_recon.delta_io import (
    read_batch,
    read_table,
    record_run,
    require_batch,
    schema_problems,
    table_exists,
    write_batch,
)

pytestmark = pytest.mark.spark

SCHEMA = StructType([StructField("_batch_id", StringType()), StructField("id", IntegerType()), StructField("v", StringType())])


def _df(spark, batch, rows):
    return spark.createDataFrame([(batch, i, v) for i, v in rows], SCHEMA)


def _versions(spark, path):
    return [(r.version, r.operation) for r in DeltaTable.forPath(spark, path).history().orderBy("version").collect()]


def test_write_read_roundtrip_with_declared_schema(spark, tmp_path):
    path = (tmp_path / "t").as_posix()
    assert write_batch(_df(spark, "b1", [(1, "a"), (2, "b")]), path, "b1", SCHEMA) == 2
    assert table_exists(spark, path) and (tmp_path / "t" / "_delta_log").is_dir()
    stored = read_table(spark, path)
    assert schema_problems(stored.schema, SCHEMA) == []
    assert sorted((r.id, r.v) for r in read_batch(spark, path, "b1").collect()) == [(1, "a"), (2, "b")]
    detail = spark.sql(f"DESCRIBE DETAIL delta.`{path}`").collect()[0]
    assert detail.partitionColumns == ["_batch_id"] and detail.format == "delta"


def test_rewriting_a_batch_is_idempotent_and_isolated(spark, tmp_path):
    path = (tmp_path / "t").as_posix()
    write_batch(_df(spark, "b1", [(1, "a"), (2, "b")]), path, "b1", SCHEMA)
    write_batch(_df(spark, "b2", [(9, "z")]), path, "b2", SCHEMA)
    before = sorted(map(tuple, read_table(spark, path).collect()))
    write_batch(_df(spark, "b1", [(1, "a"), (2, "b")]), path, "b1", SCHEMA)
    assert sorted(map(tuple, read_table(spark, path).collect())) == before, "same input, same table content"
    write_batch(_df(spark, "b1", [(3, "c")]), path, "b1", SCHEMA)
    assert [r.id for r in read_batch(spark, path, "b1").collect()] == [3], "the batch slice is replaced, not appended"
    assert [r.id for r in read_batch(spark, path, "b2").collect()] == [9], "other batches are untouched"
    operations = [op for _, op in _versions(spark, path)]
    assert "CREATE" in operations[0] and operations.count("WRITE") == 4


def test_schema_mismatch_is_refused_before_writing(spark, tmp_path):
    path = (tmp_path / "t").as_posix()
    write_batch(_df(spark, "b1", [(1, "a")]), path, "b1", SCHEMA)
    versions = _versions(spark, path)
    wrong = _df(spark, "b1", [(1, "a")]).withColumn("extra", F.lit(1))
    with pytest.raises(ValidationFailed, match="columns differ"):
        write_batch(wrong, path, "b1", SCHEMA)
    retyped = _df(spark, "b1", [(1, "a")]).withColumn("id", F.col("id").cast("string"))
    with pytest.raises(ValidationFailed, match="id: string != int"):
        write_batch(retyped, path, "b1", SCHEMA)
    assert _versions(spark, path) == versions, "no commit was made"


def test_delta_itself_enforces_the_table_schema(spark, tmp_path):
    path = (tmp_path / "t").as_posix()
    write_batch(_df(spark, "b1", [(1, "a")]), path, "b1", SCHEMA)
    with pytest.raises(AnalysisException):
        _df(spark, "b1", [(1, "a")]).withColumn("extra", F.lit(1)).write.format("delta").mode("append").save(path)


def test_rows_from_another_batch_are_refused(spark, tmp_path):
    path = (tmp_path / "t").as_posix()
    mixed = _df(spark, "b1", [(1, "a")]).unionByName(_df(spark, "b2", [(2, "b")]))
    with pytest.raises(ValidationFailed, match="do not belong to batch b1"):
        write_batch(mixed, path, "b1", SCHEMA)


def test_replace_where_violation_leaves_no_commit(spark, tmp_path):
    """Delta's own guard: data outside the replaceWhere predicate fails and the version is unchanged."""
    path = (tmp_path / "t").as_posix()
    write_batch(_df(spark, "b1", [(1, "a")]), path, "b1", SCHEMA)
    versions = _versions(spark, path)
    with pytest.raises(AnalysisException, match="DELTA_REPLACE_WHERE_MISMATCH"):
        (_df(spark, "b2", [(2, "b")]).write.format("delta").mode("overwrite")
         .option("replaceWhere", "_batch_id = 'b1'").save(path))
    assert _versions(spark, path) == versions
    assert [r.id for r in read_table(spark, path).collect()] == [1]


def test_missing_tables_and_empty_batches_are_input_errors(spark, tmp_path):
    path = (tmp_path / "missing").as_posix()
    with pytest.raises(InputError, match="not found"):
        read_table(spark, path)
    present = (tmp_path / "t").as_posix()
    write_batch(_df(spark, "b1", [(1, "a")]), present, "b1", SCHEMA)
    with pytest.raises(InputError, match="has no rows"):
        require_batch(spark, present, "b2")
    with pytest.raises(InputError):
        read_batch(spark, present, "b1' OR '1'='1")


def test_control_table_is_upserted_with_merge(spark, tmp_path):
    lakehouse = Lakehouse.local(tmp_path)
    record_run(spark, lakehouse, "b1", "bronze", "REJECTED", None, None, {"problems": ["x"]}, "r1")
    record_run(spark, lakehouse, "b1", "bronze", "SUCCEEDED", 10, 10, {"rows": 10}, "r1")
    record_run(spark, lakehouse, "b1", "silver", "SUCCEEDED", 10, 10, {}, "r1")
    rows = spark.read.format("delta").load(lakehouse.table("ops_batch_runs")).orderBy("stage").collect()
    assert [(r.batch_id, r.stage, r.status, r.rows_out) for r in rows] == [("b1", "bronze", "SUCCEEDED", 10),
                                                                           ("b1", "silver", "SUCCEEDED", 10)]
    assert [op for _, op in _versions(spark, lakehouse.table("ops_batch_runs"))].count("MERGE") == 3
