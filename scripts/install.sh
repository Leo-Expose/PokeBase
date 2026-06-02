#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

MIN_PYTHON="3.9"
VENV_DIR="venv"
DB_DIR="data"
DB_PATH="$DB_DIR/pokebase.db"
S3_BUCKET="${S3_BUCKET:-}"

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

# ── Database ──────────────────────────────────────────────────────────────────
mkdir -p "$DB_DIR"

if [ -f "$DB_PATH" ]; then
    log "Database already exists at $DB_PATH"
elif [ -n "$S3_BUCKET" ]; then
    log "Downloading database from S3..."
    if aws s3 cp "s3://$S3_BUCKET/data/pokebase.db" "$DB_PATH" 2>/dev/null; then
        log "Database downloaded from S3"
    else
        log "No database in S3, fetching from PokeAPI (slow, first run)..."
        python fetch_data.py
        log "Caching database to S3 for future runs..."
        aws s3 cp "$DB_PATH" "s3://$S3_BUCKET/data/pokebase.db" --quiet || true
    fi
else
    log "Fetching Pokémon data from PokeAPI (slow, first run)..."
    python fetch_data.py
fi

# ── Sprite directories ────────────────────────────────────────────────────────
mkdir -p static/sprites

# ── Sprites ───────────────────────────────────────────────────────────────────
if [ -d "static/sprites" ] && [ "$(ls -A static/sprites 2>/dev/null)" ]; then
    log "Sprites already downloaded"
elif [ -n "$S3_BUCKET" ]; then
    log "Checking S3 for sprites..."
    if aws s3 ls "s3://$S3_BUCKET/static/sprites/" 2>/dev/null | grep -q .; then
        log "Downloading sprites from S3..."
        aws s3 sync "s3://$S3_BUCKET/static/sprites/" "static/sprites/" --quiet
        log "Sprites downloaded from S3"
    else
        log "No sprites in S3, downloading from PokeAPI (slow, first run)..."
        python fetch_sprites.py
        log "Caching sprites to S3 for future runs..."
        aws s3 sync "static/sprites/" "s3://$S3_BUCKET/static/sprites/" --quiet || log "WARNING: Failed to cache sprites to S3"
    fi
else
    log "Downloading Pokémon sprites from PokeAPI (slow, first run)..."
    python fetch_sprites.py
fi

log "Install complete!"
