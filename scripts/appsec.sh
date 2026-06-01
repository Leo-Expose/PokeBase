#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

log()   { echo "==> $*"; }
err()   { echo "ERROR: $*" >&2; }
fail()  { err "$@"; exit 1; }

PYTHON=$(command -v python3 || command -v python || fail "Python not found")
PIP=$(command -v pip3 || command -v pip || fail "pip not found")

log "Installing security tools..."
"$PIP" install --quiet --upgrade pip-audit bandit 2>/dev/null

HAD_FAILURE=0

# ── Dependency audit ──────────────────────────────────────────────────────────
log "Running pip-audit on requirements.txt..."
if [ -f requirements.txt ]; then
    if pip-audit --requirement requirements.txt; then
        log "pip-audit: no vulnerabilities found"
    else
        err "pip-audit: vulnerabilities detected"
        HAD_FAILURE=1
    fi
else
    err "requirements.txt not found"
    HAD_FAILURE=1
fi

# ── Code scan ─────────────────────────────────────────────────────────────────
log "Running bandit on Python files..."
    if bandit -r . --quiet --exclude "venv/,__pycache__/,.git/" 2>/dev/null; then
    log "bandit: no issues found"
else
    err "bandit: security issues detected"
    HAD_FAILURE=1
fi

# ── Exit ──────────────────────────────────────────────────────────────────────
if [ "$HAD_FAILURE" -eq 1 ]; then
    err "Appsec checks failed"
    exit 1
fi

log "All appsec checks passed"
