from __future__ import annotations

from pathlib import Path

import typer

from .config import Settings, load_settings
from .db import database_summary, initialize_database
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
def plan() -> None:
    """Create collection tasks from seed queries. Not implemented yet."""
    raise typer.Exit("plan is not implemented yet")


@app.command("run-batch")
def run_batch(limit: int = typer.Option(200, help="Maximum tasks to run.")) -> None:
    """Run a resumable collection batch. Not implemented yet."""
    raise typer.Exit(f"run-batch is not implemented yet; requested limit={limit}")


@app.command("parse")
def parse() -> None:
    """Parse raw JSON into DuckDB and Parquet. Not implemented yet."""
    raise typer.Exit("parse is not implemented yet")


if __name__ == "__main__":
    app()
