from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

from .classification import infer_intent, resolve_super_intent
from .config import Settings
from .domains import classify_competitor, normalize_domain


def csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8-sig")


def write_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(csv_bytes(df))


def enrich_query_fields(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    result = df.copy()
    result["intent"] = [
        infer_intent(query, intent)
        for query, intent in zip(result["query"], result.get("intent"), strict=False)
    ]
    result["super_intent"] = [
        resolve_super_intent(intent, super_intent)
        for intent, super_intent in zip(
            result["intent"], result.get("super_intent"), strict=False
        )
    ]
    return result


def export_bi(settings: Settings) -> dict[str, Path | int]:
    output_dir = settings.exports_dir / "bi"
    output_dir.mkdir(parents=True, exist_ok=True)

    with duckdb.connect(str(settings.duckdb_path), read_only=True) as con:
        queries = con.execute(
            """
            select
                query_id,
                query,
                normalized_query,
                coalesce(category, 'uncategorized') as category,
                intent,
                super_intent,
                product_type,
                source,
                first_seen_at
            from queries
            order by query
            """
        ).fetchdf()
        snapshots = con.execute(
            """
            select
                s.task_id,
                s.query,
                coalesce(q.category, 'uncategorized') as category,
                q.intent,
                q.super_intent,
                s.region,
                s.fetched_at,
                coalesce(s.found_docs_all, s.found_all) as result_count,
                s.found_all,
                s.found_phrase,
                s.found_docs_all,
                s.found_docs_phrase,
                s.top_domain,
                s.top_url
            from search_snapshots s
            left join queries q on q.query = s.query
            order by result_count desc nulls last
            """
        ).fetchdf()
        organic_positions = con.execute(
            """
            select
                r.task_id,
                r.query,
                coalesce(q.category, 'uncategorized') as category,
                q.intent,
                q.super_intent,
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

    queries = enrich_query_fields(queries)
    snapshots = enrich_query_fields(snapshots)
    organic_positions = enrich_query_fields(organic_positions)

    if not snapshots.empty:
        snapshots["normalized_top_domain"] = snapshots["top_domain"].map(
            normalize_domain
        )
        snapshots["top_competitor_type"] = snapshots["normalized_top_domain"].map(
            classify_competitor
        )

    if not organic_positions.empty:
        organic_positions["normalized_domain"] = organic_positions["domain"].map(
            normalize_domain
        )
        organic_positions["competitor_type"] = organic_positions[
            "normalized_domain"
        ].map(classify_competitor)

    domain_visibility = pd.DataFrame()
    competitors_by_super_intent = pd.DataFrame()
    if not organic_positions.empty:
        domain_visibility = (
            organic_positions.groupby(
                ["normalized_domain", "competitor_type"], as_index=False
            )
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
        )
        competitors_by_super_intent = (
            organic_positions.groupby(
                ["super_intent", "normalized_domain", "competitor_type"],
                as_index=False,
            )
            .agg(
                top10_appearances=("query", "count"),
                unique_queries=("query", "nunique"),
                top3_appearances=("position", lambda values: int((values <= 3).sum())),
                position1_appearances=(
                    "position",
                    lambda values: int((values == 1).sum()),
                ),
                best_position=("position", "min"),
                avg_position=("position", "mean"),
            )
            .sort_values(
                ["super_intent", "top10_appearances", "top3_appearances"],
                ascending=[True, False, False],
            )
        )

    files = {
        "queries": output_dir / "queries.csv",
        "search_snapshots": output_dir / "search_snapshots.csv",
        "organic_positions": output_dir / "organic_positions.csv",
        "domain_visibility": output_dir / "domain_visibility.csv",
        "competitors_by_super_intent": output_dir / "competitors_by_super_intent.csv",
    }
    write_csv(queries, files["queries"])
    write_csv(snapshots, files["search_snapshots"])
    write_csv(organic_positions, files["organic_positions"])
    write_csv(domain_visibility, files["domain_visibility"])
    write_csv(competitors_by_super_intent, files["competitors_by_super_intent"])

    return {
        "output_dir": output_dir,
        "queries": len(queries),
        "search_snapshots": len(snapshots),
        "organic_positions": len(organic_positions),
        "domain_visibility": len(domain_visibility),
        "competitors_by_super_intent": len(competitors_by_super_intent),
    }
