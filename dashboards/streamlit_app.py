from __future__ import annotations

import duckdb
import pandas as pd
import plotly.express as px
import streamlit as st

from miele_wordstat.classification import infer_intent, resolve_super_intent
from miele_wordstat.config import load_settings


st.set_page_config(page_title="Miele Wordstat BI", layout="wide")
st.title("Miele Wordstat BI")

settings = load_settings()
st.caption(f"Data root: {settings.data_root}")

if not settings.duckdb_path.exists():
    st.warning("DuckDB database is not initialized yet.")
    st.stop()


@st.cache_data(ttl=60)
def load_search_snapshots(duckdb_path: str) -> pd.DataFrame:
    with duckdb.connect(duckdb_path, read_only=True) as con:
        return con.execute(
            """
            select
                s.task_id,
                s.query,
                coalesce(q.category, 'uncategorized') as category,
                q.intent,
                q.super_intent,
                q.product_type,
                s.region,
                s.fetched_at,
                s.found_all,
                s.found_phrase,
                s.found_docs_all,
                s.found_docs_phrase,
                coalesce(s.found_docs_all, s.found_all) as result_count,
                s.top_domain,
                s.top_url,
                s.source_file
            from search_snapshots s
            left join queries q on q.query = s.query
            order by result_count desc nulls last
            """
        ).fetchdf()


@st.cache_data(ttl=60)
def load_frequency_monthly(duckdb_path: str) -> pd.DataFrame:
    with duckdb.connect(duckdb_path, read_only=True) as con:
        return con.execute(
            """
            select
                f.month,
                f.query,
                coalesce(q.category, 'uncategorized') as category,
                q.intent,
                q.super_intent,
                q.product_type,
                f.region,
                f.impressions,
                f.source,
                f.fetched_at
            from frequency_monthly f
            left join queries q on q.query_id = f.query_id
            order by f.month, f.query
            """
        ).fetchdf()


@st.cache_data(ttl=60)
def load_search_results(duckdb_path: str) -> pd.DataFrame:
    with duckdb.connect(duckdb_path, read_only=True) as con:
        return con.execute(
            """
            select
                r.task_id,
                r.query,
                coalesce(q.category, 'uncategorized') as category,
                q.intent,
                q.super_intent,
                q.product_type,
                r.region,
                r.fetched_at,
                r.position,
                r.domain,
                r.url,
                r.title,
                r.snippet
            from search_results r
            left join queries q on q.query = r.query
            order by r.query, r.position
            """
        ).fetchdf()


def csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8-sig")


snapshots = load_search_snapshots(str(settings.duckdb_path))

if snapshots.empty:
    st.info("No search snapshots yet.")
    st.stop()

snapshots["fetched_at"] = pd.to_datetime(snapshots["fetched_at"])
snapshots["result_count"] = pd.to_numeric(snapshots["result_count"], errors="coerce")
snapshots["found_all"] = pd.to_numeric(snapshots["found_all"], errors="coerce")
snapshots["found_docs_all"] = pd.to_numeric(
    snapshots["found_docs_all"], errors="coerce"
)
snapshots["top_domain"] = snapshots["top_domain"].fillna("unknown")
snapshots["intent"] = [
    infer_intent(query, intent)
    for query, intent in zip(snapshots["query"], snapshots["intent"], strict=False)
]
snapshots["super_intent"] = snapshots["super_intent"].where(
    snapshots["super_intent"].notna(), None
)
snapshots["super_intent"] = [
    resolve_super_intent(intent, super_intent)
    for intent, super_intent in zip(
        snapshots["intent"], snapshots["super_intent"], strict=False
    )
]
organic_results = load_search_results(str(settings.duckdb_path))
if not organic_results.empty:
    organic_results["fetched_at"] = pd.to_datetime(organic_results["fetched_at"])
    organic_results["domain"] = organic_results["domain"].fillna("unknown")
    organic_results["intent"] = [
        infer_intent(query, intent)
        for query, intent in zip(
            organic_results["query"], organic_results["intent"], strict=False
        )
    ]
    organic_results["super_intent"] = organic_results["super_intent"].where(
        organic_results["super_intent"].notna(), None
    )
    organic_results["super_intent"] = [
        resolve_super_intent(intent, super_intent)
        for intent, super_intent in zip(
            organic_results["intent"],
            organic_results["super_intent"],
            strict=False,
        )
    ]

with st.sidebar:
    st.header("Filters")
    query_text = st.text_input("Query contains")

    categories = sorted(snapshots["category"].dropna().unique().tolist())
    selected_categories = st.multiselect("Categories", categories)

    intents = sorted(snapshots["intent"].dropna().unique().tolist())
    selected_intents = st.multiselect("Intents", intents)

    super_intents = sorted(snapshots["super_intent"].dropna().unique().tolist())
    selected_super_intents = st.multiselect("Super intents", super_intents)

    domains = sorted(snapshots["top_domain"].dropna().unique().tolist())
    selected_domains = st.multiselect("Top domains", domains)

    regions = sorted(snapshots["region"].dropna().unique().tolist())
    selected_regions = st.multiselect("Regions", regions)

    max_result_count = int(snapshots["result_count"].fillna(0).max())
    result_range = st.slider(
        "Result count range",
        min_value=0,
        max_value=max_result_count,
        value=(0, max_result_count),
        step=max(1, max_result_count // 100),
    )

    top_n = st.slider("Top N", min_value=5, max_value=100, value=30, step=5)

filtered = snapshots.copy()
if query_text:
    filtered = filtered[
        filtered["query"].str.contains(query_text, case=False, na=False)
    ]
if selected_categories:
    filtered = filtered[filtered["category"].isin(selected_categories)]
if selected_intents:
    filtered = filtered[filtered["intent"].isin(selected_intents)]
if selected_super_intents:
    filtered = filtered[filtered["super_intent"].isin(selected_super_intents)]
if selected_domains:
    filtered = filtered[filtered["top_domain"].isin(selected_domains)]
if selected_regions:
    filtered = filtered[filtered["region"].isin(selected_regions)]
filtered = filtered[
    filtered["result_count"].between(result_range[0], result_range[1], inclusive="both")
]

if filtered.empty:
    st.warning("No rows match the selected filters.")
    st.stop()

latest_fetch = filtered["fetched_at"].max()
total_queries = len(filtered)
median_results = int(filtered["result_count"].median())
max_results = int(filtered["result_count"].max())
domain_count = filtered["top_domain"].nunique()

kpi_cols = st.columns(5)
kpi_cols[0].metric("Queries", f"{total_queries:,}")
kpi_cols[1].metric("Median results", f"{median_results:,}")
kpi_cols[2].metric("Max results", f"{max_results:,}")
kpi_cols[3].metric("Top domains", f"{domain_count:,}")
kpi_cols[4].metric("Latest fetch", latest_fetch.strftime("%Y-%m-%d %H:%M"))

download_cols = st.columns([1, 1, 3])
download_cols[0].download_button(
    "Download filtered CSV",
    data=csv_bytes(filtered),
    file_name="miele_filtered_queries.csv",
    mime="text/csv",
)

(
    tab_overview,
    tab_domains,
    tab_categories,
    tab_intents,
    tab_super_intents,
    tab_history,
    tab_data,
) = st.tabs(
    [
        "Overview",
        "Domains",
        "Categories",
        "Intents",
        "Super Intents",
        "History",
        "Data",
    ]
)

with tab_overview:
    top_queries = filtered.nlargest(top_n, "result_count")
    fig = px.bar(
        top_queries.sort_values("result_count"),
        x="result_count",
        y="query",
        color="category",
        orientation="h",
        hover_data=["found_all", "found_docs_all", "top_domain", "top_url"],
        title=f"Top {min(top_n, len(top_queries))} queries by result count",
    )
    fig.update_layout(xaxis_title="Results", yaxis_title=None)
    st.plotly_chart(fig, width="stretch")

    chart_cols = st.columns(2)
    with chart_cols[0]:
        hist = px.histogram(
            filtered,
            x="result_count",
            nbins=40,
            title="Result count distribution",
        )
        hist.update_layout(xaxis_title="Results", yaxis_title="Queries")
        st.plotly_chart(hist, width="stretch")
    with chart_cols[1]:
        scatter = px.scatter(
            filtered,
            x="found_all",
            y="found_docs_all",
            color="category",
            hover_name="query",
            hover_data=["top_domain"],
            title="Found all vs found docs",
            log_x=True,
            log_y=True,
        )
        scatter.update_layout(xaxis_title="found_all", yaxis_title="found_docs_all")
        st.plotly_chart(scatter, width="stretch")

with tab_domains:
    filtered_results = organic_results[
        organic_results["task_id"].isin(filtered["task_id"])
    ].copy()
    if selected_domains and not filtered_results.empty:
        filtered_results = filtered_results[
            filtered_results["domain"].isin(selected_domains)
        ]

    if filtered_results.empty:
        st.info("No organic position rows yet. Run parse after collecting top-10 data.")
        domain_summary = (
            filtered.groupby("top_domain", as_index=False)
            .agg(
                queries=("query", "count"),
                median_results=("result_count", "median"),
                max_results=("result_count", "max"),
            )
            .rename(columns={"top_domain": "domain"})
            .sort_values(["queries", "max_results"], ascending=False)
            .head(top_n)
        )
        fig = px.bar(
            domain_summary.sort_values("queries"),
            x="queries",
            y="domain",
            orientation="h",
            hover_data=["median_results", "max_results"],
            title=f"Top {len(domain_summary)} domains appearing first in results",
        )
        fig.update_layout(xaxis_title="Queries", yaxis_title=None)
        st.plotly_chart(fig, width="stretch")
        st.dataframe(domain_summary, width="stretch", hide_index=True)
    else:
        domain_summary = (
            filtered_results.groupby("domain", as_index=False)
            .agg(
                top10_appearances=("query", "count"),
                unique_queries=("query", "nunique"),
                best_position=("position", "min"),
                avg_position=("position", "mean"),
                top3_appearances=("position", lambda values: int((values <= 3).sum())),
                position1_appearances=(
                    "position",
                    lambda values: int((values == 1).sum()),
                ),
            )
            .sort_values(
                ["top10_appearances", "top3_appearances", "position1_appearances"],
                ascending=False,
            )
            .head(top_n)
        )
        fig = px.bar(
            domain_summary.sort_values("top10_appearances"),
            x="top10_appearances",
            y="domain",
            orientation="h",
            hover_data=[
                "unique_queries",
                "top3_appearances",
                "position1_appearances",
                "best_position",
                "avg_position",
            ],
            title=f"Top {len(domain_summary)} domains in organic top-10",
        )
        fig.update_layout(xaxis_title="Top-10 appearances", yaxis_title=None)
        st.plotly_chart(fig, width="stretch")

        position_distribution = (
            filtered_results.groupby(["position", "domain"], as_index=False)
            .agg(appearances=("query", "count"))
            .sort_values("appearances", ascending=False)
        )
        top_domains = domain_summary["domain"].head(10).tolist()
        fig = px.bar(
            position_distribution[position_distribution["domain"].isin(top_domains)],
            x="position",
            y="appearances",
            color="domain",
            title="Position distribution for top domains",
        )
        fig.update_layout(xaxis_title="Organic position", yaxis_title="Appearances")
        st.plotly_chart(fig, width="stretch")

        st.dataframe(domain_summary, width="stretch", hide_index=True)
        st.download_button(
            "Download domain visibility CSV",
            data=csv_bytes(domain_summary),
            file_name="miele_domain_visibility_top10.csv",
            mime="text/csv",
        )

with tab_categories:
    category_summary = (
        filtered.groupby("category", as_index=False)
        .agg(
            queries=("query", "count"),
            median_results=("result_count", "median"),
            max_results=("result_count", "max"),
            avg_results=("result_count", "mean"),
        )
        .sort_values("queries", ascending=False)
    )
    fig = px.treemap(
        category_summary,
        path=["category"],
        values="queries",
        color="median_results",
        color_continuous_scale="Blues",
        title="Query coverage by category",
    )
    st.plotly_chart(fig, width="stretch")
    st.dataframe(category_summary, width="stretch", hide_index=True)
    st.download_button(
        "Download category summary CSV",
        data=csv_bytes(category_summary),
        file_name="miele_category_summary.csv",
        mime="text/csv",
    )

with tab_intents:
    intent_summary = (
        filtered.groupby("intent", as_index=False)
        .agg(
            queries=("query", "count"),
            median_results=("result_count", "median"),
            max_results=("result_count", "max"),
            avg_results=("result_count", "mean"),
        )
        .sort_values("queries", ascending=False)
    )
    chart_cols = st.columns(2)
    with chart_cols[0]:
        fig = px.pie(
            intent_summary,
            names="intent",
            values="queries",
            title="Query mix by intent",
        )
        st.plotly_chart(fig, width="stretch")
    with chart_cols[1]:
        fig = px.bar(
            intent_summary.sort_values("median_results"),
            x="median_results",
            y="intent",
            orientation="h",
            hover_data=["queries", "max_results"],
            title="Median result count by intent",
        )
        fig.update_layout(xaxis_title="Median results", yaxis_title=None)
        st.plotly_chart(fig, width="stretch")
    st.dataframe(intent_summary, width="stretch", hide_index=True)
    st.download_button(
        "Download intent summary CSV",
        data=csv_bytes(intent_summary),
        file_name="miele_intent_summary.csv",
        mime="text/csv",
    )

with tab_super_intents:
    super_intent_summary = (
        filtered.groupby("super_intent", as_index=False)
        .agg(
            queries=("query", "count"),
            median_results=("result_count", "median"),
            max_results=("result_count", "max"),
            avg_results=("result_count", "mean"),
        )
        .sort_values("queries", ascending=False)
    )
    chart_cols = st.columns(2)
    with chart_cols[0]:
        fig = px.pie(
            super_intent_summary,
            names="super_intent",
            values="queries",
            title="Commercial vs informational mix",
        )
        st.plotly_chart(fig, width="stretch")
    with chart_cols[1]:
        fig = px.bar(
            super_intent_summary.sort_values("median_results"),
            x="median_results",
            y="super_intent",
            orientation="h",
            hover_data=["queries", "max_results"],
            title="Median result count by super intent",
        )
        fig.update_layout(xaxis_title="Median results", yaxis_title=None)
        st.plotly_chart(fig, width="stretch")
    st.dataframe(super_intent_summary, width="stretch", hide_index=True)
    st.download_button(
        "Download super intent summary CSV",
        data=csv_bytes(super_intent_summary),
        file_name="miele_super_intent_summary.csv",
        mime="text/csv",
    )

with tab_history:
    st.subheader("Collection timeline")
    hourly = (
        filtered.assign(hour=filtered["fetched_at"].dt.floor("h"))
        .groupby("hour", as_index=False)
        .agg(queries=("query", "count"), median_results=("result_count", "median"))
    )
    fig = px.bar(
        hourly,
        x="hour",
        y="queries",
        hover_data=["median_results"],
        title="Collected queries by hour",
    )
    fig.update_layout(xaxis_title=None, yaxis_title="Queries")
    st.plotly_chart(fig, width="stretch")

    monthly = load_frequency_monthly(str(settings.duckdb_path))
    if monthly.empty:
        st.info(
            "No historical monthly demand data yet. Current data is a one-day Search API snapshot, not Wordstat history."
        )
    else:
        monthly["month"] = pd.to_datetime(monthly["month"])
        if selected_categories:
            monthly = monthly[monthly["category"].isin(selected_categories)]
        demand = (
            monthly.groupby(["month", "category"], as_index=False)["impressions"].sum()
        )
        fig = px.line(
            demand,
            x="month",
            y="impressions",
            color="category",
            title="Monthly demand",
        )
        fig.update_layout(xaxis_title=None, yaxis_title="Impressions")
        st.plotly_chart(fig, width="stretch")
        st.dataframe(monthly, width="stretch", hide_index=True)

with tab_data:
    st.dataframe(
        filtered[
            [
                "query",
                "category",
                "super_intent",
                "intent",
                "region",
                "result_count",
                "found_all",
                "found_phrase",
                "found_docs_all",
                "found_docs_phrase",
                "top_domain",
                "top_url",
                "fetched_at",
            ]
        ],
        width="stretch",
        hide_index=True,
    )
    if not organic_results.empty:
        st.subheader("Organic positions")
        st.dataframe(
            organic_results[
                organic_results["task_id"].isin(filtered["task_id"])
            ][
                [
                    "query",
                    "category",
                    "super_intent",
                    "intent",
                    "position",
                    "domain",
                    "url",
                    "title",
                    "snippet",
                    "fetched_at",
                ]
            ],
            width="stretch",
            hide_index=True,
        )
