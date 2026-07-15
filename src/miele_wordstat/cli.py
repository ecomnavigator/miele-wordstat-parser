from __future__ import annotations

from pathlib import Path

import typer

from .config import Settings, load_settings

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
    """Create local runtime directories on the configured data disk."""
    settings = load_settings()
    for path in runtime_dirs(settings):
        path.mkdir(parents=True, exist_ok=True)
        typer.echo(f"ok {path}")


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
    typer.echo(
        "yandex_search_api_key: "
        + ("configured" if settings.yandex_search_api_key else "missing")
    )


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
