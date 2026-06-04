#!/usr/bin/env bash
set -euo pipefail

sudo systemctl daemon-reload
sudo systemctl restart pokebase
