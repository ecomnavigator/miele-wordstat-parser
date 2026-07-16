from __future__ import annotations

import base64
import json
from datetime import datetime
from pathlib import Path
from xml.etree import ElementTree as ET

import duckdb

from .config import Settings
from .db import initialize_database


def int_text(element: ET.Element | None) -> int | None:
    if element is None or element.text is None:
        return None
    try:
        return int(element.text)
    except ValueError:
        return None


def text_at(root: ET.Element, path: str) -> str | None:
    element = root.find(path)
    if element is None:
        return None
    text = "".join(element.itertext()).strip()
    return text or None


def parse_result_rows(
    root: ET.Element,
    *,
    task_id: str,
    query: str,
    region: int,
    fetched_at: datetime,
    source_file: str,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for position, group in enumerate(root.findall(".//results/grouping/group"), start=1):
        doc = group.find("./doc")
        if doc is None:
            continue
        rows.append(
            {
                "task_id": task_id,
                "query": query,
                "region": region,
                "fetched_at": fetched_at,
                "position": position,
                "domain": text_at(doc, "./domain"),
                "url": text_at(doc, "./url"),
                "title": text_at(doc, "./title"),
                "snippet": text_at(doc, "./passages/passage"),
                "source_file": source_file,
            }
        )
    return rows


def parse_raw_file(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    task = payload["task"]
    raw_data = payload["response"]["rawData"]
    xml = base64.b64decode(raw_data).decode("utf-8", errors="replace")
    root = ET.fromstring(xml)

    response = root.find("response")
    if response is None:
        raise ValueError(f"No response element in {path}")

    found_all = int_text(response.find("./found[@priority='all']"))
    found_phrase = int_text(response.find("./found[@priority='phrase']"))
    grouping = response.find("./results/grouping")
    found_docs_all = (
        int_text(grouping.find("./found-docs[@priority='all']"))
        if grouping is not None
        else None
    )
    found_docs_phrase = (
        int_text(grouping.find("./found-docs[@priority='phrase']"))
        if grouping is not None
        else None
    )

    task_id = task["task_id"]
    query = task["query"]
    region = int(task["region"])
    fetched_at = datetime.fromisoformat(payload["fetched_at"])
    source_file = str(path)

    return {
        "task_id": task_id,
        "query": query,
        "region": region,
        "fetched_at": fetched_at,
        "found_all": found_all,
        "found_phrase": found_phrase,
        "found_docs_all": found_docs_all,
        "found_docs_phrase": found_docs_phrase,
        "top_domain": text_at(root, ".//group/doc/domain"),
        "top_url": text_at(root, ".//group/doc/url"),
        "source_file": source_file,
        "results": parse_result_rows(
            root,
            task_id=task_id,
            query=query,
            region=region,
            fetched_at=fetched_at,
            source_file=source_file,
        ),
    }


def parse_raw_files(settings: Settings) -> dict[str, int]:
    initialize_database(settings)
    files = sorted(settings.raw_dir.glob("*/*.json"))
    parsed = 0
    failed = 0

    with duckdb.connect(str(settings.duckdb_path)) as con:
        for path in files:
            try:
                row = parse_raw_file(path)
                con.execute(
                    """
                    insert or replace into search_snapshots (
                        task_id,
                        query,
                        region,
                        fetched_at,
                        found_all,
                        found_phrase,
                        found_docs_all,
                        found_docs_phrase,
                        top_domain,
                        top_url,
                        source_file
                    )
                    values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        row["task_id"],
                        row["query"],
                        row["region"],
                        row["fetched_at"],
                        row["found_all"],
                        row["found_phrase"],
                        row["found_docs_all"],
                        row["found_docs_phrase"],
                        row["top_domain"],
                        row["top_url"],
                        row["source_file"],
                    ],
                )
                con.execute(
                    "delete from search_results where task_id = ?",
                    [row["task_id"]],
                )
                for result in row["results"]:
                    con.execute(
                        """
                        insert or replace into search_results (
                            task_id,
                            query,
                            region,
                            fetched_at,
                            position,
                            domain,
                            url,
                            title,
                            snippet,
                            source_file
                        )
                        values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        [
                            result["task_id"],
                            result["query"],
                            result["region"],
                            result["fetched_at"],
                            result["position"],
                            result["domain"],
                            result["url"],
                            result["title"],
                            result["snippet"],
                            result["source_file"],
                        ],
                    )
                parsed += 1
            except Exception:
                failed += 1

    return {
        "files": len(files),
        "parsed": parsed,
        "failed": failed,
    }
