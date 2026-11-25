"""Data-quality rule catalog. Silver emits only these codes; metrics report every rule, even at zero."""

from __future__ import annotations

from .config import SOURCE_INVOICES, SOURCE_LEDGER

ERROR = "ERROR"      # record is quarantined (INVALID_RECORD / DUPLICATE) and never matched
WARNING = "WARNING"  # record stays eligible; the flag travels to Gold and may require review

_COMMON = (
    ("MALFORMED_ROW", ERROR, "Row could not be parsed against the source contract (field count, JSON shape or field names)."),
    ("MISSING_SUPPLIER_ID", ERROR, "Supplier identifier is empty."),
    ("MALFORMED_SUPPLIER_ID", ERROR, "Supplier identifier does not match SUP-#### after normalization."),
    ("MISSING_REFERENCE", ERROR, "Invoice reference is empty after removing whitespace and separators."),
    ("MISSING_DATE", ERROR, "Date is empty."),
    ("INVALID_DATE", ERROR, "Date does not match an accepted format or is not a calendar date."),
    ("MISSING_CURRENCY", ERROR, "Currency is empty."),
    ("INVALID_CURRENCY", ERROR, "Currency is not in the configured ISO 4217 allow-list."),
    ("MISSING_AMOUNT", ERROR, "A required amount is empty."),
    ("INVALID_AMOUNT", ERROR, "Amount is not a decimal number (max 4 decimals, optional thousands separators)."),
    ("AMOUNT_OUT_OF_RANGE", ERROR, "Amount is not positive or exceeds the configured maximum."),
    ("DUPLICATE_EXACT", ERROR, "Repeated record ID with identical normalized content; the earliest line survives."),
    ("DUPLICATE_CONFLICT", ERROR, "Repeated record ID with different content; no copy is trusted."),
)

RULES = {
    SOURCE_INVOICES: (
        ("MISSING_INVOICE_ID", ERROR, "Invoice ID is empty."),
        *_COMMON,
        ("TOTAL_INCONSISTENT", ERROR, "subtotal + tax_amount differs from total_amount by more than the currency tolerance."),
        ("OUT_OF_PERIOD", WARNING, "Invoice date falls outside the batch reconciliation period."),
    ),
    SOURCE_LEDGER: (
        ("MISSING_TRANSACTION_ID", ERROR, "Ledger transaction ID is empty."),
        *_COMMON,
        ("MISSING_PERIOD", ERROR, "Accounting period is empty."),
        ("INVALID_PERIOD", ERROR, "Accounting period is not YYYY-MM / YYYYMM with month 01-12."),
        ("AMBIGUOUS_DATE", WARNING, "Posting date reads as two different valid dates (D/M vs M/D); not resolved."),
        ("PERIOD_INCONSISTENT", WARNING, "Posting date month differs from the accounting period."),
        ("OUT_OF_PERIOD", WARNING, "Accounting period differs from the batch reconciliation period."),
        ("MISSING_PAYMENT_STATUS", WARNING, "Payment status is empty."),
        ("UNKNOWN_PAYMENT_STATUS", WARNING, "Payment status is not in the configured list."),
    ),
}


def rule_ids(source: str, severity: str | None = None) -> list[str]:
    return [rule for rule, level, _ in RULES[source] if severity is None or level == severity]
