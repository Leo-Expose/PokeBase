"""Download and extract the latest PokeBase data from GitHub Releases."""
import json
import os
import sys
import tarfile
import urllib.request

from tqdm import tqdm

REPO = "Leo-Expose/PokeBase"
TARGET = "/app"
DATA_DIR = os.path.join(TARGET, "data")
DB_PATH = os.path.join(DATA_DIR, "pokebase.db")
CHUNK_SIZE = 8192
PROGRESS_INTERVAL = 10 * 1024 * 1024  # report every 10 MB


def latest_asset_url() -> str | None:
    url = f"https://api.github.com/repos/{REPO}/releases/latest"
    try:
        resp = urllib.request.urlopen(url, timeout=30)
        data = json.loads(resp.read())
    except Exception as e:
        print(f"Failed to fetch release info: {e}", file=sys.stderr)
        return None

    for asset in data.get("assets", []):
        name: str = asset["name"]
        if name.endswith(".tar.gz"):
            return asset["browser_download_url"]

    print(
        "No .tar.gz asset found in latest release. "
        "Upload one via: gh release upload <tag> pokebase-data.tar.gz",
        file=sys.stderr,
    )
    return None


def download_with_progress(url: str, path: str) -> bool:
    try:
        resp = urllib.request.urlopen(url, timeout=120)
    except Exception as e:
        print(f"Connection failed: {e}", file=sys.stderr)
        return False

    total = int(resp.headers.get("Content-Length", 0))
    downloaded = 0
    last_report = 0
    try:
        with open(path, "wb") as f:
            with tqdm(
                total=total, unit="B", unit_scale=True, desc="Downloading",
                mininterval=1, file=sys.stdout, dynamic_ncols=True,
            ) as pbar:
                while chunk := resp.read(CHUNK_SIZE):
                    f.write(chunk)
                    chunk_len = len(chunk)
                    downloaded += chunk_len
                    pbar.update(chunk_len)
    except Exception as e:
        print(f"Download failed: {e}", file=sys.stderr)
        return False
    return True


def acquire_tarball() -> str | None:
    local_bundle = "/app/pokebase-data.tar.gz"
    if os.path.exists(local_bundle):
        print("Found local data bundle.")
        return local_bundle

    print("Fetching latest release info from GitHub...", flush=True)
    asset_url = latest_asset_url()
    if not asset_url:
        return None

    tarball = "/tmp/pokebase-data.tar.gz"
    if not download_with_progress(asset_url, tarball):
        return None
    return tarball


def main() -> None:
    print("PokeBase data check...", flush=True)
    sys.stdout.flush()

    if os.path.exists(DB_PATH) and os.path.getsize(DB_PATH) > 0:
        print("Data already exists, skipping download.")
        return

    tarball = acquire_tarball()
    if not tarball:
        print(
            "Could not acquire data bundle. "
            "Falling through — the app may not work without data.",
            file=sys.stderr,
        )
        return

    print("Extracting...")
    os.makedirs(DATA_DIR, exist_ok=True)
    with tarfile.open(tarball) as tf:
        tf.extractall(TARGET, filter="data")

    os.remove(tarball)

    if os.path.exists(DB_PATH):
        print(f"Data ready! ({os.path.getsize(DB_PATH) // 1024 // 1024} MB database)")
    else:
        print("Extraction completed but database not found.", file=sys.stderr)


if __name__ == "__main__":
    main()
