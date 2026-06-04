#!/bin/sh
set -e

python3 scripts/download-data.py

exec "$@"
