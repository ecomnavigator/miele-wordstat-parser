from __future__ import annotations

import duckdb
import pandas as pd
import plotly.express as px
import streamlit as st

from miele_wordstat.config import load_settings


st.set_page_config(page_title="Miele Wordstat BI", layout="wide")
st.title("Miele Wordstat BI")

settings = load_settings()
st.caption(f"Data root: {settings.data_root}")

if not settings.duckdb_path.exists():
    st.warning("DuckDB database is not initialized yet.")
    st.stop()

con = duckdb.connect(str(settings.duckdb_path), read_only=True)

snapshots = con.execute(
    """
    select
        query,
        coalesce(found_docs_all, found_all) as result_count,
        found_all,
        found_docs_all,
        top_domain,
        top_url,
        fetched_at
    from search_snapshots
    order by result_count desc nulls last
    """
).fetchdf()

if not snapshots.empty:
    st.subheader("Search result count")
    fig = px.bar(
        snapshots,
        x="query",
        y="result_count",
        color="top_domain",
        hover_data=["found_all", "found_docs_all", "top_url"],
    )
    fig.update_layout(xaxis_title=None, yaxis_title="Results")
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(snapshots, use_container_width=True)
    st.stop()

categories = con.execute(
    "select distinct category from queries where category is not null order by 1"
).fetchdf()

selected_categories = st.multiselect(
    "Categories",
    categories["category"].tolist() if not categories.empty else [],
)

where = ""
params: list[str] = []
if selected_categories:
    placeholders = ",".join(["?"] * len(selected_categories))
    where = f"where q.category in ({placeholders})"
    params.extend(selected_categories)

df = con.execute(
    f"""
    select
        f.month,
        coalesce(q.category, 'uncategorized') as category,
        sum(f.impressions) as impressions
    from frequency_monthly f
    left join queries q on q.query_id = f.query_id
    {where}
    group by 1, 2
    order by 1, 2
    """,
    params,
).fetchdf()

if df.empty:
    st.info("No frequency data yet.")
    st.stop()

df["month"] = pd.to_datetime(df["month"])

fig = px.line(
    df,
    x="month",
    y="impressions",
    color="category",
    title="Monthly demand",
)
st.plotly_chart(fig, use_container_width=True)

st.dataframe(df, use_container_width=True)
