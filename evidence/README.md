# Miele SERP Evidence

Evidence.dev report layer for the exported Miele SERP BI marts.

This app does not read the live DuckDB warehouse. It expects CSV files copied
from:

```text
$DATA_ROOT/exports/bi/
```

into:

```text
evidence/sources/bi/
```

## Refresh data

From the repository root:

```bash
miele-wordstat export-bi
scripts/sync_evidence_sources.sh
```

## Run locally

From this directory:

```bash
npm install
npm run sources
npm run dev
```

Open:

```text
http://localhost:3000
```

## Build static report

```bash
npm run sources
npm run build
```

