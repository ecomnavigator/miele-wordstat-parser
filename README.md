# miele-wordstat-parser

Local pipeline for buying out and preserving Yandex Wordstat history for the
Miele semantic core.

The intended setup is:

```text
GitHub repo = code
Debian laptop = 24/7 worker
External SSD = raw data, DuckDB, Parquet, exports
Streamlit = local BI dashboard
```

## Layout

```text
configs/                  Runtime defaults
dashboards/               Streamlit dashboard
scripts/                  Debian helper scripts
sql/                      DuckDB schema and views
src/miele_wordstat/       Python package
```

Runtime data should live outside the repository, for example:

```text
/mnt/miele-ssd/miele-data/
  raw/yandex_wordstat/
  warehouse/duckdb/
  warehouse/parquet/
  exports/
  logs/
  state/
  backups/
```

For the first laptop-only phase, use the same layout on the internal disk:

```env
DATA_ROOT=/home/maksim/miele-data
```

When a separate SSD is added later, move that directory and update `DATA_ROOT`
in the local `.env`.

## First setup on Debian

```bash
sudo apt update
sudo apt install -y git python3 python3-venv python3-pip

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .

cp .env.example .env
```

Edit `.env` locally. Do not commit it.

```env
DATA_ROOT=/mnt/miele-ssd/miele-data
YANDEX_SEARCH_API_KEY=...
YANDEX_FOLDER_ID=...
```

Initialize local data folders:

```bash
python -m miele_wordstat.cli init
python -m miele_wordstat.cli status
```

or:

```bash
miele-wordstat init
miele-wordstat status
```

## Collector shape

The collector is designed to be resumable:

```text
plan tasks -> run batches -> save raw JSON -> parse to DuckDB/Parquet -> dashboard
```

Planned commands:

```bash
miele-wordstat smoke-test --query "miele"
miele-wordstat plan
miele-wordstat run-batch --limit 50
python -m miele_wordstat.cli parse
python -m miele_wordstat.cli status
```

Current implementation:

- `init` creates runtime folders and initializes the DuckDB schema.
- `status` prints local runtime configuration.
- `smoke-test` validates Yandex Search API credentials with one small request.
- `plan` loads `seeds/miele_queries.csv` into DuckDB collection tasks.
- `run-batch` executes pending web search tasks and stores raw JSON responses.
- `parse` decodes saved Search API XML and stores snapshots for the dashboard.

For a conservative API limit probe:

```bash
miele-wordstat generate-probe-seeds --limit 120
miele-wordstat plan --seed-file seeds/miele_probe_queries.csv
miele-wordstat run-batch --limit 120 --stop-on-failure
miele-wordstat parse
```

## BI export and Metabase

Streamlit remains the operational dashboard. Metabase can be used as a second
BI layer over exported, read-only data so it does not lock the DuckDB warehouse.

After collection and parsing finish:

```bash
miele-wordstat export-bi
```

This writes CSV marts to:

```text
$DATA_ROOT/exports/bi/
  queries.csv
  search_snapshots.csv
  organic_positions.csv
  domain_visibility.csv
  competitors_by_super_intent.csv
```

Start Metabase:

```bash
docker compose -f docker-compose.metabase.yml up -d
```

Open:

```text
http://localhost:3000
```

The compose file mounts `$DATA_ROOT/exports/bi` read-only at `/exports/bi`.
