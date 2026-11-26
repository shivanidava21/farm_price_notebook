"""Farm Produce Price Notebook – Streamlit UI.   Run:  streamlit run app.py"""
from datetime import date

import pandas as pd
import streamlit as st

from pricebook import analytics, exporters
from pricebook.importer import import_csv
from pricebook.storage import Store
from pricebook.validation import CATEGORIES, MAX_PRICE, MIN_PRICE, ValidationError

st.set_page_config(page_title="Farm Produce Price Notebook", page_icon="🌾", layout="wide")


@st.cache_resource
def get_store() -> Store:
    return Store("data/prices.json")


store = get_store()
ARROWS = {"Rising": "▲ Rising", "Falling": "▼ Falling", "Stable": "● Stable"}


def to_df(records) -> pd.DataFrame:
    cols = ["id", "date", "produce", "category", "market", "price", "notes"]
    return pd.DataFrame([r.to_dict() for r in records], columns=cols)


# ---------------------------------------------------------------- sidebar
st.sidebar.title("🌾 Price Notebook")
st.sidebar.caption("Record & compare market prices (₹/kg)")
page = st.sidebar.radio("Menu", ["📊 Dashboard", "➕ Add Entry", "🔎 Browse & Search",
                                 "📈 Compare & Trends", "📁 Import / Export"])
st.sidebar.metric("Entries stored", len(store.records))
if store.recovery_note:
    st.sidebar.warning(store.recovery_note)

# ---------------------------------------------------------------- dashboard
if page.endswith("Dashboard"):
    st.title("🌾 Farm Produce Price Notebook")
    s = analytics.summary(store.records)
    if not s["entries"]:
        st.info("No data yet. Add an entry, import a CSV, or run `python -m pricebook.seed`.")
        st.stop()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Entries", s["entries"])
    c2.metric("Produce items", s["produce_count"])
    c3.metric("Markets", s["markets"])
    c4.metric("Avg price", f"₹{s['avg_price']}")
    st.caption(f"Highest: {s['highest']}  •  Lowest: {s['lowest']}  •  Period: {s['date_range'][0]} → {s['date_range'][1]}")

    flags = analytics.warnings(store.records)
    if flags:
        st.subheader(f"⚠️ Warnings ({len(flags)})")
        for f in flags:
            {"critical": st.error, "warning": st.warning}.get(f["level"], st.info)(f["message"])

    st.subheader("Price summary & trends")
    stats = pd.DataFrame(analytics.produce_stats(store.records))
    stats["trend"] = stats["trend"].map(ARROWS)
    st.dataframe(stats.rename(columns={"change_pct": "change %"}), use_container_width=True, hide_index=True)
    st.bar_chart(stats.set_index("produce")["latest"], y_label="Latest price ₹/kg")

# ---------------------------------------------------------------- add entry
elif page.endswith("Add Entry"):
    st.title("➕ Record a market price")
    st.caption("Price is typed as text on purpose, so you can see validation catch bad input.")
    with st.form("add_form", clear_on_submit=False):
        a, b = st.columns(2)
        d = a.date_input("Date", value=date.today(), max_value=date.today())
        produce = b.text_input("Produce", placeholder="e.g. Tomato")
        category = a.selectbox("Category", CATEGORIES)
        market = b.text_input("Market", placeholder="e.g. Bowenpally Market")
        price = a.text_input("Price (₹ per kg)", placeholder=f"{MIN_PRICE} – {MAX_PRICE:,.0f}")
        notes = b.text_input("Notes (optional)")
        submitted = st.form_submit_button("Save entry", type="primary")
    if submitted:
        try:
            rec = store.add({"date": d, "produce": produce, "category": category,
                             "market": market, "price": price, "notes": notes})
            st.success(f"Saved #{rec.id}: {rec.produce} ₹{rec.price}/kg at {rec.market} on {rec.date}")
            for f in analytics.warnings(store.records):
                if f["produce"] == rec.produce and rec.date in f["message"]:
                    st.warning(f["message"])
        except ValidationError as e:
            for msg in e.errors:
                st.error(msg)

# ---------------------------------------------------------------- browse
elif page.endswith("Browse & Search"):
    st.title("🔎 Browse & Search")
    c1, c2, c3 = st.columns(3)
    kw = c1.text_input("Keyword", placeholder="produce, market, notes…")
    cats = c2.multiselect("Category", CATEGORIES)
    prods = c3.multiselect("Produce", sorted({r.produce for r in store.records}))
    dr = st.date_input("Date range (optional)", value=(), max_value=date.today())
    start, end = (dr[0].isoformat(), dr[1].isoformat()) if len(dr) == 2 else (None, None)
    hits = store.search(kw, cats, prods, start, end)
    st.write(f"**{len(hits)}** matching entries")
    st.dataframe(to_df(hits), use_container_width=True, hide_index=True)
    with st.expander("Delete an entry"):
        rid = st.number_input("Entry ID", min_value=1, step=1)
        if st.button("Delete"):
            st.success("Deleted.") if store.delete(int(rid)) else st.error("No entry with that ID.")

# ---------------------------------------------------------------- trends
elif page.endswith("Compare & Trends"):
    st.title("📈 Compare produce costs over time")
    names = sorted({r.produce for r in store.records})
    if not names:
        st.info("No data yet.")
        st.stop()
    c1, c2 = st.columns([3, 1])
    chosen = c1.multiselect("Produce to compare", names, default=names[:3])
    market = c2.selectbox("Market", ["All"] + sorted({r.market for r in store.records}))
    df = to_df(store.records)
    if market != "All":
        df = df[df.market == market]
    df = df[df.produce.isin(chosen)]
    if df.empty:
        st.info("Nothing to plot for this selection.")
    else:
        pivot = df.groupby(["date", "produce"])["price"].mean().unstack()
        st.line_chart(pivot, y_label="₹ per kg")
        st.subheader("Same produce across markets")
        pick = st.selectbox("Produce", chosen or names)
        mc = analytics.market_comparison(store.records, pick)
        st.bar_chart(pd.Series(mc, name="avg ₹/kg"))

# ---------------------------------------------------------------- import/export
else:
    st.title("📁 Import / Export")
    st.subheader("Bulk import (CSV)")
    st.caption("Required columns: date, produce, category, market, price. Try data/sample_import_with_errors.csv.")
    up = st.file_uploader("Choose a CSV file", type="csv")
    if up and st.button("Import", type="primary"):
        res = import_csv(up.getvalue().decode("utf-8", errors="replace"), store)
        st.success(f"Imported {res.imported} row(s).")
        if res.errors:
            st.error(f"{len(res.errors)} row(s) rejected")
            st.dataframe(pd.DataFrame(res.errors, columns=["row", "reason"]), hide_index=True, use_container_width=True)
            st.download_button("Download error log", res.error_log(), "import_errors.txt")

    st.subheader("Export reports")
    c1, c2, c3 = st.columns(3)
    c1.download_button("📝 Markdown report", exporters.to_markdown(store.records), "price_report.md")
    c2.download_button("📄 Text audit log", exporters.to_text(store.records), "price_audit.txt")
    c3.download_button("📊 CSV data", exporters.to_csv(store.records), "prices.csv")
