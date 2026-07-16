from __future__ import annotations

from pathlib import Path

import duckdb
import typer

from .collector import run_batch as run_collection_batch
from .config import Settings, load_settings
from .db import database_summary, initialize_database
from .parser import parse_raw_files
from .planner import plan_from_seed_file
from .seed_generator import generate_probe_seed_file
from .yandex_client import YandexSearchApiError, YandexWordstatClient

app = typer.Typer(help="Local Miele Wordstat collection pipeline.")


def runtime_dirs(settings: Settings) -> list[Path]:
    return [
        settings.raw_dir,
        settings.duckdb_path.parent,
        settings.parquet_dir,
        settings.exports_dir / "csv",
        settings.exports_dir / "excel",
        settings.logs_dir / "collector",
        settings.state_dir,
        settings.backups_dir,
    ]


@app.command()
def init() -> None:
    """Create runtime directories and initialize the local DuckDB schema."""
    settings = load_settings()
    for path in runtime_dirs(settings):
        path.mkdir(parents=True, exist_ok=True)
        typer.echo(f"ok {path}")
    initialize_database(settings)
    typer.echo(f"ok {settings.duckdb_path}")


@app.command()
def status() -> None:
    """Print the current local runtime configuration."""
    settings = load_settings()
    typer.echo(f"data_root: {settings.data_root}")
    typer.echo(f"raw_dir: {settings.raw_dir}")
    typer.echo(f"duckdb_path: {settings.duckdb_path}")
    typer.echo(f"parquet_dir: {settings.parquet_dir}")
    typer.echo(f"default_region: {settings.default_region}")
    typer.echo(f"max_requests_per_batch: {settings.max_requests_per_batch}")
    summary = database_summary(settings)
    if summary["exists"]:
        typer.echo(
            f"duckdb_schema: {summary['tables']} tables, {summary['views']} views"
        )
    else:
        typer.echo("duckdb_schema: missing")
    typer.echo(
        "yandex_search_api_key: "
        + ("configured" if settings.yandex_search_api_key else "missing")
    )


@app.command("smoke-test")
def smoke_test(
    query: str = typer.Option("miele", help="Search query for the API smoke test."),
    region: int | None = typer.Option(None, help="Yandex region ID."),
) -> None:
    """Run one small Yandex Search API request to validate credentials."""
    settings = load_settings()
    if not settings.yandex_search_api_key:
        raise typer.BadParameter("YANDEX_SEARCH_API_KEY is missing")
    if not settings.yandex_folder_id:
        raise typer.BadParameter("YANDEX_FOLDER_ID is missing")

    client = YandexWordstatClient(
        api_key=settings.yandex_search_api_key,
        folder_id=settings.yandex_folder_id,
    )
    try:
        result = client.web_search(
            query=query,
            region=region or settings.default_region,
            groups_on_page=1,
            docs_in_group=1,
        )
    except YandexSearchApiError as exc:
        typer.echo(f"api_status: failed")
        typer.echo(str(exc))
        raise typer.Exit(1) from exc

    raw_data = result.get("rawData", "")
    typer.echo("api_status: ok")
    typer.echo(f"query: {query}")
    typer.echo(f"region: {region or settings.default_region}")
    typer.echo(f"raw_data_bytes: {len(raw_data)}")


@app.command("plan")
def plan(
    seed_file: Path = typer.Option(
        Path("seeds/miele_queries.csv"),
        help="CSV file with query, category, and optional region columns.",
    ),
) -> None:
    """Create collection tasks from seed queries."""
    settings = load_settings()
    if not seed_file.exists():
        raise typer.BadParameter(f"Seed file does not exist: {seed_file}")
    result = plan_from_seed_file(settings, seed_file)
    typer.echo(f"seed_rows: {result['seed_rows']}")
    typer.echo(f"inserted_queries: {result['inserted_queries']}")
    typer.echo(f"inserted_tasks: {result['inserted_tasks']}")


@app.command("run-batch")
def run_batch(
    limit: int = typer.Option(200, help="Maximum tasks to run."),
    stop_on_failure: bool = typer.Option(
        False,
        help="Stop after the first failed API task.",
    ),
    progress_every: int = typer.Option(
        25,
        help="Print progress every N processed tasks. Set 0 to disable.",
    ),
) -> None:
    """Run a resumable collection batch."""
    settings = load_settings()

    def print_progress(progress: dict[str, int]) -> None:
        processed = progress["processed"]
        selected = progress["selected"]
        if progress_every <= 0:
            return
        if processed == 1 or processed == selected or processed % progress_every == 0:
            typer.echo(
                "progress: "
                f"{processed}/{selected} "
                f"completed={progress['completed']} "
                f"failed={progress['failed']}"
            )

    try:
        result = run_collection_batch(
            settings,
            limit=limit,
            stop_on_failure=stop_on_failure,
            progress_callback=print_progress,
        )
    except YandexSearchApiError as exc:
        typer.echo(str(exc))
        raise typer.Exit(1) from exc
    typer.echo(f"selected: {result['selected']}")
    typer.echo(f"completed: {result['completed']}")
    typer.echo(f"failed: {result['failed']}")


@app.command("requeue-done")
def requeue_done(
    limit: int = typer.Option(200, help="Maximum completed tasks to requeue."),
) -> None:
    """Mark completed web search tasks as pending for recollection."""
    settings = load_settings()
    initialize_database(settings)
    with duckdb.connect(str(settings.duckdb_path)) as con:
        task_ids = [
            row[0]
            for row in con.execute(
                """
                select task_id
                from collection_tasks
                where status = 'done'
                  and method = 'web_search'
                order by finished_at desc nulls last, task_id
                limit ?
                """,
                [limit],
            ).fetchall()
        ]
        if task_ids:
            placeholders = ",".join(["?"] * len(task_ids))
            con.execute(
                f"""
                update collection_tasks
                set status = 'pending',
                    started_at = null,
                    finished_at = null,
                    error_message = null
                where task_id in ({placeholders})
                """,
                task_ids,
            )
    typer.echo(f"requeued: {len(task_ids)}")


@app.command("generate-probe-seeds")
def generate_probe_seeds(
    output: Path = typer.Option(
        Path("seeds/miele_probe_queries.csv"),
        help="Output CSV path.",
    ),
    limit: int = typer.Option(120, help="Maximum generated seed rows."),
    region: int | None = typer.Option(None, help="Yandex region ID."),
) -> None:
    """Generate a broader Miele seed list for API limit probing."""
    settings = load_settings()
    rows = generate_probe_seed_file(output, limit, region or settings.default_region)
    typer.echo(f"generated_rows: {rows}")
    typer.echo(f"output: {output}")


@app.command("parse")
def parse() -> None:
    """Parse raw JSON/XML responses into DuckDB."""
    settings = load_settings()
    result = parse_raw_files(settings)
    typer.echo(f"files: {result['files']}")
    typer.echo(f"parsed: {result['parsed']}")
    typer.echo(f"failed: {result['failed']}")


if __name__ == "__main__":
    app()
