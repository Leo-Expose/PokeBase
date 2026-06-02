#!/usr/bin/env bash
set -euo pipefail

cd /home/ubuntu/PokeBase

if [ ! -d venv ]; then
    python3 -m venv venv
fi
source venv/bin/activate
pip install --quiet -r requirements.txt

mkdir -p data static/sprites
