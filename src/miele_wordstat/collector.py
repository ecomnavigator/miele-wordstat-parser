from __future__ import annotations

import json
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import duckdb

from .config import Settings
from .db import initialize_database
from .yandex_client import YandexSearchApiError, YandexWordstatClient


def utc_now() -> datetime:
    return datetime.now(tz=UTC)


def raw_output_path(settings: Settings, task_id: str, now: datetime) -> Path:
    day_dir = settings.raw_dir / now.strftime("%Y-%m-%d")
    day_dir.mkdir(parents=True, exist_ok=True)
    return day_dir / f"{task_id}.json"


def pending_tasks(settings: Settings, limit: int) -> list[dict[str, Any]]:
    with duckdb.connect(str(settings.duckdb_path)) as con:
        rows = con.execute(
            """
            select task_id, method, query, region, attempts
            from collection_tasks
            where status in ('pending', 'failed')
              and method = 'web_search'
            order by created_at, task_id
            limit ?
            """,
            [limit],
        ).fetchall()
    return [
        {
            "task_id": row[0],
            "method": row[1],
            "query": row[2],
            "region": row[3],
            "attempts": row[4],
        }
        for row in rows
    ]


def run_batch(
    settings: Settings,
    limit: int,
    *,
    stop_on_failure: bool = False,
) -> dict[str, int]:
    initialize_database(settings)
    if not settings.yandex_search_api_key:
        raise YandexSearchApiError("YANDEX_SEARCH_API_KEY is missing")
    if not settings.yandex_folder_id:
        raise YandexSearchApiError("YANDEX_FOLDER_ID is missing")

    client = YandexWordstatClient(
        api_key=settings.yandex_search_api_key,
        folder_id=settings.yandex_folder_id,
    )
    tasks = pending_tasks(settings, limit)
    completed = 0
    failed = 0
    delay = 60 / max(settings.max_requests_per_minute, 1)

    with duckdb.connect(str(settings.duckdb_path)) as con:
        for index, task in enumerate(tasks):
            started_at = utc_now()
            con.execute(
                """
                update collection_tasks
                set status = 'running',
                    attempts = attempts + 1,
                    started_at = ?,
                    error_message = null
                where task_id = ?
                """,
                [started_at, task["task_id"]],
            )

            try:
                response = client.web_search(
                    query=task["query"],
                    region=int(task["region"]),
                    groups_on_page=1,
                    docs_in_group=1,
                )
                finished_at = utc_now()
                raw_path = raw_output_path(settings, task["task_id"], finished_at)
                payload = {
                    "task": task,
                    "fetched_at": finished_at.isoformat(),
                    "response": response,
                }
                raw_path.write_text(
                    json.dumps(payload, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
                con.execute(
                    """
                    update collection_tasks
                    set status = 'done',
                        finished_at = ?,
                        raw_file_path = ?,
                        error_message = null
                    where task_id = ?
                    """,
                    [finished_at, str(raw_path), task["task_id"]],
                )
                completed += 1
            except Exception as exc:
                finished_at = utc_now()
                con.execute(
                    """
                    update collection_tasks
                    set status = 'failed',
                        finished_at = ?,
                        error_message = ?
                    where task_id = ?
                    """,
                    [finished_at, str(exc)[:1000], task["task_id"]],
                )
                failed += 1
                if stop_on_failure:
                    break

            if index < len(tasks) - 1:
                time.sleep(delay)

    return {
        "selected": len(tasks),
        "completed": completed,
        "failed": failed,
    }
