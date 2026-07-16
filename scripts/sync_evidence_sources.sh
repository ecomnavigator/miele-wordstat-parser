#!/usr/bin/env bash
set -euo pipefail

DATA_ROOT="${DATA_ROOT:-/home/maksim/miele-data}"
BI_EXPORT_DIR="${BI_EXPORT_DIR:-$DATA_ROOT/exports/bi}"
EVIDENCE_SOURCE_DIR="${EVIDENCE_SOURCE_DIR:-evidence/sources/bi}"

if [[ ! -d "$BI_EXPORT_DIR" ]]; then
  echo "BI export directory does not exist: $BI_EXPORT_DIR" >&2
  echo "Run: miele-wordstat export-bi" >&2
  exit 1
fi

mkdir -p "$EVIDENCE_SOURCE_DIR"
cp "$BI_EXPORT_DIR"/*.csv "$EVIDENCE_SOURCE_DIR"/

echo "Synced Evidence CSV sources:"
ls -1 "$EVIDENCE_SOURCE_DIR"/*.csv

