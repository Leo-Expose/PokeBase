#!/usr/bin/env python3
"""
fetch_sprites.py — Download sprites from PokeAPI GitHub sprites repo.
Skips files that already exist on disk.
Uses concurrent downloads with retry logic for resilience.
Run AFTER fetch_data.py or fetch_data_fast.py.
"""

import sqlite3, requests, os
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

DB_PATH = "data/pokebase.db"
SPRITE_BASE = "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon"
ARTWORK_BASE = f"{SPRITE_BASE}/other/official-artwork"
MAX_WORKERS = 8
MAX_RETRIES = 3

session = requests.Session()
adapter = requests.adapters.HTTPAdapter(
    max_retries=3, pool_connections=12, pool_maxsize=12
)
session.mount('https://', adapter)
session.mount('http://', adapter)


def download(url, path):
    """Download a single file if it doesn't already exist."""
    if os.path.exists(path) and os.path.getsize(path) > 0:
        return "skip"
    for attempt in range(MAX_RETRIES):
        try:
            r = session.get(url, timeout=30)
            if r.status_code == 200 and len(r.content) > 100:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "wb") as f:
                    f.write(r.content)
                return "ok"
            elif r.status_code == 404:
                return "404"
        except Exception:
            if attempt < MAX_RETRIES - 1:
                import time
                time.sleep(0.5)
                continue
            return "fail"
    return "fail"


def download_job(args):
    """Worker function for thread pool."""
    url, path = args
    return download(url, path)


if __name__ == "__main__":
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("SELECT id, name FROM pokemon ORDER BY id").fetchall()
    conn.close()

    # Build download queue — skip files that already exist
    jobs = []
    for pid, name in rows:
        # Default front sprite (small pixel art)
        jobs.append((f"{SPRITE_BASE}/{pid}.png", f"static/sprites/{pid}.png"))
        # Also save by name for evolution chain lookups
        jobs.append((f"{SPRITE_BASE}/{pid}.png", f"static/sprites/{name}.png"))
        # Shiny variant
        jobs.append((f"{SPRITE_BASE}/shiny/{pid}.png", f"static/sprites/shiny/{pid}.png"))
        # Official artwork (large, high quality)
        jobs.append((f"{ARTWORK_BASE}/{pid}.png", f"static/sprites/official-artwork/{pid}.png"))
        # Shiny Official artwork
        jobs.append((f"{ARTWORK_BASE}/shiny/{pid}.png", f"static/sprites/official-artwork/shiny/{pid}.png"))

    # Filter out already-downloaded files
    pending = [(url, path) for url, path in jobs if not (os.path.exists(path) and os.path.getsize(path) > 0)]
    total_skipped = len(jobs) - len(pending)

    print(f"Sprites for {len(rows)} Pokémon ({len(jobs)} total files)")
    print(f"  Already downloaded: {total_skipped}")
    print(f"  Remaining: {len(pending)}")

    if not pending:
        print("Nothing to download — all sprites present!")
        exit(0)

    stats = {"ok": 0, "skip": 0, "404": 0, "fail": 0}

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(download_job, job): job for job in pending}
        for future in tqdm(as_completed(futures), total=len(futures), desc="Downloading"):
            result = future.result()
            stats[result] = stats.get(result, 0) + 1

    print(f"\nDone! Downloaded: {stats['ok']}, Skipped: {total_skipped + stats['skip']}, "
          f"Not found: {stats['404']}, Failed: {stats['fail']}")
