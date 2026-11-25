"""Source contracts, rule catalog, lakehouse layout and error types shared by every layer."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from importlib import resources
from pathlib import Path

SOURCE_INVOICES = "E_INVOICES"
SOURCE_LEDGER = "ERP_LEDGER"
SIDE_INVOICE = "INVOICE"
SIDE_LEDGER = "LEDGER"

INVOICE_FILE = "invoices.csv"
LEDGER_FILE = "ledger.jsonl"
MANIFEST_FILE = "batch.json"
GROUND_TRUTH_FILE = "expected_outcomes.jsonl"
GROUND_TRUTH_SUGGESTIONS_FILE = "expected_suggestions.jsonl"

# Source A: electronic invoices (CSV). supplier_name is not needed for matching; it is used only by the
# secondary similarity suggestions, never by deterministic matching.
INVOICE_COLUMNS = (
    "invoice_id", "supplier_id", "supplier_name", "invoice_date", "currency",
    "subtotal", "tax_amount", "total_amount", "invoice_reference",
)
# Source B: ERP ledger export (JSON Lines).
LEDGER_COLUMNS = (
    "transaction_id", "invoice_reference", "supplier_id", "supplier_name", "posting_date",
    "currency", "recorded_amount", "payment_status", "accounting_period",
)

# Reconciliation statuses: exactly one per source record.
STATUSES = (
    "MATCHED", "AMOUNT_MISMATCH", "CURRENCY_MISMATCH", "ONLY_IN_INVOICES", "ONLY_IN_LEDGER",
    "AMBIGUOUS", "DUPLICATE", "INVALID_RECORD",
)
# Flags add information to a status. Review flags send an otherwise MATCHED record to review.
REVIEW_FLAGS = ("AMBIGUOUS_DATE", "PERIOD_INCONSISTENT", "OUT_OF_PERIOD")
INFO_FLAGS = ("REFERENCE_FORMAT_VARIANT", "ROUNDING_DIFFERENCE", "UNKNOWN_PAYMENT_STATUS", "MISSING_PAYMENT_STATUS")

TABLES = {
    "bronze_invoices": "bronze_invoices",
    "bronze_ledger": "bronze_ledger",
    "bronze_ingestion_errors": "bronze_ingestion_errors",
    "silver_invoices": "silver_invoices",
    "silver_ledger": "silver_ledger",
    "silver_quarantine": "silver_quarantine",
    "silver_dq_metrics": "silver_dq_metrics",
    "gold_reconciliation": "gold_reconciliation",
    "gold_match_evidence": "gold_match_evidence",
    "gold_candidate_suggestions": "gold_candidate_suggestions",
    "gold_exceptions": "gold_exceptions",
    "gold_batch_metrics": "gold_batch_metrics",
    "ops_batch_runs": "ops_batch_runs",
}
BATCH_TABLES = tuple(name for name in TABLES if name != "ops_batch_runs")

EXIT_OK = 0
EXIT_INTERNAL = 1
EXIT_USAGE = 2
EXIT_INPUT = 3
EXIT_VALIDATION = 4
EXIT_ENVIRONMENT = 5

_BATCH_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")
_PERIOD = re.compile(r"^(\d{4})-(0[1-9]|1[0-2])$")
_CURRENCY = re.compile(r"^[A-Z]{3}$")


class PipelineError(Exception):
    """Base class for errors that map to a documented exit code."""

    exit_code = EXIT_INTERNAL


class InputError(PipelineError):
    """Missing or unusable input: landing files, manifest, upstream tables, schema mismatch."""

    exit_code = EXIT_INPUT


class ValidationFailed(PipelineError):
    """A record-conservation, invariant or drift check failed."""

    exit_code = EXIT_VALIDATION


class EnvironmentProblem(PipelineError):
    """Java, Hadoop native helpers or Spark itself are not usable."""

    exit_code = EXIT_ENVIRONMENT


def validate_batch_id(batch_id: str) -> str:
    """Batch ids end up in paths and in Delta replaceWhere predicates, so they are allow-listed."""
    if not isinstance(batch_id, str) or not _BATCH_ID.match(batch_id):
        raise InputError(f"invalid batch id {batch_id!r}: use letters, digits, '.', '_' or '-' (max 64)")
    return batch_id


def validate_period(period: str) -> str:
    if not isinstance(period, str) or not _PERIOD.match(period):
        raise InputError(f"invalid period {period!r}: expected YYYY-MM")
    return period


def shift_period(period: str, months: int) -> str:
    year, month = (int(part) for part in validate_period(period).split("-"))
    index = year * 12 + (month - 1) + months
    return f"{index // 12:04d}-{index % 12 + 1:02d}"


@dataclass(frozen=True)
class CurrencyRule:
    code: str
    minor_units: int
    tolerance: Decimal


@dataclass(frozen=True)
class Rules:
    version: str
    currencies: dict
    amount_max: Decimal
    payment_statuses: tuple
    name_similarity_threshold: Decimal
    reference_similarity_threshold: Decimal
    max_suggestions_per_record: int
    legal_suffixes: tuple

    def tolerance(self, currency: str) -> Decimal:
        return self.currencies[currency].tolerance


def _decimal(value, what: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise InputError(f"rules: {what} is not a decimal: {value!r}") from exc
    if not result.is_finite():
        raise InputError(f"rules: {what} must be finite")
    return result


def load_rules(path: str | Path | None = None) -> Rules:
    """Load and validate the reconciliation rules (tolerances, currencies, thresholds)."""
    if path is None:
        text = resources.files("invoice_recon").joinpath("data/reconciliation_rules.json").read_text(encoding="utf-8")
    else:
        text = Path(path).read_text(encoding="utf-8")
    try:
        raw = json.loads(text)
    except json.JSONDecodeError as exc:
        raise InputError(f"rules: invalid JSON: {exc}") from exc
    currencies = {}
    for code, spec in sorted(raw.get("currencies", {}).items()):
        if not _CURRENCY.match(code):
            raise InputError(f"rules: invalid currency code {code!r}")
        minor = spec.get("minor_units")
        if not isinstance(minor, int) or not 0 <= minor <= 4:
            raise InputError(f"rules: {code} minor_units must be an integer 0-4")
        tolerance = _decimal(spec.get("tolerance"), f"{code} tolerance")
        if tolerance < 0 or tolerance.as_tuple().exponent < -4:
            raise InputError(f"rules: {code} tolerance must be >= 0 with at most 4 decimals")
        currencies[code] = CurrencyRule(code, minor, tolerance)
    if not currencies:
        raise InputError("rules: at least one currency is required")
    fuzzy = raw.get("fuzzy", {})
    rules = Rules(
        version=str(raw.get("rules_version", "")),
        currencies=currencies,
        amount_max=_decimal(raw.get("amount_max"), "amount_max"),
        payment_statuses=tuple(raw.get("payment_statuses", ())),
        name_similarity_threshold=_decimal(fuzzy.get("name_similarity_threshold"), "name_similarity_threshold"),
        reference_similarity_threshold=_decimal(fuzzy.get("reference_similarity_threshold"), "reference_similarity_threshold"),
        max_suggestions_per_record=int(fuzzy.get("max_suggestions_per_record", 3)),
        legal_suffixes=tuple(raw.get("legal_suffixes", ())),
    )
    if not rules.version:
        raise InputError("rules: rules_version is required")
    if rules.amount_max <= 0:
        raise InputError("rules: amount_max must be positive")
    for name in ("name_similarity_threshold", "reference_similarity_threshold"):
        if not Decimal(0) < getattr(rules, name) <= Decimal(1):
            raise InputError(f"rules: {name} must be in (0, 1]")
    if rules.max_suggestions_per_record < 1:
        raise InputError("rules: max_suggestions_per_record must be >= 1")
    return rules


@dataclass(frozen=True)
class Lakehouse:
    """Lakehouse layout: Files/ for landing files and reports, Tables/ for Delta tables.

    ``root`` is an absolute local directory for local runs. In a Fabric notebook it can be
    "" so that paths resolve as ``Files/...`` and ``Tables/...`` against the default
    lakehouse (not tested in Fabric; see docs/fabric.md).
    """

    root: str

    @classmethod
    def local(cls, directory: str | Path) -> "Lakehouse":
        return cls(Path(directory).resolve().as_posix())

    def path(self, *parts: str) -> str:
        base = self.root.rstrip("/")
        return "/".join(([base] if base else []) + list(parts))

    def landing_root(self) -> str:
        return self.path("Files", "landing")

    def landing(self, batch_id: str) -> str:
        return self.path("Files", "landing", validate_batch_id(batch_id))

    def ground_truth(self, batch_id: str) -> str:
        return self.path("Files", "synthetic_ground_truth", validate_batch_id(batch_id))

    def reports(self, batch_id: str) -> str:
        return self.path("Files", "reports", validate_batch_id(batch_id))

    def table(self, name: str) -> str:
        if name not in TABLES:
            raise KeyError(name)
        return self.path("Tables", TABLES[name])

    @staticmethod
    def relative_landing_file(batch_id: str, file_name: str) -> str:
        """Location recorded in Bronze lineage columns: portable, independent of the root."""
        return f"Files/landing/{validate_batch_id(batch_id)}/{file_name}"
