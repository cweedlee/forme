#!/bin/sh
set -eu

mkdir -p /app/data/output /app/data/synced_data
chown -R app:app /app/data 2>/dev/null || true

exec gosu app "$@"
