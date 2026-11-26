"""Markdown / plain-text / CSV exports."""
from __future__ import annotations

import csv
import io
from datetime import datetime

from . import analytics
from .validation import FIELDS


def to_csv(records) -> str:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=FIELDS)
    w.writeheader()
    for r in records:
        w.writerow(r.to_dict())
    return buf.getvalue()


def to_markdown(records) -> str:
    s, stats, flags = analytics.summary(records), analytics.produce_stats(records), analytics.warnings(records)
    lines = ["# Farm Produce Price Report", f"_Generated {datetime.now():%Y-%m-%d %H:%M}_", "",
             "## Summary", f"- Entries: **{s['entries']}**", f"- Produce items: **{s['produce_count']}**",
             f"- Markets: **{s['markets']}**", f"- Average price: **₹{s['avg_price']}/kg**"]
    if s["entries"]:
        lines += [f"- Highest: {s['highest']}", f"- Lowest: {s['lowest']}", f"- Period: {s['date_range'][0]} to {s['date_range'][1]}"]
    lines += ["", "## Price trends", "| Produce | Avg | Min | Max | Latest | Change | Trend |", "|---|---:|---:|---:|---:|---:|---|"]
    lines += [f"| {x['produce']} | {x['avg']} | {x['min']} | {x['max']} | {x['latest']} | {x['change_pct']:+.1f}% | {x['trend']} |" for x in stats]
    lines += ["", "## Warnings"] + ([f"- **{f['level'].upper()}** {f['message']}" for f in flags] or ["- None"])
    return "\n".join(lines) + "\n"


def to_text(records) -> str:
    s, stats, flags = analytics.summary(records), analytics.produce_stats(records), analytics.warnings(records)
    out = ["FARM PRODUCE PRICE AUDIT LOG", "=" * 60, f"Generated: {datetime.now():%Y-%m-%d %H:%M}",
           f"Entries: {s['entries']} | Produce: {s['produce_count']} | Markets: {s['markets']} | Avg: Rs {s['avg_price']}/kg", "",
           f"{'Produce':<14}{'Avg':>8}{'Min':>8}{'Max':>8}{'Latest':>8}{'Chg%':>8}  Trend", "-" * 60]
    out += [f"{x['produce']:<14}{x['avg']:>8}{x['min']:>8}{x['max']:>8}{x['latest']:>8}{x['change_pct']:>+8.1f}  {x['trend']}" for x in stats]
    out += ["", "WARNINGS", "-" * 60] + ([f"[{f['level'].upper()}] {f['message']}" for f in flags] or ["None"])
    return "\n".join(out) + "\n"
