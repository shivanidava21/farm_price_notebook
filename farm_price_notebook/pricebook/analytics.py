"""Summaries, trends, comparisons and threshold warnings (stdlib only)."""
from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
from statistics import mean, median


def daily_series(records, produce, market=None):
    buckets = defaultdict(list)
    for r in records:
        if r.produce == produce and (market is None or r.market == market):
            buckets[r.date].append(r.price)
    return [(d, round(mean(v), 2)) for d, v in sorted(buckets.items())]


def produce_stats(records, flat_band_pct: float = 5.0):
    groups = defaultdict(list)
    for r in records:
        groups[r.produce].append(r)
    rows = []
    for name, recs in sorted(groups.items()):
        series = daily_series(records, name)
        prices = [r.price for r in recs]
        first, last = series[0][1], series[-1][1]
        change = (last - first) / first * 100 if len(series) > 1 else 0.0
        trend = "Rising" if change > flat_band_pct else "Falling" if change < -flat_band_pct else "Stable"
        rows.append({
            "produce": name, "category": recs[0].category, "entries": len(recs),
            "avg": round(mean(prices), 2), "min": min(prices), "max": max(prices),
            "latest": last, "change_pct": round(change, 1), "trend": trend,
            "last_date": series[-1][0],
        })
    return rows


def summary(records):
    if not records:
        return {"entries": 0, "produce_count": 0, "markets": 0, "avg_price": 0.0,
                "highest": None, "lowest": None, "date_range": None}
    hi = max(records, key=lambda r: r.price)
    lo = min(records, key=lambda r: r.price)
    dates = sorted(r.date for r in records)
    return {
        "entries": len(records),
        "produce_count": len({r.produce for r in records}),
        "markets": len({r.market for r in records}),
        "avg_price": round(mean(r.price for r in records), 2),
        "highest": f"{hi.produce} ₹{hi.price} ({hi.market}, {hi.date})",
        "lowest": f"{lo.produce} ₹{lo.price} ({lo.market}, {lo.date})",
        "date_range": (dates[0], dates[-1]),
    }


def market_comparison(records, produce):
    buckets = defaultdict(list)
    for r in records:
        if r.produce == produce:
            buckets[r.market].append(r.price)
    return {m: round(mean(v), 2) for m, v in sorted(buckets.items())}


def warnings(records, spike_pct=25.0, outlier_pct=50.0, stale_days=30, today=None):
    """Threshold flags: sudden jumps, anomalous prices, stale produce."""
    today = today or date.today()
    flags = []
    by_pm, by_p = defaultdict(list), defaultdict(list)
    for r in sorted(records, key=lambda r: r.date):
        by_pm[(r.produce, r.market)].append(r)
        by_p[r.produce].append(r)

    for (prod, mkt), recs in by_pm.items():
        for prev, cur in zip(recs, recs[1:]):
            chg = (cur.price - prev.price) / prev.price * 100
            if abs(chg) >= spike_pct:
                flags.append({"level": "warning", "produce": prod,
                              "message": f"{prod} @ {mkt}: price moved {chg:+.0f}% (₹{prev.price} → ₹{cur.price}) on {cur.date}"})
    for prod, recs in by_p.items():
        if len(recs) < 5:
            continue
        med = median(r.price for r in recs)
        for r in recs:
            dev = (r.price - med) / med * 100
            if abs(dev) >= outlier_pct:
                flags.append({"level": "critical", "produce": prod,
                              "message": f"{prod} @ {r.market} on {r.date}: ₹{r.price} is {dev:+.0f}% from the median (₹{med:.2f}) – possible entry error"})
        last = datetime.strptime(recs[-1].date, "%Y-%m-%d").date()
        if (today - last).days > stale_days:
            flags.append({"level": "info", "produce": prod,
                          "message": f"{prod}: no new price for {(today - last).days} days (last {last}) – update overdue"})
    return flags
