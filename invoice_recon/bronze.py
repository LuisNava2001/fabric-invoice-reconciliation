"""Bronze: land each source file line by line as raw strings with lineage. No line is dropped.

Each landing file is read whole and split into physical lines with their position
(``posexplode``), so every record keeps its line number regardless of how Spark partitions
the file. Batch files are expected to be far below Spark's 2 GB per-row limit.

* Invoices (CSV): the header must equal the contract exactly or the batch is rejected.
  Rows are parsed with ``from_csv`` in PERMISSIVE mode; a row whose field count differs
  from the header is kept with ``_parse_error`` set and its fields left empty.
* Ledger (JSON Lines): the first record's keys must equal the contract or the batch is
  rejected. A row that is not a JSON object, or whose keys differ, is kept with
  ``_parse_error`` set. Numeric JSON amounts keep their literal text from the raw line
  (Spark's JSON reader would otherwise pass them through a double).
"""

from __future__ import annotations

import json

from pyspark.errors import AnalysisException
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F

from .config import (
    INVOICE_COLUMNS,
    LEDGER_COLUMNS,
    MANIFEST_FILE,
    SOURCE_INVOICES,
    SOURCE_LEDGER,
    InputError,
    Lakehouse,
    validate_batch_id,
    validate_period,
)
from .schemas import BRONZE_INGESTION_ERRORS

CSV_OPTIONS = {"mode": "PERMISSIVE", "columnNameOfCorruptRecord": "_corrupt_record", "escape": '"'}
JSON_OPTIONS = {"mode": "PERMISSIVE", "columnNameOfCorruptRecord": "_corrupt_record"}
_NUMBER_LITERAL = r'"recorded_amount"\s*:\s*(-?[0-9][0-9.eE+-]*)'


def read_manifest(spark: SparkSession, lakehouse: Lakehouse, batch_id: str) -> dict:
    path = f"{lakehouse.landing(batch_id)}/{MANIFEST_FILE}"
    try:
        rows = spark.read.text(path, wholetext=True).collect()
    except AnalysisException as exc:
        raise InputError(f"batch manifest not found: {path}") from exc
    if not rows:
        raise InputError(f"batch manifest is empty: {path}")
    try:
        manifest = json.loads(rows[0].value)
    except json.JSONDecodeError as exc:
        raise InputError(f"batch manifest is not valid JSON: {path}: {exc}") from exc
    if not isinstance(manifest, dict) or manifest.get("batch_id") != batch_id:
        raise InputError(f"manifest {path} does not declare batch_id {batch_id!r}")
    validate_period(manifest.get("reconciliation_period"))
    sources = manifest.get("sources")
    if not isinstance(sources, dict) or set(sources) != {SOURCE_INVOICES, SOURCE_LEDGER}:
        raise InputError(f"manifest {path} must list exactly the sources {SOURCE_INVOICES} and {SOURCE_LEDGER}")
    for name in sources.values():
        if not isinstance(name, str) or "/" in name or "\\" in name or name.startswith("."):
            raise InputError(f"manifest {path} has an invalid source file name {name!r}")
    return manifest


def discover_batches(spark: SparkSession, lakehouse: Lakehouse) -> list[str]:
    """Batch ids found under Files/landing/*/batch.json (folder name must equal batch_id)."""
    pattern = f"{lakehouse.landing_root()}/*/{MANIFEST_FILE}"
    try:
        rows = spark.read.text(pattern, wholetext=True).select("value", F.col("_metadata.file_path").alias("path")).collect()
    except AnalysisException:
        return []
    batch_ids = []
    for row in rows:
        try:
            batch_id = validate_batch_id(json.loads(row.value).get("batch_id"))
        except (json.JSONDecodeError, AttributeError) as exc:
            raise InputError(f"unreadable batch manifest: {row.path}") from exc
        if not row.path.rstrip("/").endswith(f"/{batch_id}/{MANIFEST_FILE}"):
            raise InputError(f"manifest {row.path} declares batch_id {batch_id!r} but lives in another folder")
        batch_ids.append(batch_id)
    return sorted(batch_ids)


def read_lines(spark: SparkSession, path: str) -> DataFrame:
    """One row per physical line: ``_line_number`` (1-based) and ``_raw_line`` (no line ending).

    The final line ending is removed before splitting, so it does not produce an empty
    trailing "line". (An earlier version computed ``size(split(value))`` next to the
    ``posexplode``; Spark then re-split the whole file for every generated row, which was
    quadratic: 24.8 s instead of 0.5 s for a 5,101-line file.)
    """
    try:
        whole = spark.read.text(path, wholetext=True)
    except AnalysisException as exc:
        raise InputError(f"landing file not found: {path}") from exc
    text = F.regexp_replace(F.col("value"), r"\r?\n\z", "")
    return whole.filter(F.length("value") > 0).select(F.posexplode(F.split(text, "\n")).alias("_pos", "_line")).select(
        (F.col("_pos") + 1).cast("int").alias("_line_number"),
        F.regexp_replace(F.col("_line"), "\r$", "").alias("_raw_line"),
    )


def _lineage(batch_id: str, source: str, relative_file: str) -> list:
    return [
        F.lit(batch_id).alias("_batch_id"),
        F.lit(source).alias("_source_system"),
        F.lit(relative_file).alias("_source_file"),
        F.col("_line_number"),
        F.sha2(F.col("_raw_line"), 256).alias("_record_hash"),
        F.col("_raw_line"),
    ]


def _errors(rows: DataFrame, batch_id: str, source: str, relative_file: str, error_type, detail) -> DataFrame:
    return rows.select(
        F.lit(batch_id).alias("_batch_id"),
        F.lit(source).alias("_source_system"),
        F.lit(relative_file).alias("_source_file"),
        F.col("_line_number").cast("int").alias("_line_number"),
        (error_type if not isinstance(error_type, str) else F.lit(error_type)).alias("error_type"),
        (detail if not isinstance(detail, str) else F.lit(detail)).alias("error_detail"),
        F.col("_raw_line"),
    )


def file_error(spark: SparkSession, batch_id: str, source: str, relative_file: str, detail: str,
               raw_line: str | None) -> DataFrame:
    return spark.createDataFrame(
        [(batch_id, source, relative_file, None, "SCHEMA_MISMATCH", detail, raw_line)], BRONZE_INGESTION_ERRORS)


def _row_errors(lines: DataFrame, bronze: DataFrame, batch_id: str, source: str, relative_file: str) -> DataFrame:
    malformed = bronze.filter(F.col("_parse_error").isNotNull())
    parse_type = F.when(F.col("_parse_error").startswith("SCHEMA_DRIFT"), "SCHEMA_DRIFT").otherwise("MALFORMED_ROW")
    blank = lines.filter(F.trim(F.col("_raw_line")) == "")
    return _errors(malformed, batch_id, source, relative_file, parse_type, F.col("_parse_error")).unionByName(
        _errors(blank, batch_id, source, relative_file, "BLANK_LINE", "blank line skipped (not a record)"))


def ingest_invoices(spark: SparkSession, lakehouse: Lakehouse, batch_id: str, file_name: str):
    """Return ``(bronze_df | None, errors_df, file_problem | None)``."""
    relative = Lakehouse.relative_landing_file(batch_id, file_name)
    lines = read_lines(spark, f"{lakehouse.landing(batch_id)}/{file_name}")
    header = [row._raw_line for row in lines.filter(F.col("_line_number") == 1).collect()]
    if not header:
        problem = "file is empty (no header)"
    else:
        found = [cell.strip() for cell in header[0].lstrip("﻿").split(",")]
        problem = None if found == list(INVOICE_COLUMNS) else f"header {found} differs from contract {list(INVOICE_COLUMNS)}"
    if problem:
        return None, file_error(spark, batch_id, SOURCE_INVOICES, relative, problem, header[0] if header else None), problem

    data = lines.filter(F.col("_line_number") > 1)
    rows = data.filter(F.trim(F.col("_raw_line")) != "")
    ddl = ", ".join(f"`{column}` STRING" for column in INVOICE_COLUMNS) + ", `_corrupt_record` STRING"
    parsed = rows.withColumn("_p", F.from_csv(F.col("_raw_line"), ddl, CSV_OPTIONS))
    well_formed = F.col("_p._corrupt_record").isNull()
    bronze = parsed.select(
        *_lineage(batch_id, SOURCE_INVOICES, relative),
        F.when(~well_formed, F.lit("MALFORMED_ROW: field count differs from the header")).alias("_parse_error"),
        *[F.when(well_formed, F.col(f"_p.{column}")).alias(column) for column in INVOICE_COLUMNS],
    )
    return bronze, _row_errors(data, bronze, batch_id, SOURCE_INVOICES, relative), None


def ingest_ledger(spark: SparkSession, lakehouse: Lakehouse, batch_id: str, file_name: str):
    """Return ``(bronze_df | None, errors_df, file_problem | None)``."""
    relative = Lakehouse.relative_landing_file(batch_id, file_name)
    lines = read_lines(spark, f"{lakehouse.landing(batch_id)}/{file_name}")
    rows = lines.filter(F.trim(F.col("_raw_line")) != "")
    first = [row._raw_line for row in rows.orderBy("_line_number").limit(1).collect()]
    problem = None
    if not first:
        problem = "file has no records"
    else:
        try:
            probe = json.loads(first[0])
        except json.JSONDecodeError:
            probe = None
        if not isinstance(probe, dict) or sorted(probe) != sorted(LEDGER_COLUMNS):
            found = sorted(probe) if isinstance(probe, dict) else "not a JSON object"
            problem = f"first record fields {found} differ from contract {sorted(LEDGER_COLUMNS)}"
    if problem:
        return None, file_error(spark, batch_id, SOURCE_LEDGER, relative, problem, first[0] if first else None), problem

    keys = F.json_object_keys(F.col("_raw_line"))
    expected = F.array(*[F.lit(column) for column in sorted(LEDGER_COLUMNS)])
    parse_error = (F.when(keys.isNull(), F.lit("MALFORMED_ROW: not a JSON object"))
                   .when(F.array_sort(keys) != expected, F.lit("SCHEMA_DRIFT: fields differ from the contract")))
    ddl = ", ".join(f"`{column}` STRING" for column in LEDGER_COLUMNS) + ", `_corrupt_record` STRING"
    parsed = rows.withColumn("_p", F.from_json(F.col("_raw_line"), ddl, JSON_OPTIONS)).withColumn("_err", parse_error)
    literal = F.regexp_extract(F.col("_raw_line"), _NUMBER_LITERAL, 1)
    value = {column: F.col(f"_p.{column}") for column in LEDGER_COLUMNS}
    value["recorded_amount"] = F.when(F.length(literal) > 0, literal).otherwise(F.col("_p.recorded_amount"))
    ok = F.col("_err").isNull()
    bronze = parsed.select(
        *_lineage(batch_id, SOURCE_LEDGER, relative),
        F.col("_err").alias("_parse_error"),
        *[F.when(ok, value[column]).alias(column) for column in LEDGER_COLUMNS],
    )
    return bronze, _row_errors(lines, bronze, batch_id, SOURCE_LEDGER, relative), None
