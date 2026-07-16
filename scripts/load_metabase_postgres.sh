#!/usr/bin/env bash
set -euo pipefail

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.metabase.yml}"
POSTGRES_SERVICE="${POSTGRES_SERVICE:-postgres}"
POSTGRES_DB="${POSTGRES_DB:-miele_bi}"
POSTGRES_USER="${POSTGRES_USER:-miele}"
BI_DIR="${BI_DIR:-${DATA_ROOT:-/home/maksim/miele-data}/exports/bi}"

required_files=(
  queries.csv
  search_snapshots.csv
  organic_positions.csv
  domain_visibility.csv
  competitors_by_super_intent.csv
)

for file in "${required_files[@]}"; do
  if [[ ! -f "$BI_DIR/$file" ]]; then
    echo "Missing $BI_DIR/$file. Run: miele-wordstat export-bi" >&2
    exit 1
  fi
done

docker compose -f "$COMPOSE_FILE" up -d "$POSTGRES_SERVICE"

docker compose -f "$COMPOSE_FILE" exec -T "$POSTGRES_SERVICE" \
  psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" <<'SQL'
create table if not exists queries (
  query_id text,
  query text,
  normalized_query text,
  category text,
  intent text,
  super_intent text,
  product_type text,
  source text,
  first_seen_at timestamptz
);

create table if not exists search_snapshots (
  task_id text,
  query text,
  category text,
  intent text,
  super_intent text,
  region text,
  fetched_at timestamptz,
  result_count bigint,
  found_all bigint,
  found_phrase bigint,
  found_docs_all bigint,
  found_docs_phrase bigint,
  top_domain text,
  top_url text,
  normalized_top_domain text,
  top_competitor_type text
);

create table if not exists organic_positions (
  task_id text,
  query text,
  category text,
  intent text,
  super_intent text,
  region text,
  fetched_at timestamptz,
  position integer,
  domain text,
  url text,
  title text,
  snippet text,
  normalized_domain text,
  competitor_type text
);

create table if not exists domain_visibility (
  normalized_domain text,
  competitor_type text,
  top10_appearances bigint,
  unique_queries bigint,
  best_position integer,
  avg_position double precision,
  top3_appearances bigint,
  position1_appearances bigint
);

create table if not exists competitors_by_super_intent (
  super_intent text,
  normalized_domain text,
  competitor_type text,
  top10_appearances bigint,
  unique_queries bigint,
  top3_appearances bigint,
  position1_appearances bigint,
  best_position integer,
  avg_position double precision
);

truncate table
  queries,
  search_snapshots,
  organic_positions,
  domain_visibility,
  competitors_by_super_intent;

\copy queries from '/exports/bi/queries.csv' with (format csv, header true)
\copy search_snapshots from '/exports/bi/search_snapshots.csv' with (format csv, header true)
\copy organic_positions from '/exports/bi/organic_positions.csv' with (format csv, header true)
\copy domain_visibility from '/exports/bi/domain_visibility.csv' with (format csv, header true)
\copy competitors_by_super_intent from '/exports/bi/competitors_by_super_intent.csv' with (format csv, header true)

create index if not exists idx_queries_query on queries (query);
create index if not exists idx_snapshots_query on search_snapshots (query);
create index if not exists idx_organic_query_position on organic_positions (query, position);
create index if not exists idx_organic_domain on organic_positions (normalized_domain);
create index if not exists idx_domain_visibility_domain on domain_visibility (normalized_domain);
SQL

docker compose -f "$COMPOSE_FILE" exec -T "$POSTGRES_SERVICE" \
  psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  -c "select 'queries' as table_name, count(*) from queries union all select 'search_snapshots', count(*) from search_snapshots union all select 'organic_positions', count(*) from organic_positions union all select 'domain_visibility', count(*) from domain_visibility union all select 'competitors_by_super_intent', count(*) from competitors_by_super_intent order by table_name;"
