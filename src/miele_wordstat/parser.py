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
    if element is None or element.text is None:
        return None
    return element.text


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

    return {
        "task_id": task["task_id"],
        "query": task["query"],
        "region": int(task["region"]),
        "fetched_at": datetime.fromisoformat(payload["fetched_at"]),
        "found_all": found_all,
        "found_phrase": found_phrase,
        "found_docs_all": found_docs_all,
        "found_docs_phrase": found_docs_phrase,
        "top_domain": text_at(root, ".//group/doc/domain"),
        "top_url": text_at(root, ".//group/doc/url"),
        "source_file": str(path),
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
                parsed += 1
            except Exception:
                failed += 1

    return {
        "files": len(files),
        "parsed": parsed,
        "failed": failed,
    }
