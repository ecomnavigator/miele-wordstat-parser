from __future__ import annotations

import csv
import hashlib
from dataclasses import dataclass
from pathlib import Path

import duckdb

from .classification import infer_intent, infer_super_intent
from .config import Settings
from .db import initialize_database


@dataclass(frozen=True)
class SeedQuery:
    query: str
    category: str | None
    region: int


def stable_id(*parts: object) -> str:
    raw = "\x1f".join(str(part) for part in parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def read_seed_queries(path: Path, default_region: int) -> list[SeedQuery]:
    with path.open(newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        seeds: list[SeedQuery] = []
        for row in reader:
            query = (row.get("query") or "").strip()
            if not query:
                continue
            category = (row.get("category") or "").strip() or None
            region_raw = (row.get("region") or "").strip()
            region = int(region_raw) if region_raw else default_region
            seeds.append(SeedQuery(query=query, category=category, region=region))
    return seeds


def plan_from_seed_file(settings: Settings, seed_file: Path) -> dict[str, int]:
    initialize_database(settings)
    seeds = read_seed_queries(seed_file, settings.default_region)

    inserted_queries = 0
    inserted_tasks = 0
    with duckdb.connect(str(settings.duckdb_path)) as con:
        for seed in seeds:
            query_id = stable_id("query", seed.query)
            task_id = stable_id("web_search", seed.query, seed.region)
            intent = infer_intent(seed.query)
            super_intent = infer_super_intent(intent)

            if not con.execute(
                "select 1 from queries where query_id = ?", [query_id]
            ).fetchone():
                con.execute(
                    """
                    insert into queries (
                        query_id,
                        query,
                        normalized_query,
                        category,
                        intent,
                        super_intent,
                        source
                    )
                    values (?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        query_id,
                        seed.query,
                        seed.query.casefold(),
                        seed.category,
                        intent,
                        super_intent,
                        "seed",
                    ],
                )
                inserted_queries += 1
            else:
                con.execute(
                    """
                    update queries
                    set category = coalesce(category, ?),
                        intent = coalesce(intent, ?),
                        super_intent = coalesce(super_intent, ?)
                    where query_id = ?
                    """,
                    [seed.category, intent, super_intent, query_id],
                )

            if not con.execute(
                "select 1 from collection_tasks where task_id = ?", [task_id]
            ).fetchone():
                con.execute(
                    """
                    insert into collection_tasks (
                        task_id, method, query, region, status
                    )
                    values (?, ?, ?, ?, 'pending')
                    """,
                    [task_id, "web_search", seed.query, seed.region],
                )
                inserted_tasks += 1

    return {
        "seed_rows": len(seeds),
        "inserted_queries": inserted_queries,
        "inserted_tasks": inserted_tasks,
    }
