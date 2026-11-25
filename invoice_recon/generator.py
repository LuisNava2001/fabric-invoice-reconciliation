"""Deterministic synthetic sources for the reconciliation pipeline.

Company names are composed from invented word stems; identifiers, amounts and dates come
from a seeded ``random.Random``. Besides the two source files, the generator writes the
outcome each record was designed to produce (synthetic ground truth). Tests compare the
pipeline against it; the pipeline itself never reads it.

This module is plain Python on purpose: it fabricates small landing files, it is not part
of the Spark processing.
"""

from __future__ import annotations

import calendar
import csv
import io
import json
import random
import re
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from .config import (
    GROUND_TRUTH_FILE,
    GROUND_TRUTH_SUGGESTIONS_FILE,
    INVOICE_COLUMNS,
    INVOICE_FILE,
    LEDGER_COLUMNS,
    LEDGER_FILE,
    MANIFEST_FILE,
    SIDE_INVOICE,
    SIDE_LEDGER,
    SOURCE_INVOICES,
    SOURCE_LEDGER,
    InputError,
    load_rules,
    shift_period,
    validate_period,
)

GENERATOR_VERSION = "1"
DEFAULT_SEED = 4242
DEFAULT_BATCHES = 2
DEFAULT_INVOICES = 5000
DEFAULT_START_PERIOD = "2026-03"
MIN_INVOICES = 100
MAX_INVOICES = 200_000
MAX_BATCHES = 12

NAME_STEMS = (
    "Amberlyn", "Brindlecove", "Corvantis", "Delmora", "Fenlowe", "Gristmere", "Halvorne", "Istrella",
    "Jorvale", "Kestwick", "Lumbrel", "Marrowind", "Nimbrel", "Ostravale", "Penwhistle", "Quillbrook",
    "Rosmerin", "Sablecrest", "Tavernell", "Umbervale", "Vexmoor", "Wrenfold", "Yarrowby", "Zelmont",
)
SECTORS = (
    "Fasteners", "Packaging", "Coatings", "Tooling", "Castings", "Polymers", "Electrical", "Logistics",
    "Fixtures", "Office Supplies",
)
# Sector spellings for "similar name, different company" pairs.
SIBLING_SECTOR = {
    "Fasteners": "Fastening", "Packaging": "Packagers", "Coatings": "Coating", "Castings": "Casting",
    "Polymers": "Polymer", "Fixtures": "Fixture", "Logistics": "Logistic", "Electrical": "Electric",
}
SUFFIXES = ("Ltd", "LLC", "Inc", "Co")
CURRENCY_WEIGHTS = (("USD", 55), ("EUR", 20), ("MXN", 15), ("CAD", 7), ("JPY", 3))
TAX_RATES = ("0", "0.05", "0.08", "0.16", "0.20")
PAYMENT_STATUSES = ("OPEN", "PAID", "PARTIALLY_PAID")
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
INVALID_CURRENCIES = ("US$", "XYZ", "EURO", "MX")

# (scenario, share of base invoices). Everything not listed here is a clean match.
SCENARIOS = (
    ("reference_variant", 0.06),
    ("rounding", 0.03),
    ("amount_mismatch", 0.03),
    ("currency_mismatch", 0.015),
    ("only_invoice", 0.03),
    ("invoice_exact_duplicate", 0.01),
    ("invoice_conflicting_duplicate", 0.005),
    ("ledger_exact_duplicate", 0.01),
    ("multiple_ledger_candidates", 0.01),
    ("multiple_invoice_candidates", 0.005),
    ("null_invoice_id", 0.004),
    ("null_transaction_id", 0.004),
    ("missing_reference_invoice", 0.004),
    ("missing_reference_ledger", 0.004),
    ("invalid_invoice_date", 0.004),
    ("invalid_posting_date", 0.004),
    ("ambiguous_posting_date", 0.03),
    ("null_amount", 0.004),
    ("non_numeric_amount", 0.004),
    ("negative_invoice_amount", 0.003),
    ("excessive_ledger_amount", 0.003),
    ("inconsistent_totals", 0.005),
    ("invalid_currency", 0.003),
    ("out_of_period", 0.01),
    ("period_inconsistent", 0.005),
    ("invalid_accounting_period", 0.003),
    ("similar_supplier_wrong_id", 0.005),
    ("unnormalizable_reference", 0.005),
    ("malformed_invoice_row", 0.002),
    ("malformed_ledger_row", 0.002),
)
ONLY_LEDGER_SHARE = 0.03
SCENARIO_NAMES = tuple(name for name, _ in SCENARIOS) + ("clean", "only_ledger")


class JsonNumber(str):
    """Amount text written as a bare JSON number instead of a JSON string."""


@dataclass
class Supplier:
    supplier_id: str
    name: str
    stem: str
    sector: str
    prefix: str
    currency: str
    next_number: int
    sibling: "Supplier | None" = None

    def next_reference(self, rng: random.Random) -> str:
        self.next_number += rng.randint(1, 7)
        return f"{self.prefix}-{self.next_number:06d}"


@dataclass
class Invoice:
    values: dict
    supplier: Supplier
    when: date
    total: Decimal


@dataclass
class Record:
    side: str
    values: dict
    scenario: str
    status: str
    reason: str | None = None
    flags: tuple = ()
    review: bool = True
    raw: str | None = None
    dup_group: str | None = None
    link: str | None = None
    criterion: str | None = None
    line: int = 0


@dataclass
class BatchSummary:
    batch_id: str
    period: str
    invoice_rows: int
    ledger_rows: int
    scenarios: dict = field(default_factory=dict)


def name_key(name: str, suffixes: tuple) -> str:
    """Python mirror of the Spark supplier-name normalization used for suggestions."""
    tokens = re.sub(r"[^A-Z0-9 ]", " ", name.upper()).split()
    return " ".join(token for token in tokens if token not in suffixes)


def levenshtein(a: str, b: str) -> int:
    previous = list(range(len(b) + 1))
    for i, char_a in enumerate(a, start=1):
        current = [i]
        for j, char_b in enumerate(b, start=1):
            current.append(min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + (char_a != char_b)))
        previous = current
    return previous[-1]


def similarity(a: str, b: str) -> Decimal:
    longest = max(len(a), len(b))
    if not longest:
        return Decimal(0)
    return (Decimal(1) - Decimal(levenshtein(a, b)) / Decimal(longest)).quantize(Decimal("0.001"), ROUND_HALF_UP)


def _unit(currency: str) -> Decimal:
    return Decimal(1) if currency == "JPY" else Decimal("0.01")


def _money(value: Decimal, currency: str) -> str:
    return str(value.quantize(_unit(currency), ROUND_HALF_UP))


def _bounds(period: str) -> tuple[date, date]:
    year, month = (int(part) for part in period.split("-"))
    return date(year, month, 1), date(year, month, calendar.monthrange(year, month)[1])


def _period_of(day: date) -> str:
    return f"{day.year:04d}-{day.month:02d}"


def _weighted_currency(rng: random.Random) -> str:
    codes, weights = zip(*CURRENCY_WEIGHTS)
    return rng.choices(codes, weights=weights, k=1)[0]


def make_suppliers(rng: random.Random, count: int = 40, siblings: int = 6) -> list[Supplier]:
    rules = load_rules()
    combos = [(stem, sector) for stem in NAME_STEMS for sector in SECTORS]
    rng.shuffle(combos)
    chosen = combos[:count]
    taken = set(chosen)
    used_prefixes: set[str] = set()
    suppliers: list[Supplier] = []

    def new_supplier(stem: str, sector: str, currency: str) -> Supplier:
        index = len(suppliers) + 1
        suffix = rng.choice(SUFFIXES)
        name = f"{stem} {sector}, {suffix}" if rng.random() < 0.15 else f"{stem} {sector} {suffix}"
        prefix = next(
            (p for p in (stem[:2] + sector[0], stem[0] + stem[2] + sector[0], stem[:3], stem[0] + sector[:2])
             if p.upper() not in used_prefixes),
            f"S{index:02d}",
        ).upper()
        used_prefixes.add(prefix)
        supplier = Supplier(f"SUP-{index:04d}", name, stem, sector, prefix, currency, rng.randint(1000, 40000))
        suppliers.append(supplier)
        return supplier

    for stem, sector in chosen:
        new_supplier(stem, sector, _weighted_currency(rng))
    made = 0
    for base in list(suppliers):
        variant = SIBLING_SECTOR.get(base.sector)
        if made >= siblings or variant is None or (base.stem, variant) in taken:
            continue
        sibling = new_supplier(base.stem, variant, base.currency)
        score = similarity(name_key(base.name, rules.legal_suffixes), name_key(sibling.name, rules.legal_suffixes))
        if score < rules.name_similarity_threshold:
            raise AssertionError(f"sibling names too different: {base.name!r} / {sibling.name!r} ({score})")
        base.sibling = sibling
        taken.add((base.stem, variant))
        made += 1
    if made == 0:
        raise AssertionError("no similar-name supplier pairs were generated")
    return suppliers


class _Batch:
    def __init__(self, rng: random.Random, suppliers: list[Supplier], period: str):
        self.rng = rng
        self.suppliers = suppliers
        self.with_sibling = [s for s in suppliers if s.sibling is not None]
        self.period = period
        self.previous = shift_period(period, -1)
        self.yyyymm = period.replace("-", "")
        self.inv_seq = 0
        self.tx_seq = 0

    # -- building blocks -------------------------------------------------------------------
    def amounts(self, currency: str) -> tuple[Decimal, Decimal, Decimal]:
        if currency == "JPY":
            subtotal = Decimal(self.rng.randint(5_000, 2_500_000))
        else:
            subtotal = Decimal(self.rng.randint(5_000, 2_500_000)) / 100
        tax = (subtotal * Decimal(self.rng.choice(TAX_RATES))).quantize(_unit(currency), ROUND_HALF_UP)
        return subtotal, tax, subtotal + tax

    def invoice(self, supplier: Supplier | None = None, when: date | None = None, period: str | None = None) -> Invoice:
        supplier = supplier or self.rng.choice(self.suppliers)
        first, last = _bounds(period or self.period)
        when = when or first + timedelta(days=self.rng.randint(0, (last - first).days))
        subtotal, tax, total = self.amounts(supplier.currency)
        self.inv_seq += 1
        currency = supplier.currency
        values = {
            "invoice_id": f"EI-{self.yyyymm}-{self.inv_seq:05d}",
            "supplier_id": supplier.supplier_id,
            "supplier_name": supplier.name,
            "invoice_date": when.isoformat(),
            "currency": currency,
            "subtotal": _money(subtotal, currency),
            "tax_amount": _money(tax, currency),
            "total_amount": _money(total, currency),
            "invoice_reference": supplier.next_reference(self.rng),
        }
        return Invoice(values, supplier, when, total)

    def posting_text(self, day: date) -> str:
        roll = self.rng.random()
        if roll < 0.70:
            return day.isoformat()
        if roll < 0.80:
            return day.strftime("%Y/%m/%d")
        if roll < 0.90:
            month = MONTHS[day.month - 1]
            return f"{day.day:02d}-{month.upper() if self.rng.random() < 0.3 else month}-{day.year}"
        if day.day > 12 or day.day == day.month:  # only unambiguous day/month readings here
            return f"{day.day:02d}/{day.month:02d}/{day.year}"
        return day.isoformat()

    def amount_text(self, value: Decimal, currency: str):
        text = _money(value, currency)
        roll = self.rng.random()
        if roll < 0.10:
            return JsonNumber(text)
        if roll < 0.20 and abs(value) >= 1000:
            return f"{Decimal(text):,}"
        return text

    def ledger(self, inv: Invoice, posting: date | None = None, period: str | None = None) -> dict:
        _, last = _bounds(_period_of(inv.when))
        posting = posting or min(inv.when + timedelta(days=self.rng.randint(0, 6)), last)
        self.tx_seq += 1
        accounting = period or _period_of(posting)
        return {
            "transaction_id": f"GL-{self.yyyymm}-{self.tx_seq:06d}",
            "invoice_reference": inv.values["invoice_reference"],
            "supplier_id": inv.supplier.supplier_id,
            "supplier_name": inv.supplier.name,
            "posting_date": self.posting_text(posting),
            "currency": inv.supplier.currency,
            "recorded_amount": self.amount_text(inv.total, inv.supplier.currency),
            "payment_status": self.rng.choice(PAYMENT_STATUSES),
            "accounting_period": accounting.replace("-", "") if self.rng.random() < 0.10 else accounting,
        }

    def add_noise(self, inv: dict, led: dict) -> None:
        """Formatting noise that normalization must absorb without changing the outcome."""
        sid = led["supplier_id"]
        choice = self.rng.randrange(6)
        if choice == 0:
            led["supplier_id"] = self.rng.choice((sid.lower(), sid.replace("-", ""), f" {sid} ", sid + " "))
        elif choice == 1:
            led["currency"] = self.rng.choice((led["currency"].lower(), f" {led['currency']}", f"{led['currency']} "))
        elif choice == 2:
            inv["invoice_id"] = inv["invoice_id"].lower()
        elif choice == 3:
            inv["supplier_name"] = inv["supplier_name"].replace(" ", "  ", 1)
        elif choice == 4:
            led["payment_status"] = led["payment_status"].lower()
        else:
            led["invoice_reference"] = f" {led['invoice_reference']} "

    def reference_variant(self, reference: str) -> str:
        prefix, number = reference.split("-")
        return self.rng.choice((
            reference.lower(), prefix + number, f"{prefix}/{number}", f"{prefix} {number}",
            f"{prefix}.{number}", f"{prefix}_{number}", f"{prefix.lower()}-{number}",
        ))

    # -- scenarios --------------------------------------------------------------------------
    def case(self, scenario: str, index: int) -> list[Record]:
        rng = self.rng
        inv_side, led_side = SIDE_INVOICE, SIDE_LEDGER

        def rec(side, values, status, reason=None, flags=(), review=True, **extra):
            return Record(side, values, scenario, status, reason, tuple(flags), review, **extra)

        if scenario == "only_ledger":
            supplier = rng.choice(self.suppliers)
            _, _, total = self.amounts(supplier.currency)
            first, last = _bounds(self.period)
            ghost = Invoice({"invoice_reference": supplier.next_reference(rng)}, supplier,
                            first + timedelta(days=rng.randint(0, (last - first).days)), total)
            return [rec(led_side, self.ledger(ghost), "ONLY_IN_LEDGER", "NO_COUNTERPART")]

        ambiguous = None
        if scenario == "out_of_period":
            first, last = _bounds(self.previous)
            inv = self.invoice(period=self.previous, when=last - timedelta(days=rng.randint(0, 9)))
        elif scenario == "ambiguous_posting_date":
            first, _ = _bounds(self.period)
            day = rng.choice([d for d in range(1, 13) if d != first.month])
            ambiguous = first.replace(day=day)
            inv = self.invoice(when=ambiguous - timedelta(days=rng.randint(0, min(3, day - 1))))
        elif scenario == "similar_supplier_wrong_id":
            inv = self.invoice(supplier=rng.choice(self.with_sibling))
        else:
            inv = self.invoice()
        v, cur, unit = inv.values, inv.supplier.currency, _unit(inv.supplier.currency)
        matched = dict(reason="EXACT_AMOUNT", review=False)

        if scenario == "clean":
            led = self.ledger(inv)
            if rng.random() < 0.3:
                self.add_noise(v, led)
            return [rec(inv_side, v, "MATCHED", **matched), rec(led_side, led, "MATCHED", **matched)]
        if scenario == "reference_variant":
            led = self.ledger(inv)
            led["invoice_reference"] = self.reference_variant(v["invoice_reference"])
            flags = ("REFERENCE_FORMAT_VARIANT",)
            return [rec(inv_side, v, "MATCHED", flags=flags, **matched), rec(led_side, led, "MATCHED", flags=flags, **matched)]
        if scenario == "rounding":
            led = self.ledger(inv)
            led["recorded_amount"] = _money(inv.total + rng.choice((unit, -unit)), cur)
            kw = dict(reason="WITHIN_TOLERANCE", flags=("ROUNDING_DIFFERENCE",), review=False)
            return [rec(inv_side, v, "MATCHED", **kw), rec(led_side, led, "MATCHED", **kw)]
        if scenario == "amount_mismatch":
            led = self.ledger(inv)
            delta = max(2 * unit, (inv.total * Decimal(rng.choice(("0.05", "0.10", "0.25")))).quantize(unit))
            led["recorded_amount"] = _money(inv.total + rng.choice((delta, -delta)), cur)
            return [rec(inv_side, v, "AMOUNT_MISMATCH", "DIFFERENCE_ABOVE_TOLERANCE"),
                    rec(led_side, led, "AMOUNT_MISMATCH", "DIFFERENCE_ABOVE_TOLERANCE")]
        if scenario == "currency_mismatch":
            led = self.ledger(inv)
            other = rng.choice([code for code, _ in CURRENCY_WEIGHTS if code != cur])
            led["currency"], led["recorded_amount"] = other, _money(inv.total, other)
            return [rec(inv_side, v, "CURRENCY_MISMATCH", "CURRENCY_DIFFERS_NO_CONVERSION"),
                    rec(led_side, led, "CURRENCY_MISMATCH", "CURRENCY_DIFFERS_NO_CONVERSION")]
        if scenario == "only_invoice":
            return [rec(inv_side, v, "ONLY_IN_INVOICES", "NO_COUNTERPART")]
        if scenario == "invoice_exact_duplicate":
            copy = dict(v)
            copy["supplier_name"] = copy["supplier_name"].replace(" ", " ", 1)
            group = f"inv-dup-{index}"
            return [rec(inv_side, v, "MATCHED", dup_group=group, **matched),
                    rec(inv_side, copy, "MATCHED", dup_group=group, **matched),
                    rec(led_side, self.ledger(inv), "MATCHED", **matched)]
        if scenario == "invoice_conflicting_duplicate":
            subtotal, tax, total = self.amounts(cur)
            copy = dict(v, subtotal=_money(subtotal, cur), tax_amount=_money(tax, cur), total_amount=_money(total, cur))
            return [rec(inv_side, v, "DUPLICATE", "DUPLICATE_CONFLICT"),
                    rec(inv_side, copy, "DUPLICATE", "DUPLICATE_CONFLICT"),
                    rec(led_side, self.ledger(inv), "ONLY_IN_LEDGER", "COUNTERPART_NOT_ELIGIBLE")]
        if scenario == "ledger_exact_duplicate":
            led = self.ledger(inv)
            group = f"led-dup-{index}"
            return [rec(inv_side, v, "MATCHED", **matched),
                    rec(led_side, led, "MATCHED", dup_group=group, **matched),
                    rec(led_side, dict(led), "MATCHED", dup_group=group, **matched)]
        if scenario == "multiple_ledger_candidates":
            reason = "MULTIPLE_LEDGER_ENTRIES_FOR_KEY"
            return [rec(inv_side, v, "AMBIGUOUS", reason), rec(led_side, self.ledger(inv), "AMBIGUOUS", reason),
                    rec(led_side, self.ledger(inv), "AMBIGUOUS", reason)]
        if scenario == "multiple_invoice_candidates":
            second = self.invoice(supplier=inv.supplier)
            second.values["invoice_reference"] = v["invoice_reference"]
            reason = "MULTIPLE_INVOICES_FOR_KEY"
            return [rec(inv_side, v, "AMBIGUOUS", reason), rec(inv_side, second.values, "AMBIGUOUS", reason),
                    rec(led_side, self.ledger(inv), "AMBIGUOUS", reason)]

        not_eligible = ("ONLY_IN_LEDGER", "COUNTERPART_NOT_ELIGIBLE")
        if scenario == "null_invoice_id":
            v["invoice_id"] = ""
            return [rec(inv_side, v, "INVALID_RECORD", "MISSING_INVOICE_ID"), rec(led_side, self.ledger(inv), *not_eligible)]
        if scenario == "missing_reference_invoice":
            led = self.ledger(inv)
            v["invoice_reference"] = rng.choice(("", "   "))
            return [rec(inv_side, v, "INVALID_RECORD", "MISSING_REFERENCE"), rec(led_side, led, "ONLY_IN_LEDGER", "NO_COUNTERPART")]
        if scenario == "invalid_invoice_date":
            year, month = inv.when.year, inv.when.month
            v["invoice_date"] = rng.choice((f"{year}-02-30", f"{year}-{month:02d}-32", f"{year}-13-{inv.when.day:02d}"))
            return [rec(inv_side, v, "INVALID_RECORD", "INVALID_DATE"), rec(led_side, self.ledger(inv), *not_eligible)]
        if scenario == "null_amount":
            v["total_amount"] = ""
            return [rec(inv_side, v, "INVALID_RECORD", "MISSING_AMOUNT"), rec(led_side, self.ledger(inv), *not_eligible)]
        if scenario == "negative_invoice_amount":
            for column in ("subtotal", "tax_amount", "total_amount"):
                v[column] = _money(-Decimal(v[column]), cur)
            return [rec(inv_side, v, "INVALID_RECORD", "AMOUNT_OUT_OF_RANGE")]
        if scenario == "inconsistent_totals":
            wrong = inv.total + 500 * unit
            v["total_amount"] = _money(wrong, cur)
            led = self.ledger(inv)
            led["recorded_amount"] = _money(wrong, cur)
            return [rec(inv_side, v, "INVALID_RECORD", "TOTAL_INCONSISTENT"), rec(led_side, led, *not_eligible)]
        if scenario == "invalid_currency":
            led = self.ledger(inv)
            v["currency"] = rng.choice(INVALID_CURRENCIES)
            return [rec(inv_side, v, "INVALID_RECORD", "INVALID_CURRENCY"), rec(led_side, led, *not_eligible)]
        if scenario == "malformed_invoice_row":
            cells = [v[c] for c in INVOICE_COLUMNS if c != "tax_amount"]
            return [rec(inv_side, v, "INVALID_RECORD", "MALFORMED_ROW", raw=_csv_line(cells)),
                    rec(led_side, self.ledger(inv), "ONLY_IN_LEDGER", "NO_COUNTERPART")]

        only_invoice_not_eligible = ("ONLY_IN_INVOICES", "COUNTERPART_NOT_ELIGIBLE")
        led = self.ledger(inv)
        if scenario == "null_transaction_id":
            led["transaction_id"] = rng.choice((None, ""))
            return [rec(inv_side, v, *only_invoice_not_eligible), rec(led_side, led, "INVALID_RECORD", "MISSING_TRANSACTION_ID")]
        if scenario == "missing_reference_ledger":
            led["invoice_reference"] = None
            return [rec(inv_side, v, "ONLY_IN_INVOICES", "NO_COUNTERPART"), rec(led_side, led, "INVALID_RECORD", "MISSING_REFERENCE")]
        if scenario == "invalid_posting_date":
            led["posting_date"] = rng.choice((f"31/02/{inv.when.year}", f"{inv.when.year}-02-30", "2026-99-01"))
            return [rec(inv_side, v, *only_invoice_not_eligible), rec(led_side, led, "INVALID_RECORD", "INVALID_DATE")]
        if scenario == "ambiguous_posting_date":
            # DD/MM/YYYY where the MM/DD reading is also a valid date: the pipeline must not pick one.
            led["posting_date"] = f"{ambiguous.day:02d}/{ambiguous.month:02d}/{ambiguous.year}"
            flags = ("AMBIGUOUS_DATE",)
            return [rec(inv_side, v, "MATCHED", "EXACT_AMOUNT", flags), rec(led_side, led, "MATCHED", "EXACT_AMOUNT", flags)]
        if scenario == "non_numeric_amount":
            text = _money(inv.total, cur)
            led["recorded_amount"] = text.replace("0", "O", 1) if "0" in text else text[0] + "O" + text[1:]
            return [rec(inv_side, v, *only_invoice_not_eligible), rec(led_side, led, "INVALID_RECORD", "INVALID_AMOUNT")]
        if scenario == "excessive_ledger_amount":
            led["recorded_amount"] = _money(Decimal("250000000"), cur)
            return [rec(inv_side, v, *only_invoice_not_eligible), rec(led_side, led, "INVALID_RECORD", "AMOUNT_OUT_OF_RANGE")]
        if scenario == "out_of_period":
            flags = ("OUT_OF_PERIOD",)
            return [rec(inv_side, v, "MATCHED", "EXACT_AMOUNT", flags), rec(led_side, led, "MATCHED", "EXACT_AMOUNT", flags)]
        if scenario == "period_inconsistent":
            led["accounting_period"] = self.previous
            flags = ("PERIOD_INCONSISTENT", "OUT_OF_PERIOD")
            return [rec(inv_side, v, "MATCHED", "EXACT_AMOUNT", flags), rec(led_side, led, "MATCHED", "EXACT_AMOUNT", flags)]
        if scenario == "invalid_accounting_period":
            led["accounting_period"] = rng.choice((f"{inv.when.year}-13", f"{inv.when.year}-00", f"{inv.when.year}/03"))
            return [rec(inv_side, v, *only_invoice_not_eligible), rec(led_side, led, "INVALID_RECORD", "INVALID_PERIOD")]
        if scenario == "similar_supplier_wrong_id":
            sibling = inv.supplier.sibling
            led["supplier_id"], led["supplier_name"] = sibling.supplier_id, sibling.name
            link = f"sugg-{index}"
            criterion = "SAME_REFERENCE_DIFFERENT_SUPPLIER"
            return [rec(inv_side, v, "ONLY_IN_INVOICES", "NO_COUNTERPART", link=link, criterion=criterion),
                    rec(led_side, led, "ONLY_IN_LEDGER", "NO_COUNTERPART", link=link, criterion=criterion)]
        if scenario == "unnormalizable_reference":
            prefix, number = v["invoice_reference"].split("-")
            led["invoice_reference"] = f"{prefix}-{int(number)}"
            led["recorded_amount"] = _money(inv.total, cur)
            link = f"sugg-{index}"
            criterion = "SAME_SUPPLIER_AMOUNT_SIMILAR_REFERENCE"
            return [rec(inv_side, v, "ONLY_IN_INVOICES", "NO_COUNTERPART", link=link, criterion=criterion),
                    rec(led_side, led, "ONLY_IN_LEDGER", "NO_COUNTERPART", link=link, criterion=criterion)]
        if scenario == "malformed_ledger_row":
            line = _json_line(led)
            if index % 2:
                raw = line[: int(len(line) * 0.6)]
            else:
                raw = _json_line({("amount" if k == "recorded_amount" else k): val for k, val in led.items()})
            return [rec(inv_side, v, "ONLY_IN_INVOICES", "NO_COUNTERPART"),
                    rec(led_side, led, "INVALID_RECORD", "MALFORMED_ROW", raw=raw)]
        raise ValueError(f"unknown scenario {scenario!r}")


def _csv_line(cells) -> str:
    buffer = io.StringIO()
    csv.writer(buffer, lineterminator="\n").writerow(["" if cell is None else cell for cell in cells])
    return buffer.getvalue().rstrip("\n")


def _json_line(values: dict) -> str:
    parts = []
    for key, value in values.items():
        rendered = str(value) if isinstance(value, JsonNumber) else json.dumps(value, ensure_ascii=False)
        parts.append(f"{json.dumps(key)}: {rendered}")
    return "{" + ", ".join(parts) + "}"


def scenario_counts(base_invoices: int, rng: random.Random | None = None) -> dict:
    """Records per scenario. With ``rng`` each share varies by up to +/-20 % so batches differ."""
    def scaled(share: float) -> int:
        factor = rng.uniform(0.8, 1.2) if rng else 1.0
        return max(1, round(base_invoices * share * factor))

    counts = {name: scaled(share) for name, share in SCENARIOS}
    counts["clean"] = base_invoices - sum(counts.values())
    counts["only_ledger"] = scaled(ONLY_LEDGER_SHARE)
    if counts["clean"] < base_invoices * 2 // 5:
        raise InputError(f"too few invoices ({base_invoices}) for the scenario mix; use at least {MIN_INVOICES}")
    return counts


def build_batch(rng: random.Random, suppliers: list[Supplier], period: str, base_invoices: int):
    batch = _Batch(rng, suppliers, period)
    counts = scenario_counts(base_invoices, rng)
    plan = [name for name in SCENARIO_NAMES for _ in range(counts[name])]
    rng.shuffle(plan)
    records: list[Record] = []
    for index, scenario in enumerate(plan):
        records.extend(batch.case(scenario, index))
    invoices = [r for r in records if r.side == SIDE_INVOICE]
    ledger = [r for r in records if r.side == SIDE_LEDGER]
    rng.shuffle(invoices)
    rng.shuffle(ledger)
    # The ledger file has no header: its first record also serves as the schema probe.
    first_ok = next(i for i, r in enumerate(ledger) if r.raw is None)
    ledger[0], ledger[first_ok] = ledger[first_ok], ledger[0]
    for line, record in enumerate(invoices, start=2):
        record.line = line
    for line, record in enumerate(ledger, start=1):
        record.line = line
    _resolve_duplicates(invoices + ledger)
    return invoices, ledger, counts


def _resolve_duplicates(records: list[Record]) -> None:
    """The earliest line of an exact-duplicate group survives; later copies are DUPLICATE."""
    groups: dict[str, list[Record]] = {}
    for record in records:
        if record.dup_group:
            groups.setdefault(record.dup_group, []).append(record)
    for members in groups.values():
        for copy in sorted(members, key=lambda r: r.line)[1:]:
            copy.status, copy.reason, copy.flags, copy.review = "DUPLICATE", "DUPLICATE_EXACT", (), True


def _expected_rows(invoices: list[Record], ledger: list[Record]):
    outcomes = [
        {
            "side": r.side, "line_number": r.line, "scenario": r.scenario, "expected_status": r.status,
            "expected_reason": r.reason, "expected_flags": sorted(r.flags), "expected_review": r.review,
        }
        for r in invoices + ledger
    ]
    links: dict[str, dict] = {}
    for r in invoices + ledger:
        if r.link:
            links.setdefault(r.link, {"criterion": r.criterion})[r.side] = r.line
    suggestions = [
        {"invoice_line": item[SIDE_INVOICE], "ledger_line": item[SIDE_LEDGER], "criterion": item["criterion"]}
        for item in links.values()
    ]
    outcomes.sort(key=lambda row: (row["side"], row["line_number"]))
    suggestions.sort(key=lambda row: row["invoice_line"])
    return outcomes, suggestions


def _write_text(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        handle.write("".join(line + "\n" for line in lines))


def generate(lakehouse_dir: str | Path, seed: int = DEFAULT_SEED, batches: int = DEFAULT_BATCHES,
             invoices: int = DEFAULT_INVOICES, start_period: str = DEFAULT_START_PERIOD,
             force: bool = False) -> list[BatchSummary]:
    """Write landing files and synthetic ground truth under ``<lakehouse_dir>/Files``."""
    if not MIN_INVOICES <= invoices <= MAX_INVOICES:
        raise InputError(f"--invoices must be between {MIN_INVOICES} and {MAX_INVOICES}")
    if not 1 <= batches <= MAX_BATCHES:
        raise InputError(f"--batches must be between 1 and {MAX_BATCHES}")
    validate_period(start_period)
    root = Path(lakehouse_dir)
    periods = [shift_period(start_period, i) for i in range(batches)]
    batch_ids = [f"batch-{period}" for period in periods]
    landing = root / "Files" / "landing"
    existing = [b for b in batch_ids if (landing / b / MANIFEST_FILE).exists()]
    if existing and not force:
        raise InputError(f"landing data already exists for {', '.join(existing)}; use --force to overwrite")

    suppliers = make_suppliers(random.Random(seed))
    summaries = []
    for index, (batch_id, period) in enumerate(zip(batch_ids, periods)):
        rng = random.Random(seed * 1000 + index + 1)
        inv_records, led_records, counts = build_batch(rng, suppliers, period, invoices)
        batch_dir = landing / batch_id
        header = ",".join(INVOICE_COLUMNS)
        _write_text(batch_dir / INVOICE_FILE,
                    [header] + [r.raw if r.raw is not None else _csv_line([r.values[c] for c in INVOICE_COLUMNS])
                                for r in inv_records])
        _write_text(batch_dir / LEDGER_FILE,
                    [r.raw if r.raw is not None else _json_line({c: r.values[c] for c in LEDGER_COLUMNS})
                     for r in led_records])
        manifest = {
            "batch_id": batch_id,
            "reconciliation_period": period,
            "sources": {SOURCE_INVOICES: INVOICE_FILE, SOURCE_LEDGER: LEDGER_FILE},
            "synthetic": True,
            "generator": {"name": "invoice_recon.generator", "version": GENERATOR_VERSION, "seed": seed,
                          "batch_index": index, "base_invoices": invoices},
        }
        _write_text(batch_dir / MANIFEST_FILE, [json.dumps(manifest, indent=2, sort_keys=True)])
        outcomes, suggestions = _expected_rows(inv_records, led_records)
        truth_dir = root / "Files" / "synthetic_ground_truth" / batch_id
        _write_text(truth_dir / GROUND_TRUTH_FILE, [json.dumps(row, sort_keys=True) for row in outcomes])
        _write_text(truth_dir / GROUND_TRUTH_SUGGESTIONS_FILE, [json.dumps(row, sort_keys=True) for row in suggestions])
        summaries.append(BatchSummary(batch_id, period, len(inv_records), len(led_records), counts))
    return summaries
