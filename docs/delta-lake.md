# Delta Lake

All tables are real Delta tables written and read with `delta-spark` 4.2.0 on Spark 4.1.1. They are
path-based tables under `Tables/` (no metastore), the layout a Fabric Lakehouse uses.

## Writes: overwrite by batch, not MERGE

| Table group | Write | Why |
| --- | --- | --- |
| Bronze, Silver, Gold batch tables | `mode("overwrite")` + `replaceWhere("_batch_id = '<id>'")` | Each stage is a pure function of its upstream batch. Replacing the slice is simpler than reconciling row by row, re-running converges to the same content, and a corrected landing file fully replaces what the old one produced (no stale rows). |
| `ops_batch_runs` | `MERGE` on `(batch_id, stage)` | One row per batch and stage that must be updated in place (status, counts, details) without rewriting other batches' rows. |

MERGE was not used for the data tables because the stages recompute the whole batch anyway: a MERGE would
need a delete clause for rows that disappeared from a corrected file, which `replaceWhere` gives for free.

## Safeguards around each write (`delta_io.write_batch`)

1. **Explicit schema.** The DataFrame's columns, order and types must equal the declared schema, or the
   write is refused before touching the table. Tables are created from the declared schema
   (`DeltaTable.createIfNotExists(...).addColumns(schema).partitionedBy("_batch_id")`), never inferred.
2. **Batch guard.** A frame containing rows for another batch is refused. The batch ID is allow-listed
   (`[A-Za-z0-9][A-Za-z0-9_.-]{0,63}`) because it is interpolated into the `replaceWhere` predicate.
3. **Count validation.** The row count before the write must equal the count read back from Delta for
   that batch after the write.

Delta adds its own checks, which the tests exercise: appending a frame with an extra column fails
(schema enforcement), and writing rows outside the `replaceWhere` predicate fails with
`DELTA_REPLACE_WHERE_MISMATCH`.

## What is verified, and what is not

| Property | Status | Evidence |
| --- | --- | --- |
| Real Delta write, read, `_delta_log`, partitioning by `_batch_id` | Verified | `tests/test_delta.py` (`DESCRIBE DETAIL`) |
| Re-running a batch produces identical table content | Verified | `test_rerunning_a_batch_changes_nothing_and_leaves_the_other_batch_alone` compares SHA-256 digests of every batch table before and after |
| Rewriting one batch leaves other batches untouched | Verified | same test, plus `test_rewriting_a_batch_is_idempotent_and_isolated` |
| A refused write (schema, predicate violation) creates no new table version | Verified | version history compared before and after |
| Corrected landing file replaces the old Bronze slice | Verified | `test_corrected_landing_file_replaces_the_bronze_slice` |
| A rejected batch keeps the previously ingested data | Verified | `test_schema_mismatch_rejects_the_batch_and_keeps_previous_data` |
| Atomicity of a single commit if the process dies mid-write | **Not tested** | relies on Delta's commit protocol; no crash was simulated |
| Several writers on the same table at the same time | **Not tested** | the CLI runs one batch at a time; concurrent runs are not supported |
| Consistency across tables of one stage | **Not provided** | each table is its own commit; a failure between two writes leaves the stage half-written until it is re-run, which `ops_batch_runs` and `validate` make visible |
| Time travel, `VACUUM`, `OPTIMIZE`, checkpoints tuning | Not used | |

## Reading the tables

```python
spark.read.format("delta").load("lakehouse/Tables/gold_reconciliation").groupBy("status").count().show()
spark.sql("DESCRIBE HISTORY delta.`lakehouse/Tables/gold_reconciliation`").show()
```

## Local performance note

On the development machine (Windows 11, corporate endpoint protection) one Delta commit takes about
5 seconds even for tiny tables, while the Spark jobs inside it take about 1.5 seconds. A batch writes
12 batch tables plus 3 MERGEs into the control table, so commit overhead dominates local run time. Two settings are applied to local
sessions only: `spark.databricks.delta.snapshotPartitions=2` (measured ~8.5 s → ~5 s per commit) and
`spark.jars.excludes` for artifacts that PySpark already ships (start-up ~82 s → ~34 s).
