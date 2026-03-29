#!/usr/bin/env python3
"""
fetch_data_fast.py — Optimized concurrent PokeAPI fetcher
Uses ThreadPoolExecutor for parallel requests.
Skips already-fetched data. Runs 5-10x faster than sequential fetch.
Run: python fetch_data_fast.py
"""

import sqlite3, requests, time, json, os, sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

BASE_URL = "https://pokeapi.co/api/v2"
DB_PATH = "data/pokebase.db"
MAX_WORKERS = 5  # Concurrent requests (be respectful to PokeAPI)
DELAY = 0.1  # Short delay per request

session = requests.Session()
adapter = requests.adapters.HTTPAdapter(max_retries=3, pool_connections=10, pool_maxsize=10)
session.mount('https://', adapter)
session.mount('http://', adapter)

def fetch(endpoint, retries=3):
    url = f"{BASE_URL}/{endpoint}" if not endpoint.startswith("http") else endpoint
    for attempt in range(retries):
        try:
            r = session.get(url, timeout=30)
            r.raise_for_status()
            time.sleep(DELAY)
            return r.json()
        except Exception as e:
            if attempt == retries - 1:
                return None
            time.sleep(1)

def create_schema(conn):
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS pokemon (
        id INTEGER PRIMARY KEY, name TEXT NOT NULL,
        base_experience INTEGER, height INTEGER, weight INTEGER,
        is_default BOOLEAN, species_id INTEGER
    );
    CREATE TABLE IF NOT EXISTS species (
        id INTEGER PRIMARY KEY, name TEXT NOT NULL, flavor_text TEXT,
        genus TEXT, generation_id INTEGER, generation_name TEXT,
        legendary BOOLEAN, mythical BOOLEAN, capture_rate INTEGER,
        base_happiness INTEGER, growth_rate TEXT, egg_groups TEXT,
        evolution_chain_id INTEGER, evolves_from TEXT,
        color TEXT, shape TEXT, region TEXT
    );
    CREATE TABLE IF NOT EXISTS pokemon_types (
        pokemon_id INTEGER, slot INTEGER, type_name TEXT,
        PRIMARY KEY (pokemon_id, slot)
    );
    CREATE TABLE IF NOT EXISTS pokemon_stats (
        pokemon_id INTEGER, stat_name TEXT, base_stat INTEGER,
        effort INTEGER, PRIMARY KEY (pokemon_id, stat_name)
    );
    CREATE TABLE IF NOT EXISTS pokemon_abilities (
        pokemon_id INTEGER, ability_name TEXT, is_hidden BOOLEAN,
        slot INTEGER, flavor_text TEXT, PRIMARY KEY (pokemon_id, slot)
    );
    CREATE TABLE IF NOT EXISTS pokemon_sprites (
        pokemon_id INTEGER PRIMARY KEY, front_default TEXT,
        front_shiny TEXT, front_female TEXT,
        official_artwork TEXT, official_artwork_shiny TEXT
    );
    CREATE TABLE IF NOT EXISTS moves (
        id INTEGER PRIMARY KEY, name TEXT NOT NULL, type_name TEXT,
        damage_class TEXT, power INTEGER, accuracy INTEGER,
        pp INTEGER, priority INTEGER, effect_chance INTEGER,
        short_effect TEXT
    );
    CREATE TABLE IF NOT EXISTS pokemon_moves (
        pokemon_id INTEGER, move_id INTEGER, version_group TEXT,
        learn_method TEXT, level_learned INTEGER,
        PRIMARY KEY (pokemon_id, move_id, version_group, learn_method)
    );
    CREATE TABLE IF NOT EXISTS evolutions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        from_species TEXT, to_species TEXT, trigger TEXT,
        min_level INTEGER, item TEXT, held_item TEXT,
        known_move TEXT, min_happiness INTEGER, time_of_day TEXT,
        min_affection INTEGER, needs_overworld_rain BOOLEAN,
        gender INTEGER, location TEXT
    );
    CREATE TABLE IF NOT EXISTS forms (
        id INTEGER PRIMARY KEY, pokemon_id INTEGER, name TEXT,
        form_name TEXT, is_default BOOLEAN, is_mega BOOLEAN,
        is_gmax BOOLEAN, is_regional BOOLEAN, region TEXT
    );
    CREATE TABLE IF NOT EXISTS encounters (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pokemon_id INTEGER, location TEXT, version TEXT,
        method TEXT, min_level INTEGER, max_level INTEGER,
        chance INTEGER
    );
    """)
    conn.commit()

def store_pokemon(conn, data):
    pid = data["id"]
    conn.execute("""
        INSERT OR REPLACE INTO pokemon
        (id, name, base_experience, height, weight, is_default, species_id)
        VALUES (?,?,?,?,?,?,?)
    """, (pid, data["name"], data.get("base_experience"),
          data.get("height"), data.get("weight"),
          data.get("is_default", True),
          int(data["species"]["url"].split("/")[-2])))

    for t in data.get("types", []):
        conn.execute("INSERT OR REPLACE INTO pokemon_types (pokemon_id, slot, type_name) VALUES (?,?,?)",
                     (pid, t["slot"], t["type"]["name"]))
    for s in data.get("stats", []):
        conn.execute("INSERT OR REPLACE INTO pokemon_stats (pokemon_id, stat_name, base_stat, effort) VALUES (?,?,?,?)",
                     (pid, s["stat"]["name"], s["base_stat"], s["effort"]))

    sp = data.get("sprites", {})
    other = sp.get("other", {})
    artwork = other.get("official-artwork", {})
    conn.execute("""
        INSERT OR REPLACE INTO pokemon_sprites
        (pokemon_id, front_default, front_shiny, front_female, official_artwork, official_artwork_shiny)
        VALUES (?,?,?,?,?,?)
    """, (pid, sp.get("front_default"), sp.get("front_shiny"), sp.get("front_female"),
          artwork.get("front_default"), artwork.get("front_shiny")))

    for pm in data.get("moves", []):
        move_id = int(pm["move"]["url"].split("/")[-2])
        for vgd in pm.get("version_group_details", []):
            conn.execute("""
                INSERT OR REPLACE INTO pokemon_moves
                (pokemon_id, move_id, version_group, learn_method, level_learned) VALUES (?,?,?,?,?)
            """, (pid, move_id, vgd["version_group"]["name"],
                  vgd["move_learn_method"]["name"], vgd.get("level_learned_at", 0)))

def store_abilities(conn, pokemon_data):
    pid = pokemon_data["id"]
    for pa in pokemon_data.get("abilities", []):
        ability_url = pa["ability"]["url"]
        adata = fetch(ability_url)
        if not adata:
            continue
        flavor = ""
        for fte in reversed(adata.get("flavor_text_entries", [])):
            if fte["language"]["name"] == "en":
                flavor = fte["flavor_text"].replace("\n", " ").replace("\f", " ")
                break
        name_en = pa["ability"]["name"]
        for an in adata.get("names", []):
            if an["language"]["name"] == "en":
                name_en = an["name"]
                break
        conn.execute("""
            INSERT OR REPLACE INTO pokemon_abilities
            (pokemon_id, ability_name, is_hidden, slot, flavor_text) VALUES (?,?,?,?,?)
        """, (pid, name_en, pa["is_hidden"], pa["slot"], flavor))

def store_species(conn, data):
    sid = data["id"]
    flavor = ""
    for ft in reversed(data.get("flavor_text_entries", [])):
        if ft["language"]["name"] == "en":
            flavor = ft["flavor_text"].replace("\n", " ").replace("\f", " ")
            break
    genus = ""
    for g in data.get("genera", []):
        if g["language"]["name"] == "en":
            genus = g["genus"]
            break
    egg_groups = json.dumps([eg["name"] for eg in data.get("egg_groups", [])])
    gen_name = data.get("generation", {}).get("name", "")
    gen_id = int(data["generation"]["url"].split("/")[-2]) if data.get("generation") else 0
    evo_chain_id = int(data["evolution_chain"]["url"].split("/")[-2]) if data.get("evolution_chain") else None
    evolves_from = data["evolves_from_species"]["name"] if data.get("evolves_from_species") else None

    conn.execute("""
        INSERT OR REPLACE INTO species
        (id, name, flavor_text, genus, generation_id, generation_name,
         legendary, mythical, capture_rate, base_happiness,
         growth_rate, egg_groups, evolution_chain_id, evolves_from,
         color, shape, region) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (sid, data["name"], flavor, genus, gen_id, gen_name,
          data.get("is_legendary", False), data.get("is_mythical", False),
          data.get("capture_rate"), data.get("base_happiness"),
          data.get("growth_rate", {}).get("name", ""),
          egg_groups, evo_chain_id, evolves_from,
          data.get("color", {}).get("name", ""),
          data.get("shape", {}).get("name", ""), ""))

def fetch_pokemon_worker(url):
    """Fetch a single pokemon (used in thread pool)."""
    data = fetch(url)
    if not data:
        return None
    return data

def fetch_species_worker(url):
    return fetch(url)

def fetch_move_worker(move_id):
    return fetch(f"move/{move_id}")

def store_move(conn, data):
    if not data:
        return
    effect = ""
    for e in data.get("effect_entries", []):
        if e["language"]["name"] == "en":
            effect = e["short_effect"]
            break
    conn.execute("""
        INSERT OR REPLACE INTO moves
        (id, name, type_name, damage_class, power, accuracy, pp,
         priority, effect_chance, short_effect) VALUES (?,?,?,?,?,?,?,?,?,?)
    """, (data["id"], data["name"],
          data.get("type", {}).get("name", ""),
          data.get("damage_class", {}).get("name", ""),
          data.get("power"), data.get("accuracy"), data.get("pp"),
          data.get("priority", 0), data.get("effect_chance"), effect))

def fetch_evolution_chain(conn, chain_id):
    data = fetch(f"evolution-chain/{chain_id}")
    if not data:
        return
    def parse_chain(node, from_name=None):
        to_name = node["species"]["name"]
        for detail in node.get("evolution_details", []):
            conn.execute("""
                INSERT INTO evolutions
                (from_species, to_species, trigger, min_level, item,
                 held_item, known_move, min_happiness, time_of_day,
                 min_affection, needs_overworld_rain, gender, location)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (from_name, to_name,
                  detail.get("trigger", {}).get("name", ""),
                  detail.get("min_level"),
                  detail.get("item", {}).get("name") if detail.get("item") else None,
                  detail.get("held_item", {}).get("name") if detail.get("held_item") else None,
                  detail.get("known_move", {}).get("name") if detail.get("known_move") else None,
                  detail.get("min_happiness"),
                  detail.get("time_of_day") or None,
                  detail.get("min_affection"),
                  detail.get("needs_overworld_rain", False),
                  detail.get("gender"),
                  detail.get("location", {}).get("name") if detail.get("location") else None))
        for evolved in node.get("evolves_to", []):
            parse_chain(evolved, to_name)
    parse_chain(data["chain"])
    conn.commit()


if __name__ == "__main__":
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    create_schema(conn)

    # Check what's already fetched
    existing_pokemon = set(r[0] for r in conn.execute("SELECT id FROM pokemon WHERE id < 10000"))
    existing_species = set(r[0] for r in conn.execute("SELECT id FROM species"))
    existing_moves = set(r[0] for r in conn.execute("SELECT id FROM moves"))

    print(f"Already in DB: {len(existing_pokemon)} pokemon, {len(existing_species)} species, {len(existing_moves)} moves")

    # Step 1: Get full list
    print("Step 1: Fetching Pokémon list...")
    data = fetch("pokemon?limit=2000&offset=0")
    pokemon_list = data["results"] if data else []
    print(f"  Found {len(pokemon_list)} entries")

    # Step 2: Fetch pokemon data (concurrent)
    print("Step 2: Fetching Pokémon data (concurrent)...")
    move_ids_to_fetch = set()
    species_urls_to_fetch = {}

    # Filter to only unfetched
    urls_to_fetch = []
    for entry in pokemon_list:
        pid = int(entry["url"].rstrip("/").split("/")[-1])
        if pid not in existing_pokemon:
            urls_to_fetch.append(entry["url"])

    print(f"  Need to fetch {len(urls_to_fetch)} new pokemon ({len(existing_pokemon)} already done)")

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(fetch_pokemon_worker, url): url for url in urls_to_fetch}
        for future in tqdm(as_completed(futures), total=len(futures), desc="  Pokemon"):
            pdata = future.result()
            if not pdata:
                continue
            store_pokemon(conn, pdata)
            # Collect species
            sid = int(pdata["species"]["url"].split("/")[-2])
            if sid not in existing_species:
                species_urls_to_fetch[sid] = pdata["species"]["url"]
            # Collect move IDs
            for pm in pdata.get("moves", []):
                mid = int(pm["move"]["url"].split("/")[-2])
                if mid not in existing_moves:
                    move_ids_to_fetch.add(mid)
        conn.commit()

    # Also collect move IDs from existing pokemon_moves table
    all_move_ids_in_db = set(r[0] for r in conn.execute("SELECT DISTINCT move_id FROM pokemon_moves"))
    move_ids_to_fetch = all_move_ids_in_db - existing_moves
    print(f"  Total unique moves to fetch: {len(move_ids_to_fetch)}")

    # Fetch abilities for new pokemon
    print("Step 2b: Fetching abilities...")
    new_pokemon = conn.execute("""
        SELECT id FROM pokemon WHERE id < 10000
        AND id NOT IN (SELECT DISTINCT pokemon_id FROM pokemon_abilities)
    """).fetchall()
    for (pid,) in tqdm(new_pokemon, desc="  Abilities"):
        pdata = fetch(f"pokemon/{pid}")
        if pdata:
            store_abilities(conn, pdata)
    conn.commit()

    # Step 2c: Fetch species (concurrent)
    # Also check for missing ones from existing pokemon
    all_species_ids = set(r[0] for r in conn.execute("SELECT DISTINCT species_id FROM pokemon WHERE id < 10000"))
    for sid in all_species_ids:
        if sid not in existing_species and sid not in species_urls_to_fetch:
            species_urls_to_fetch[sid] = f"pokemon-species/{sid}"

    print(f"Step 2c: Fetching {len(species_urls_to_fetch)} species...")
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(fetch_species_worker, url): sid for sid, url in species_urls_to_fetch.items()}
        for future in tqdm(as_completed(futures), total=len(futures), desc="  Species"):
            sdata = future.result()
            if sdata:
                store_species(conn, sdata)
        conn.commit()

    # Step 3: Fetch moves (concurrent)
    print(f"Step 3: Fetching {len(move_ids_to_fetch)} moves...")
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(fetch_move_worker, mid): mid for mid in move_ids_to_fetch}
        for future in tqdm(as_completed(futures), total=len(futures), desc="  Moves"):
            mdata = future.result()
            if mdata:
                store_move(conn, mdata)
        conn.commit()

    # Step 4: Evolution chains
    print("Step 4: Fetching evolution chains...")
    conn.execute("DELETE FROM evolutions")
    chain_ids = set(r[0] for r in conn.execute(
        "SELECT DISTINCT evolution_chain_id FROM species WHERE evolution_chain_id IS NOT NULL"))
    print(f"  {len(chain_ids)} chains to fetch")
    for cid in tqdm(chain_ids, desc="  Evolutions"):
        fetch_evolution_chain(conn, cid)

    # Final stats
    print("\n=== Final DB Stats ===")
    print(f"Pokemon:    {conn.execute('SELECT COUNT(*) FROM pokemon WHERE id < 10000').fetchone()[0]}")
    print(f"Species:    {conn.execute('SELECT COUNT(*) FROM species').fetchone()[0]}")
    print(f"Moves:      {conn.execute('SELECT COUNT(*) FROM moves').fetchone()[0]}")
    print(f"PokeMoves:  {conn.execute('SELECT COUNT(*) FROM pokemon_moves').fetchone()[0]}")
    print(f"Evolutions: {conn.execute('SELECT COUNT(*) FROM evolutions').fetchone()[0]}")

    conn.close()
    print("\nDone! Run: python fetch_sprites.py")
