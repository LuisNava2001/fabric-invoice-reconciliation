# Data quality

Nothing is dropped silently. Every landing line ends in exactly one place and the path is checked by
`validate` after each run.

```text
landing line ──> Bronze row (malformed rows kept, _parse_error set)
                 └─> Silver row: VALID | INVALID | DUPLICATE   (INVALID + DUPLICATE -> silver_quarantine)
                     └─> Gold row: exactly one status
blank line ────> bronze_ingestion_errors (BLANK_LINE)
bad header ────> batch rejected, bronze_ingestion_errors (SCHEMA_MISMATCH), exit code 3
```

## Bronze checks

| Check | Result |
| --- | --- |
| CSV header differs from the contract (names, order, count) | batch rejected; previous data for the batch is kept |
| First JSON record's fields differ from the contract | batch rejected |
| CSV row with a different field count | kept with `_parse_error`; becomes `INVALID_RECORD / MALFORMED_ROW` |
| JSON row that is not an object, or with missing/extra fields | kept with `_parse_error`; `MALFORMED_ROW` |
| Blank line | logged as `BLANK_LINE`, not a record |

Bronze stores every field as the original string. Numeric JSON amounts keep their literal text.

## Silver rules

The catalog is [`invoice_recon/dq.py`](../invoice_recon/dq.py). ERROR rules quarantine the record;
WARNING rules keep it eligible and travel to Gold as flags.

| Rule | Severity | Sources |
| --- | --- | --- |
| `MALFORMED_ROW` | ERROR | both |
| `MISSING_INVOICE_ID` / `MISSING_TRANSACTION_ID` | ERROR | invoices / ledger |
| `MISSING_SUPPLIER_ID`, `MALFORMED_SUPPLIER_ID` | ERROR | both |
| `MISSING_REFERENCE` | ERROR | both |
| `MISSING_DATE`, `INVALID_DATE` | ERROR | both |
| `MISSING_CURRENCY`, `INVALID_CURRENCY` | ERROR | both |
| `MISSING_AMOUNT`, `INVALID_AMOUNT`, `AMOUNT_OUT_OF_RANGE` | ERROR | both |
| `TOTAL_INCONSISTENT` | ERROR | invoices |
| `MISSING_PERIOD`, `INVALID_PERIOD` | ERROR | ledger |
| `DUPLICATE_EXACT`, `DUPLICATE_CONFLICT` | ERROR | both |
| `OUT_OF_PERIOD` | WARNING | both |
| `AMBIGUOUS_DATE`, `PERIOD_INCONSISTENT` | WARNING | ledger |
| `MISSING_PAYMENT_STATUS`, `UNKNOWN_PAYMENT_STATUS` | WARNING | ledger |

The reason stored for an INVALID record is its highest-priority error (the catalog order); all failed
rules stay in `dq_errors`.

## Normalization

| Field | Treatment |
| --- | --- |
| All text | zero-width characters removed; NBSP, tabs and line breaks become spaces; runs collapsed; trimmed; empty becomes NULL |
| IDs, currency, payment status | upper case, internal whitespace removed |
| `supplier_id` | `SUP-####`; `SUP0042`, `sup-0042` and `SUP-0042` followed by a non-breaking space all become `SUP-0042` |
| `invoice_reference` | cleaned text kept for evidence; key = upper case `A-Z0-9` only |
| Amounts | `^-?\d+(\.\d{1,4})?$`, or correctly grouped thousands (`1,234.50`); `try_cast` to `DECIMAL(18,4)` |
| Invoice date | ISO `YYYY-MM-DD` only, strict calendar check (`2026-02-30` is invalid) |
| Accounting period | `YYYY-MM`, `YYYY-M` or `YYYYMM`, month 01-12 |

## Dates are validated, not guessed

| Posting date text | Result |
| --- | --- |
| `2026-03-04`, `2026/03/04`, `04-Mar-2026` | unambiguous |
| `14/03/2026` | only D/M is a calendar date: 14 March, basis `D/M/YYYY_ONLY_VALID_READING` |
| `03/14/2026` | only M/D is a calendar date: 14 March |
| `03/03/2026` | both readings agree |
| `04/03/2026` | 4 March or 3 April: `posting_date` stays NULL, both candidates kept, `AMBIGUOUS_DATE` |
| `31/02/2026` | no valid reading: `INVALID_DATE` |

The accounting period is *not* used to pick a reading. A record with an ambiguous date can still match
on rule R1 (the date is not part of the key), but it goes to review.

## Duplicates

Duplicate detection groups VALID-shaped rows by normalized record ID (NULL IDs and malformed rows are
never grouped). A content hash over the cleaned fields decides between:

* **exact** duplicates: the earliest line survives; later copies are `DUPLICATE_EXACT` with
  `duplicate_of_line`;
* **conflicting** duplicates: same ID, different content. No copy is trusted; all are
  `DUPLICATE_CONFLICT`.

## Per-batch metrics

`silver_dq_metrics` holds one row per catalog rule, source and batch, including rules with zero failures,
with `failed_records`, `total_records` and `failure_rate`. `gold_batch_metrics` adds records with any
error or warning. Reports and the demo list the rules that fired.

## Record-conservation checks (`validate`)

| Check | Meaning |
| --- | --- |
| `LANDING_TO_BRONZE[source]` | non-blank landing records, re-counted with a line-mode reader, equal Bronze rows |
| `BRONZE_TO_SILVER[source]`, `SILVER_TO_GOLD[side]` | same set of line numbers in both layers |
| `SILVER_STATUS_PARTITION`, `QUARANTINE_COMPLETE`, `QUARANTINE_HAS_REASON` | every non-VALID row is quarantined with a reason |
| `GOLD_ONE_ROW_PER_RECORD`, `STATUS_IN_CATALOG` | one known status per record |
| `NO_NULL_KEY_MATCH`, `ONE_TO_ONE_MATCHES`, `COUNTERPARTS_SYMMETRIC` | no NULL match, no record matched twice, both sides agree |
| `MATCHED_SAME_CURRENCY`, `MATCHED_WITHIN_TOLERANCE`, `NO_CROSS_CURRENCY_COMPARISON` | rule R1 holds on stored data |
| `ONLY_VALID_RECORDS_DECIDED`, `SUGGESTIONS_NEVER_APPROVED` | quarantined records never matched; suggestions stay suggestions |
| `EXCEPTIONS_MATCH_REVIEW_FLAG`, `METRICS_CONSISTENT` | derived tables agree with the reconciliation table |
| `SYNTHETIC_GROUND_TRUTH`, `SYNTHETIC_SUGGESTIONS` | synthetic data only (designed-outcome agreement, not accuracy against real data): every record has its designed status and review decision, its designed reason when one was designed, and at least its designed flags; every designed suggestion is produced |
