#!/bin/sh
set -e

if [ ! -f data/pokebase.db ]; then
    echo "========================================================================="
    echo " WARNING: pokebase.db not found!"
    echo ""
    echo " This image expects the Pokémon database to be bundled during build."
    echo " To build with data, check out the 'dev' branch which tracks the"
    echo " pre-fetched database and sprites:"
    echo ""
    echo "   git checkout dev"
    echo "   docker build -t pokebase ."
    echo ""
    echo " Alternatively, fetch the data at runtime (will take a long time):"
    echo "   python fetch_data.py && python fetch_sprites.py"
    echo "========================================================================="
    exit 1
fi

exec "$@"
