# 🌾 Farm Produce Price Notebook (Streamlit)

Record market prices (₹/kg), compare produce costs over time, validate every input,
persist to JSON, and export Markdown / text / CSV reports.

## Run
```bash
pip install -r requirements.txt
python -m pricebook.seed        # creates data/ with 40 sample records + error-demo CSV
streamlit run app.py
python -m unittest discover -s tests -t .     # core tests (no UI needed)
```

## Plan (maps to the brief's 8 steps)
| # | Step | Where |
|---|------|-------|
| 1 | Project structure, requirements | this folder, `requirements.txt` |
| 2 | Data model | `PriceRecord` dataclass – `pricebook/validation.py` |
| 3 | Defensive validation (all errors reported at once, range/date/regex/duplicate checks) | `validation.py`, `storage.add` |
| 4 | Core logic: series, trends, market comparison, warnings | `pricebook/analytics.py` |
| 5 | Persistence: atomic JSON writes, corrupt-file recovery | `pricebook/storage.py` |
| 6 | Navigation (sidebar pages) | `app.py` |
| 7 | Summary tables + charts | Dashboard / Compare & Trends pages |
| 8 | Seed data + tests + demo script | `seed.py`, `tests/` |

Stretch: Markdown/TXT/CSV export (`exporters.py`), threshold warnings (spikes ≥25%, outliers ≥50% from median,
stale >30 days), bulk CSV import with row-by-row error log (`importer.py`).

## 5-minute demo script
1. Dashboard: metrics, ⚠ warnings (Tomato spike), trend table.
2. Add Entry: submit blank produce, future date, price `abc` → all errors shown; then a valid entry.
3. Browse & Search: keyword `dal`, category filter.
4. Compare & Trends: Tomato vs Onion vs Potato line chart; market comparison.
5. Import: upload `data/sample_import_with_errors.csv` → 1 imported, 6 rejected with reasons.
6. Stop and relaunch the app → data persists. Download the Markdown report.

## Swapping the UI
`pricebook/` has no UI imports. To use NiceGUI or FastHTML, replace `app.py` only.
