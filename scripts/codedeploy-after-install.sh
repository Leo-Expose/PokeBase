#!/usr/bin/env bash
set -euo pipefail

cd /home/ubuntu/PokeBase

chmod -R +x scripts/*.sh
sudo chown -R ubuntu:ubuntu /home/ubuntu/PokeBase 2>/dev/null || true

if [ ! -d venv ]; then
    python3 -m venv venv
fi
source venv/bin/activate
pip install --quiet -r requirements.txt

mkdir -p data static/sprites
