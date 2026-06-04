#!/usr/bin/env bash
set -euo pipefail

cd /home/ubuntu/PokeBase

chmod -R +x scripts/*.sh
chown -R ubuntu:ubuntu /home/ubuntu/PokeBase

if [ ! -d venv ]; then
    sudo -u ubuntu python3 -m venv venv
fi
sudo -u ubuntu bash -c "source venv/bin/activate && pip install --quiet -r requirements.txt"

mkdir -p data static/sprites
