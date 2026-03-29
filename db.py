"""
db.py — All database queries for PokeBase.
Replaces inline queries from app.py.
"""

import sqlite3, json, os, random
from type_calc import defender_chart

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "pokebase.db")

VERSION_GROUP_NAMES = {
    "red-blue":          "Red / Blue",
    "yellow":            "Yellow",
    "gold-silver":       "Gold / Silver",
    "crystal":           "Crystal",
    "ruby-sapphire":     "Ruby / Sapphire",
    "emerald":           "Emerald",
    "firered-leafgreen": "FireRed / LeafGreen",
    "diamond-pearl":     "Diamond / Pearl",
    "platinum":          "Platinum",
    "heartgold-soulsilver": "HeartGold / SoulSilver",
    "black-white":       "Black / White",
    "colosseum":         "Colosseum",
    "xd":                "XD",
    "black-2-white-2":   "Black 2 / White 2",
    "x-y":               "X / Y",
    "omega-ruby-alpha-sapphire": "Omega Ruby / Alpha Sapphire",
    "sun-moon":          "Sun / Moon",
    "ultra-sun-ultra-moon": "Ultra Sun / Ultra Moon",
    "lets-go-pikachu-lets-go-eevee": "Let's Go",
    "sword-shield":      "Sword / Shield",
    "the-isle-of-armor": "Isle of Armor",
    "the-crown-tundra":  "Crown Tundra",
    "brilliant-diamond-shining-pearl": "BD / SP",
    "legends-arceus":    "Legends: Arceus",
    "scarlet-violet":    "Scarlet / Violet",
    "the-teal-mask":     "Teal Mask",
    "the-indigo-disk":   "Indigo Disk",
}

GENERATION_VERSION_GROUPS = {
    1: ["red-blue", "yellow"],
    2: ["gold-silver", "crystal"],
    3: ["ruby-sapphire", "emerald", "firered-leafgreen", "colosseum", "xd"],
    4: ["diamond-pearl", "platinum", "heartgold-soulsilver"],
    5: ["black-white", "black-2-white-2"],
    6: ["x-y", "omega-ruby-alpha-sapphire"],
    7: ["sun-moon", "ultra-sun-ultra-moon", "lets-go-pikachu-lets-go-eevee"],
    8: ["sword-shield", "the-isle-of-armor", "the-crown-tundra",
        "brilliant-diamond-shining-pearl", "legends-arceus"],
    9: ["scarlet-violet", "the-teal-mask", "the-indigo-disk"],
}

# Ordered list of version groups for sorting
VERSION_GROUP_ORDER = []
for gen in sorted(GENERATION_VERSION_GROUPS.keys()):
    VERSION_GROUP_ORDER.extend(GENERATION_VERSION_GROUPS[gen])


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def get_pokemon(identifier: str) -> dict | None:
    """Full Pokémon data for detail page."""
    conn = get_db()
    c = conn.cursor()

    # Lookup by name or national dex number
    if identifier.isdigit():
        row = c.execute("SELECT * FROM pokemon WHERE species_id=? AND is_default=1", (int(identifier),)).fetchone()
    else:
        row = c.execute("SELECT * FROM pokemon WHERE name=?", (identifier,)).fetchone()

    if not row:
        conn.close()
        return None

    pid = row["id"]
    sid = row["species_id"]

    species = c.execute("SELECT * FROM species WHERE id=?", (sid,)).fetchone()
    types   = c.execute("SELECT type_name FROM pokemon_types WHERE pokemon_id=? ORDER BY slot", (pid,)).fetchall()
    stats   = c.execute("SELECT * FROM pokemon_stats WHERE pokemon_id=?", (pid,)).fetchall()
    abilities = c.execute("SELECT * FROM pokemon_abilities WHERE pokemon_id=? ORDER BY slot", (pid,)).fetchall()
    sprites = c.execute("SELECT * FROM pokemon_sprites WHERE pokemon_id=?", (pid,)).fetchone()

    type_names = [t["type_name"] for t in types]
    matchups   = defender_chart(type_names)

    # Evolution chain — always show the FULL chain for any member
    evolutions = []
    evo_chain_species = []
    evolution_tree = None
    if species and species["evolution_chain_id"]:
        chain_id = species["evolution_chain_id"]

        # Get all evolutions for this chain
        evo_rows = c.execute("""
            SELECT DISTINCT e.* FROM evolutions e
            JOIN species s1 ON s1.name = e.from_species
            JOIN species s2 ON s2.name = e.to_species
            WHERE s1.evolution_chain_id = ? OR s2.evolution_chain_id = ?
            ORDER BY e.id
        """, (chain_id, chain_id)).fetchall()
        evolutions = [dict(r) for r in evo_rows]
        
        from collections import defaultdict
        evo_children = defaultdict(list)
        to_species_set = set()
        
        def edge_score(edge):
            score = 0
            if edge.get("item"): score += 10
            if edge.get("min_level"): score += 8
            if edge.get("min_happiness"): score += 5
            if edge.get("known_move"): score += 5
            if edge.get("trigger") == "trade": score += 2
            return score

        for e in evolutions:
            from_sp = e["from_species"]
            to_sp = e["to_species"]
            
            existing = next((x for x in evo_children[from_sp] if x["to_species"] == to_sp), None)
            if existing:
                if edge_score(e) > edge_score(existing):
                    evo_children[from_sp].remove(existing)
                    evo_children[from_sp].append(e)
            else:
                evo_children[from_sp].append(e)
                
            to_species_set.add(to_sp)
            
        roots = [e["from_species"] for e in evolutions if e["from_species"] not in to_species_set]
        roots = list(dict.fromkeys(roots))
        if not roots and evolutions:
            roots = [evolutions[0]["from_species"]]
            
        def build_evo_tree(species_name):
            return {
                "species": species_name,
                "evolves_to": [
                    {"details": edge, "node": build_evo_tree(edge["to_species"])}
                    for edge in evo_children[species_name]
                ]
            }
            
        evolution_tree = build_evo_tree(roots[0]) if roots else None

        # If no evolutions found (single-stage), still list chain species
        chain_species = c.execute("""
            SELECT id, name FROM species WHERE evolution_chain_id=? ORDER BY id
        """, (chain_id,)).fetchall()
        evo_chain_species = [dict(r) for r in chain_species]

    # Available version groups for this Pokémon
    vg_rows = c.execute("""
        SELECT DISTINCT version_group FROM pokemon_moves WHERE pokemon_id=?
    """, (pid,)).fetchall()
    available_games = [
        {"key": r["version_group"], "name": VERSION_GROUP_NAMES.get(r["version_group"], r["version_group"])}
        for r in vg_rows
        if r["version_group"] in VERSION_GROUP_NAMES
    ]
    # Sort by canonical game order
    available_games.sort(key=lambda x: VERSION_GROUP_ORDER.index(x["key"]) if x["key"] in VERSION_GROUP_ORDER else 999)

    # Default game: most recent available
    default_game = available_games[-1]["key"] if available_games else None

    # Prev / next
    nav_prev = c.execute("""
        SELECT p.name, p.species_id as dex FROM pokemon p
        WHERE p.species_id < ? AND p.is_default=1
        ORDER BY p.species_id DESC LIMIT 1
    """, (sid,)).fetchone()
    nav_next = c.execute("""
        SELECT p.name, p.species_id as dex FROM pokemon p
        WHERE p.species_id > ? AND p.is_default=1
        ORDER BY p.species_id ASC LIMIT 1
    """, (sid,)).fetchone()

    forms_rows = c.execute("SELECT id, name, is_default FROM pokemon WHERE species_id=? ORDER BY is_default DESC, id ASC", (sid,)).fetchall()
    forms = [dict(f) for f in forms_rows]

    conn.close()

    # Stat bar percentages
    MAX_STAT_VIS = 180
    stat_list = []
    for s in stats:
        base = s["base_stat"]
        pct = max(0, min(int((base / MAX_STAT_VIS) * 100), 100))
        stat_list.append({
            "stat_name": s["stat_name"],
            "base_stat": base,
            "effort": s["effort"],
            "percent": pct,
        })

    return {
        "id": pid,
        "name": row["name"],
        "display_name": row["name"].replace("-", " ").title(),
        "dex": sid,
        "species": dict(species) if species else {},
        "types": type_names,
        "stats": stat_list,
        "total_bst": sum(s["base_stat"] for s in stats),
        "abilities": [dict(a) for a in abilities],
        "sprites": dict(sprites) if sprites else {},
        "matchups": matchups,
        "evolutions": evolutions,
        "evolution_tree": evolution_tree,
        "evo_chain_species": evo_chain_species,
        "available_games": available_games,
        "default_game": default_game,
        "nav_prev": dict(nav_prev) if nav_prev else None,
        "nav_next": dict(nav_next) if nav_next else None,
        "egg_groups": json.loads(species["egg_groups"]) if species and species["egg_groups"] else [],
        "height": row["height"],
        "weight": row["weight"],
        "forms": forms,
    }

def get_moves(identifier: str, version_group: str, learn_method: str = "level-up") -> list:
    """Move pool for a Pokémon in a specific game."""
    conn = get_db()
    rows = conn.execute("""
        SELECT m.name, m.type_name, m.damage_class, m.power, m.accuracy,
               m.pp, m.priority, m.effect_chance, m.short_effect,
               pm.level_learned, pm.learn_method
        FROM pokemon_moves pm
        JOIN moves m ON m.id = pm.move_id
        JOIN pokemon p ON p.id = pm.pokemon_id
        WHERE p.name=? AND pm.version_group=? AND pm.learn_method=?
        ORDER BY pm.level_learned, m.name
    """, (identifier, version_group, learn_method)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def browse_pokemon(gen="all", type_="all", page=1, per_page=60) -> dict:
    conn = get_db()
    params = []
    where_clauses = ["p.is_default=1", "p.id < 10000"]

    if gen != "all":
        where_clauses.append("s.generation_id=?")
        params.append(int(gen))
    if type_ != "all":
        where_clauses.append("""
            EXISTS (SELECT 1 FROM pokemon_types pt
                    WHERE pt.pokemon_id=p.id AND pt.type_name=?)
        """)
        params.append(type_)

    where_sql = " AND ".join(where_clauses)
    offset = (page - 1) * per_page

    total = conn.execute(f"""
        SELECT COUNT(*) FROM pokemon p
        JOIN species s ON s.id=p.species_id
        WHERE {where_sql}
    """, params).fetchone()[0]

    rows = conn.execute(f"""
        SELECT p.id, p.name, p.species_id,
               GROUP_CONCAT(pt.type_name) as types
        FROM pokemon p
        JOIN species s ON s.id=p.species_id
        LEFT JOIN pokemon_types pt ON pt.pokemon_id=p.id
        WHERE {where_sql}
        GROUP BY p.id
        ORDER BY p.species_id
        LIMIT ? OFFSET ?
    """, params + [per_page, offset]).fetchall()

    conn.close()
    return {
        "pokemon": [dict(r) | {"types_list": (r["types"] or "").split(",")} for r in rows],
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page,
    }

def search_pokemon(q: str) -> list:
    if not q or len(q) < 1:
        return []
    conn = get_db()
    rows = conn.execute("""
        SELECT p.name, p.species_id as dex,
               GROUP_CONCAT(pt.type_name) as types
        FROM pokemon p
        LEFT JOIN pokemon_types pt ON pt.pokemon_id=p.id
        WHERE p.name LIKE ? AND p.is_default=1
        GROUP BY p.id
        ORDER BY p.species_id, p.id ASC
        LIMIT 10
    """, (q.lower() + "%",)).fetchall()
    conn.close()
    return [{"name": r["name"], "dex": r["dex"], "types": (r["types"] or "").split(",")} for r in rows]

def get_random_pokemon() -> str:
    conn = get_db()
    row = conn.execute("SELECT name FROM pokemon WHERE is_default=1 AND id<10000 ORDER BY RANDOM() LIMIT 1").fetchone()
    conn.close()
    return row["name"] if row else "pikachu"

def get_generations() -> list:
    conn = get_db()
    rows = conn.execute("SELECT DISTINCT generation_id, generation_name FROM species WHERE generation_id IS NOT NULL ORDER BY generation_id").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_all_types() -> list:
    from type_calc import ALL_TYPES
    return ALL_TYPES
