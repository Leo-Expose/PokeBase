# PokeBase

A self-hosted Pokédex application covering Pokémon through Gen 9.  
Data fetched from [PokeAPI](https://pokeapi.co/) and sprites from [PokeAPI/sprites](https://github.com/PokeAPI/sprites).

## Quick Start (Docker)

```bash
docker compose up --build
```

Visit [http://localhost:5000](http://localhost:5000).

On first start, the container downloads the Pokémon database and sprites from the
[latest GitHub Release](https://github.com/Leo-Expose/PokeBase/releases) and
extracts them into named volumes. Subsequent starts are instant.

## Running Without Docker

```bash
pip install -r requirements.txt
python fetch_data.py    # pulls from PokeAPI (~5-10 min)
python fetch_sprites.py # downloads sprites (~2-5 min)
python app.py
```

## Refreshing the Data

When new games or Pokémon are released, update the data and publish a new release:

```bash
git checkout dev
python fetch_data.py && python fetch_sprites.py
bash scripts/prepare-release.sh            # creates pokebase-data.tar.gz
gh release upload v1.0.0 pokebase-data.tar.gz --clobber
```

Then rebuild containers — they pull the latest release on first start.

## Branches

| Branch | Contains data? | Use |
|--------|---------------|-----|
| `master` | No | Lightweight clone, Docker-friendly |
| `dev` | Yes (DB + sprites) | Development, data refreshes |
