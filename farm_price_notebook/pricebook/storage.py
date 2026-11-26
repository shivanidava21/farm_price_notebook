"""JSON persistence with corruption recovery and atomic writes."""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

from .validation import PriceRecord, ValidationError, validate_entry

SCHEMA = "farm-price-notebook/v1"


class Store:
    def __init__(self, path: str | Path = "data/prices.json"):
        self.path = Path(path)
        self.records: list[PriceRecord] = []
        self.recovery_note = ""
        self._load()

    # ---- persistence -------------------------------------------------
    def _load(self) -> None:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if data.get("schema") != SCHEMA:
                raise ValueError("unknown schema")
            self.records = [PriceRecord(**r) for r in data["records"]]
        except FileNotFoundError:
            self.records = []
            self.save()
        except (ValueError, KeyError, TypeError, AttributeError):  # JSONDecodeError is a ValueError
            backup = self.path.with_name(f"{self.path.stem}.corrupt-{int(time.time())}.json")
            self.path.replace(backup)
            self.records = []
            self.recovery_note = f"Data file was unreadable. It was saved as '{backup.name}' and a fresh notebook was created."
            self.save()

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        payload = {"schema": SCHEMA, "records": [r.to_dict() for r in self.records]}
        tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, self.path)  # atomic: never leaves a half-written file

    # ---- operations --------------------------------------------------
    def add(self, raw: dict, save: bool = True) -> PriceRecord:
        clean = validate_entry(raw)
        if any((r.date, r.produce, r.market) == (clean["date"], clean["produce"], clean["market"]) for r in self.records):
            raise ValidationError([f"Duplicate: {clean['produce']} at {clean['market']} on {clean['date']} already exists."])
        rec = PriceRecord(id=max((r.id for r in self.records), default=0) + 1, **clean)
        self.records.append(rec)
        if save:
            self.save()
        return rec

    def delete(self, record_id: int) -> bool:
        before = len(self.records)
        self.records = [r for r in self.records if r.id != record_id]
        if len(self.records) != before:
            self.save()
            return True
        return False

    def search(self, keyword: str = "", categories=None, produce=None, start=None, end=None) -> list[PriceRecord]:
        kw = keyword.strip().lower()
        out = []
        for r in self.records:
            if kw and kw not in f"{r.produce} {r.market} {r.category} {r.notes}".lower():
                continue
            if categories and r.category not in categories:
                continue
            if produce and r.produce not in produce:
                continue
            if start and r.date < start:
                continue
            if end and r.date > end:
                continue
            out.append(r)
        return sorted(out, key=lambda r: (r.date, r.produce), reverse=True)
