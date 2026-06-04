#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

echo "=== PokeBase Release Data Packer ==="
echo ""

# Ensure virtualenv is active if it exists
if [ -d venv ] && [ -z "${VIRTUAL_ENV:-}" ]; then
    echo "Activating venv..."
    # shellcheck disable=SC1091
    source venv/bin/activate
fi

# Fetch latest data if needed
if [ ! -f data/pokebase.db ]; then
    echo "Fetching Pokémon data from PokeAPI..."
    python fetch_data.py
else
    echo "Database already exists at data/pokebase.db (skipping fetch)"
fi

# Fetch sprites if needed
sprite_count=$(find static/sprites -maxdepth 1 -name '*.png' 2>/dev/null | wc -l)
if [ "$sprite_count" -lt 100 ]; then
    echo "Fetching sprites from PokeAPI..."
    python fetch_sprites.py
else
    echo "Sprites already downloaded ($sprite_count files, skipping fetch)"
fi

# Create tarball
echo ""
echo "Creating pokebase-data.tar.gz..."
tar czf pokebase-data.tar.gz data/ static/sprites/

echo ""
echo "=== Done! ==="
echo "Created: $(du -h pokebase-data.tar.gz | cut -f1)"
echo ""
echo "Upload to GitHub Releases:"
echo "  gh release create <tag> pokebase-data.tar.gz --notes '<description>'"
echo ""
echo "Or update an existing release:"
echo "  gh release upload <tag> pokebase-data.tar.gz --clobber"
