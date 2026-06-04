#!/usr/bin/env bash
set -euo pipefail

docker stop pokebase 2>/dev/null || true
docker rm pokebase 2>/dev/null || true
