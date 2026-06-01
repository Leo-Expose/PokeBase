#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

MIN_PYTHON="3.9"
VENV_DIR="venv"
DB_DIR="data"
DB_PATH="$DB_DIR/pokebase.db"

log()  { echo "==> $*"; }
err()  { echo "ERROR: $*" >&2; exit 1; }

# Check Python version
PYTHON=$(command -v python3 || command -v python || err "Python not found")
PY_VER=$("$PYTHON" --version 2>&1 | grep -oP '\d+\.\d+')
if [[ "$(printf '%s\n' "$MIN_PYTHON" "$PY_VER" | sort -V | head -1)" != "$MIN_PYTHON" ]]; then
    err "Python $MIN_PYTHON+ required, found $PY_VER"
fi
log "Python $PY_VER found"

# Virtual environment
if [ -d "$VENV_DIR" ]; then
    log "Virtual environment already exists at $VENV_DIR"
else
    log "Creating virtual environment..."
    "$PYTHON" -m venv "$VENV_DIR"
fi
source "$VENV_DIR/bin/activate"

# Install dependencies
log "Installing Python dependencies..."
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

# Data directory
mkdir -p "$DB_DIR"

# Database and data fetch
if [ -f "$DB_PATH" ]; then
    log "Database already exists at $DB_PATH"
else
    log "Fetching Pokémon data from PokeAPI..."
    python fetch_data.py
fi

# Sprites
if [ -d "static/sprites" ] && [ "$(ls -A static/sprites 2>/dev/null)" ]; then
    log "Sprites already downloaded"
else
    log "Downloading Pokémon sprites..."
    python fetch_sprites.py
fi

log "Install complete! Run 'python app.py' to start."
