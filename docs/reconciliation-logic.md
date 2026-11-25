# Reconciliation logic

## Rule R1, the only rule that can produce MATCHED

```text
same canonical supplier_id
AND same normalized invoice reference   (upper case, only A-Z and 0-9 kept)
AND same currency
AND |invoice total_amount - ledger recorded_amount| <= tolerance of that currency
```

Tolerances live in [`reconciliation_rules.json`](../invoice_recon/data/reconciliation_rules.json): one
minor unit (`0.01` for USD, EUR, MXN, CAD; `1` for JPY). The comparison is inclusive, so a difference
equal to the tolerance matches and is flagged `ROUNDING_DIFFERENCE`.

Only Silver records with `record_status = VALID` take part. A VALID record always has a supplier ID and
a reference, so its match key is never NULL.

## Why a FULL OUTER JOIN of key counts

A plain FULL OUTER JOIN of invoices with ledger rows on the match key has three problems:

1. Rows with a NULL key never join (NULL = NULL is not true), so they come out twice, once per side,
   looking like legitimate one-sided records.
2. When a key has *n* invoices and *m* ledger rows, the join produces *n × m* rows: one invoice can
   appear matched several times.
3. Which of those rows "wins" would depend on row order.

The engine therefore:

1. keeps NULL keys out of the join entirely (those records are already INVALID in Silver);
2. counts VALID records per key on each side and FULL OUTER JOINs the two **count** tables, so every
   key appears exactly once with `(n_inv, n_led)`;
3. classifies each key: `(1, 1)` pair, `(n, 0)` / `(0, m)` one-sided, anything with `n > 1` or `m > 1`
   ambiguous;
4. joins records back only for `(1, 1)` keys. A record cannot be matched twice because its key has
   exactly one record on each side.

The full outer join keeps keys that exist on only one side (with zero on the other), which is what makes
`ONLY_IN_INVOICES` and `ONLY_IN_LEDGER` explicit instead of being lost by an inner join.

## Statuses (exactly one per record)

| Status | Condition | Reason codes |
| --- | --- | --- |
| `MATCHED` | pair key, same currency, difference within tolerance | `EXACT_AMOUNT`, `WITHIN_TOLERANCE` |
| `AMOUNT_MISMATCH` | pair key, same currency, difference above tolerance | `DIFFERENCE_ABOVE_TOLERANCE` |
| `CURRENCY_MISMATCH` | pair key, different currencies (amounts are not compared) | `CURRENCY_DIFFERS_NO_CONVERSION` |
| `ONLY_IN_INVOICES` / `ONLY_IN_LEDGER` | key present on one side only | `NO_COUNTERPART`, `COUNTERPART_NOT_ELIGIBLE` |
| `AMBIGUOUS` | more than one record on at least one side | `MULTIPLE_INVOICES_FOR_KEY`, `MULTIPLE_LEDGER_ENTRIES_FOR_KEY`, `MULTIPLE_CANDIDATES_BOTH_SIDES` |
| `DUPLICATE` | repeated record ID in its own source | `DUPLICATE_EXACT`, `DUPLICATE_CONFLICT` |
| `INVALID_RECORD` | a data-quality ERROR rule failed | the highest-priority rule, for example `MISSING_REFERENCE` |

`COUNTERPART_NOT_ELIGIBLE` means a record with the same key exists on the other side but was quarantined
(invalid or duplicate); the reviewer should look there first.

`DUPLICATE` is about the same record ID repeated inside one source. Two *different* IDs that share a
supplier and reference are not duplicates of each other: they are competing candidates (`AMBIGUOUS`),
for example a possible double posting.

## Flags and review

Flags add detail without changing the status:

| Flag | Origin | Sends a MATCHED record to review |
| --- | --- | --- |
| `REFERENCE_FORMAT_VARIANT` | references differ in case or separators but normalize to the same key | no |
| `ROUNDING_DIFFERENCE` | non-zero difference within tolerance | no |
| `AMBIGUOUS_DATE` | ledger posting date has two valid readings | yes |
| `PERIOD_INCONSISTENT` | posting date month differs from the accounting period | yes |
| `OUT_OF_PERIOD` | record belongs to a different period than the batch | yes |
| `UNKNOWN_PAYMENT_STATUS`, `MISSING_PAYMENT_STATUS` | ledger payment status | no |

A pair carries the union of both records' warnings plus its own flags. `requires_review` is true for
every status other than MATCHED and for MATCHED records with a review flag; those rows form
`gold_exceptions`, with a priority (HIGH: amount or currency mismatch, ambiguity, conflicting duplicate;
MEDIUM: one-sided, invalid, duplicate; LOW: matched with review flags) and a recommended action.

## Evidence

`gold_match_evidence` has one row per compared pair (decision MATCHED, AMOUNT_MISMATCH or
CURRENCY_MISMATCH) and one row per candidate pair of an ambiguous key (decision
`NOT_DECIDED_MULTIPLE_CANDIDATES`). Each row stores the raw and normalized references, both currencies,
both amounts, the difference, the tolerance, the flags and a sentence. This one comes from the default
run (batch-2026-03, flag `REFERENCE_FORMAT_VARIANT`):

```text
supplier_id SUP-0040 on both sides; reference 'UMC-036532' vs 'UMC 036532' normalize to UMC036532;
currency EUR on both sides; |9921.6500 - 9921.6500| = 0.0000 vs tolerance 0.0100
```

## Similarity suggestions (secondary)

Records left `ONLY_IN_INVOICES` and `ONLY_IN_LEDGER` are compared with two criteria:

| Criterion | Join | Kept when |
| --- | --- | --- |
| `SAME_REFERENCE_DIFFERENT_SUPPLIER` | same normalized reference, different supplier ID | supplier-name similarity >= 0.80 |
| `SAME_SUPPLIER_AMOUNT_SIMILAR_REFERENCE` | same supplier and currency, amount within tolerance | reference similarity >= 0.75 |

Similarity is `1 - Levenshtein distance / longer length` (Spark's built-in `levenshtein`), on names with
punctuation and legal suffixes (`LTD`, `LLC`, `INC`, ...) removed. Suggestions keep the score, the
criterion and an explanation, are capped at three per invoice, are **never auto-approved** and never
change a status. Matched records are never suggested, so similarity cannot override identifiers.

## Determinism

Re-running a batch gives identical row content in every batch table (verified by order-independent row digests in
the tests; the Delta files themselves are rewritten). The engine has no
order-dependent choice: survivors of exact duplicates are the earliest line, suggestion ranks break ties
on the ledger line, and reports sort everything they show.
