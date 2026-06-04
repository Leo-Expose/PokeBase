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
