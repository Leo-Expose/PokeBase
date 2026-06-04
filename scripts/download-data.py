"""Download and extract the latest PokeBase data from GitHub Releases."""
import json
import os
import sys
import tarfile
import urllib.request

REPO = "Leo-Expose/PokeBase"
TARGET = "/app"
DATA_DIR = os.path.join(TARGET, "data")
DB_PATH = os.path.join(DATA_DIR, "pokebase.db")


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


def acquire_tarball() -> str | None:
    local_bundle = "/app/pokebase-data.tar.gz"
    if os.path.exists(local_bundle):
        print("Found local data bundle.")
        return local_bundle

    asset_url = latest_asset_url()
    if not asset_url:
        return None

    tarball = "/tmp/pokebase-data.tar.gz"
    print(f"Downloading {asset_url}...")
    try:
        urllib.request.urlretrieve(asset_url, tarball)
    except Exception as e:
        print(f"Download failed: {e}", file=sys.stderr)
        return None
    return tarball


def main() -> None:
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
