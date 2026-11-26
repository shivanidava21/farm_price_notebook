"""Bulk CSV import with a row-by-row error log."""
from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field

from .validation import ValidationError

REQUIRED = {"date", "produce", "category", "market", "price"}


@dataclass
class ImportResult:
    imported: int = 0
    errors: list = field(default_factory=list)  # (row_number, message)

    def error_log(self) -> str:
        return "\n".join(f"Row {n}: {m}" for n, m in self.errors) or "No errors."


def import_csv(text: str, store) -> ImportResult:
    res = ImportResult()
    reader = csv.DictReader(io.StringIO(text.lstrip("\ufeff")))
    if not reader.fieldnames:
        res.errors.append((1, "File is empty."))
        return res
    missing = REQUIRED - {c.strip().lower() for c in reader.fieldnames if c}
    if missing:
        res.errors.append((1, f"Missing required column(s): {', '.join(sorted(missing))}"))
        return res
    for n, row in enumerate(reader, start=2):
        row = {(k or "").strip().lower(): v for k, v in row.items()}
        try:
            store.add(row, save=False)
            res.imported += 1
        except ValidationError as e:
            res.errors.append((n, "; ".join(e.errors)))
    if res.imported:
        store.save()
    return res
