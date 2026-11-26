"""Generate 40 realistic sample records + an import file with deliberate errors.
Usage:  python -m pricebook.seed
"""
from __future__ import annotations

import random
from datetime import date, timedelta
from pathlib import Path

from .exporters import to_csv
from .storage import Store

ITEMS = [("Tomato", "Vegetable", 30), ("Onion", "Vegetable", 28), ("Potato", "Vegetable", 25),
         ("Banana", "Fruit", 55), ("Mango", "Fruit", 90), ("Rice", "Grain", 52),
         ("Toor Dal", "Pulse", 140), ("Green Chilli", "Spice", 60)]
MARKETS = ["Bowenpally Market", "Gaddiannaram Market"]


def build_rows(today: date | None = None):
    today, rng, rows = today or date.today(), random.Random(42), []
    for i, (name, cat, base) in enumerate(ITEMS):
        for w in range(5):
            price = base * (1 + 0.04 * w) * rng.uniform(0.95, 1.05)
            note = ""
            if name == "Tomato" and w == 3:
                price, note = base * 4.2, "Edge case: unusual spike"
            if name == "Onion" and w == 0:
                price, note = 0.5, "Edge case: minimum boundary"
            rows.append({"date": (today - timedelta(days=7 * (4 - w))).isoformat(), "produce": name,
                         "category": cat, "market": MARKETS[(i + w) % 2], "price": round(price, 2), "notes": note})
    return rows


def main(data_dir="data"):
    d = Path(data_dir)
    d.mkdir(exist_ok=True)
    rows = build_rows()
    sample = Path(d / "sample_prices.json")
    if sample.exists():
        sample.unlink()
    store = Store(sample)
    for r in rows:
        store.add(r, save=False)
    store.save()
    (d / "sample_prices.csv").write_text(to_csv(store.records), encoding="utf-8")
    t = date.today()
    bad = ["date,produce,category,market,price,notes",
           f"{t},Cabbage,Vegetable,Bowenpally Market,22,ok row",
           f"{t + timedelta(days=5)},Carrot,Vegetable,Bowenpally Market,40,future date",
           f"{t},Brinjal,Vegetable,Bowenpally Market,-5,negative price",
           f"{t},Apple,Gadget,Bowenpally Market,120,bad category",
           f"{t},,Fruit,Bowenpally Market,80,blank produce",
           f"{t},Garlic,Spice,Bowenpally Market,abc,non-numeric price",
           f"{t},Cabbage,Vegetable,Bowenpally Market,23,duplicate of first row"]
    (d / "sample_import_with_errors.csv").write_text("\n".join(bad) + "\n", encoding="utf-8")
    live = Store(d / "prices.json")
    if not live.records:
        for r in rows:
            live.add(r, save=False)
        live.save()
    print(f"Seeded {len(rows)} records into {d}/")


if __name__ == "__main__":
    main()
