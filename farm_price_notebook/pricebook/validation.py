"""Record model + defensive input validation (UI-independent)."""
from __future__ import annotations

import math
import re
from dataclasses import asdict, dataclass
from datetime import date, datetime

CATEGORIES = ["Vegetable", "Fruit", "Grain", "Pulse", "Spice", "Dairy", "Other"]
MIN_PRICE, MAX_PRICE = 0.5, 5000.0  # INR per kg
FIELDS = ["id", "date", "produce", "category", "market", "price", "notes"]
_NAME_RE = re.compile(r"^[A-Za-z][A-Za-z .'\-]{1,39}$")
_MARKET_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 .,'\-]{1,59}$")


class ValidationError(ValueError):
    def __init__(self, errors):
        self.errors = list(errors)
        super().__init__("; ".join(self.errors))


@dataclass
class PriceRecord:
    id: int
    date: str
    produce: str
    category: str
    market: str
    price: float
    notes: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def parse_date(value) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return datetime.strptime(str(value).strip(), "%Y-%m-%d").date()


def parse_price(value) -> float:
    if isinstance(value, (int, float)):
        p = float(value)
    else:
        s = re.sub(r"₹|,|\s|rs\.?", "", str(value), flags=re.I)
        if not s:
            raise ValueError("blank")
        p = float(s)
    if math.isnan(p) or math.isinf(p):
        raise ValueError("not finite")
    return p


def validate_entry(raw: dict) -> dict:
    """Return a cleaned dict (no id) or raise ValidationError listing ALL problems."""
    errors, out = [], {}

    try:
        d = parse_date(raw.get("date", ""))
        if d > date.today():
            errors.append("Date cannot be in the future.")
        elif d.year < 2000:
            errors.append("Date cannot be before the year 2000.")
        else:
            out["date"] = d.isoformat()
    except (ValueError, TypeError):
        errors.append("Date must be a valid date in YYYY-MM-DD format.")

    produce = " ".join(str(raw.get("produce") or "").split())
    if not _NAME_RE.match(produce):
        errors.append("Produce name must be 2-40 characters, letters only (e.g. 'Tomato').")
    else:
        out["produce"] = produce.title()

    category = str(raw.get("category") or "").strip().title()
    if category not in CATEGORIES:
        errors.append(f"Category must be one of: {', '.join(CATEGORIES)}.")
    else:
        out["category"] = category

    market = " ".join(str(raw.get("market") or "").split())
    if not _MARKET_RE.match(market):
        errors.append("Market name must be 2-60 characters (letters, digits, spaces).")
    else:
        out["market"] = market

    try:
        p = parse_price(raw.get("price", ""))
        if not (MIN_PRICE <= p <= MAX_PRICE):
            errors.append(f"Price must be between ₹{MIN_PRICE} and ₹{MAX_PRICE:,.0f} per kg.")
        else:
            out["price"] = round(p, 2)
    except (ValueError, TypeError):
        errors.append("Price must be a number (e.g. 42.50).")

    notes = raw.get("notes")
    out["notes"] = "" if notes is None or (isinstance(notes, float) and math.isnan(notes)) else str(notes).strip()[:200]

    if errors:
        raise ValidationError(errors)
    return out
