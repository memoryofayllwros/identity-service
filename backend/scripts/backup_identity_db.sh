#!/usr/bin/env bash
# Backup identity_db (Phase 3 ops). Requires mongodump on PATH.
set -euo pipefail

URI="${MONGODB_URI:?Set MONGODB_URI}"
DB="${IDENTITY_DATABASE_NAME:-identity_db}"
OUT="${1:-./backups/identity_$(date +%Y%m%d_%H%M%S)}"

mkdir -p "$(dirname "$OUT")"
mongodump --uri="$URI" --db="$DB" --out="$OUT"
echo "Wrote $OUT/$DB"
