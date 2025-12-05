from flask import Flask, render_template, request, jsonify, redirect, url_for
import sqlite3
import random
import os
app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "pokedex.sqlite")

LANG_EN = 9
BW_VERSION_GROUP_ID = 11                # Black & White
LEVELUP_METHOD_ID = 1                   # Level-up moves


# ---------- DB helpers ----------

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_pokemon_basic(conn, identifier: str):
    """
    Return a single pokemon row by identifier with a 'display_name'
    based on pokemon_form_names (for megas/forms) or species name.
    """
    c = conn.cursor()
    c.execute(
        """
        SELECT
            p.id,
            p.identifier,
            p.species_id,
            COALESCE(pfn.pokemon_name, psn.name) AS display_name
        FROM pokemon p
        LEFT JOIN pokemon_forms pf
               ON pf.pokemon_id = p.id
        LEFT JOIN pokemon_form_names pfn
               ON pfn.pokemon_form_id = pf.id
              AND pfn.local_language_id = ?
        JOIN pokemon_species_names psn
             ON psn.pokemon_species_id = p.species_id
            AND psn.local_language_id = ?
        WHERE p.identifier = ?
        LIMIT 1
        """,
        (LANG_EN, LANG_EN, identifier.lower()),
    )
    return c.fetchone()


def compute_type_matchups(conn, types_rows):
    """Compute weaknesses / resists / immunities from type_efficacy."""
    if not types_rows:
        return {"weak": [], "resist": [], "immune": []}

    type_ids = [t["id"] for t in types_rows]
    c = conn.cursor()

    c.execute(
        """
        SELECT t.id, t.identifier, tn.name
        FROM types t
        JOIN type_names tn
             ON tn.type_id = t.id AND tn.local_language_id = ?
        ORDER BY t.id
        """,
        (LANG_EN,),
    )
    attack_types = c.fetchall()
    factors = {row["id"]: 1.0 for row in attack_types}

    placeholders = ",".join("?" for _ in type_ids)
    c.execute(
        f"""
        SELECT damage_type_id, target_type_id, damage_factor
        FROM type_efficacy
        WHERE target_type_id IN ({placeholders})
        """,
        type_ids,
    )
    for row in c.fetchall():
        atk = row["damage_type_id"]
        factors[atk] *= row["damage_factor"] / 100.0

    weak, resist, immune = [], [], []

    for row in attack_types:
        atk_id = row["id"]
        mult = round(factors.get(atk_id, 1.0), 2)
        entry = {
            "identifier": row["identifier"],
            "name": row["name"],
            "multiplier": mult,
            "label": f"×{mult:g}",
        }
        if mult == 0:
            immune.append(entry)
        elif mult > 1.01:
            weak.append(entry)
        elif mult < 0.99:
            resist.append(entry)

    weak.sort(key=lambda x: x["multiplier"], reverse=True)
    resist.sort(key=lambda x: x["multiplier"])
    return {"weak": weak, "resist": resist, "immune": immune}


def describe_evo_step(row):
    """Turn a pokemon_evolution row (with joined names) into a simple text label."""
    parts = []
    trigger = row["trigger_identifier"] or ""

    lvl = row["minimum_level"]
    item = row["item_name"]
    held_item = row["held_item_name"]
    move_name = row["known_move_name"]
    happiness = row["minimum_happiness"]
    time_of_day = row["time_of_day"] or ""

    if lvl:
        parts.append(f"Level {lvl}")
    if item:
        parts.append(f"Use {item}")
    if held_item:
        parts.append(f"Holding {held_item}")
    if happiness:
        parts.append("High friendship")
    if move_name:
        parts.append(f"Knows {move_name}")
    if time_of_day:
        parts.append(time_of_day.capitalize())

    if not parts and trigger:
        parts.append(trigger.replace("-", " ").title())

    return ", ".join(parts) or ""


def get_pokemon_data(identifier: str):
    conn = get_db()
    c = conn.cursor()

    base = get_pokemon_basic(conn, identifier)
    if not base:
        conn.close()
        return None

    pokemon_id = base["id"]
    species_id = base["species_id"]

    # --- stats ---------------------------------------------------------
    c.execute(
        """
        SELECT
            ps.stat_id,
            s.identifier AS stat_identifier,
            sn.name      AS stat_name,
            ps.base_stat
        FROM pokemon_stats ps
        JOIN stats s     ON s.id = ps.stat_id
        JOIN stat_names sn
             ON sn.stat_id = s.id AND sn.local_language_id = ?
        WHERE ps.pokemon_id = ?
        ORDER BY ps.stat_id
        """,
        (LANG_EN, pokemon_id),
    )
    stat_rows = c.fetchall()
    if not stat_rows:
        conn.close()
        return None

    # For tooltips: real min / max per stat across the whole dex
    c.execute(
        """
        SELECT stat_id,
               MIN(base_stat) AS lo,
               MAX(base_stat) AS hi
        FROM pokemon_stats
        GROUP BY stat_id
        """
    )
    mins_maxs = {r["stat_id"]: (r["lo"], r["hi"]) for r in c.fetchall()}

    # For bars: use a fixed visual max so low stats don't look microscopic
    MAX_STAT_VIS = 180  # tweak if you want; 180 feels nice visually

    stats, total = [], 0
    for row in stat_rows:
        lo, hi = mins_maxs.get(row["stat_id"], (0, 255))
        base_val = row["base_stat"]

        pct = int(base_val / MAX_STAT_VIS * 100) if MAX_STAT_VIS else 0
        # clamp for aesthetics
        pct = max(5, min(pct, 100))

        stats.append(
            {
                "id": row["stat_id"],
                "identifier": row["stat_identifier"],
                "name": row["stat_name"],
                "value": base_val,
                "min": lo,
                "max": hi,
                "percent": pct,
            }
        )
        total += base_val


    # --- types ---------------------------------------------------------
    c.execute(
        """
        SELECT ty.id, ty.identifier, tn.name
        FROM pokemon_types pt
        JOIN types ty      ON ty.id = pt.type_id
        JOIN type_names tn
             ON tn.type_id = ty.id AND tn.local_language_id = ?
        WHERE pt.pokemon_id = ?
        ORDER BY pt.slot
        """,
        (LANG_EN, pokemon_id),
    )
    type_rows = c.fetchall()
    types = [
        {"id": r["id"], "identifier": r["identifier"], "name": r["name"]}
        for r in type_rows
    ]

    # --- abilities -----------------------------------------------------
    c.execute(
        """
        SELECT
            a.identifier,
            an.name,
            pa.is_hidden,
            (
                SELECT aft.flavor_text
                FROM ability_flavor_text aft
                WHERE aft.ability_id = a.id
                  AND aft.language_id = ?
                ORDER BY aft.version_group_id DESC
                LIMIT 1
            ) AS flavor_text
        FROM pokemon_abilities pa
        JOIN abilities a  ON a.id = pa.ability_id
        JOIN ability_names an
             ON an.ability_id = a.id AND an.local_language_id = ?
        WHERE pa.pokemon_id = ?
        ORDER BY pa.slot
        """,
        (LANG_EN, LANG_EN, pokemon_id),
    )
    abilities = []
    for r in c.fetchall():
        text = (r["flavor_text"] or "").replace("\n", " ").replace("\f", " ")
        abilities.append(
            {
                "identifier": r["identifier"],
                "name": r["name"],
                "is_hidden": bool(r["is_hidden"]),
                "flavor_text": text,
            }
        )

    # --- species info, generation, region ------------------------------
    c.execute(
        """
        SELECT
            evolution_chain_id,
            growth_rate_id,
            capture_rate,
            base_happiness,
            generation_id
        FROM pokemon_species
        WHERE id = ?
        """,
        (species_id,),
    )
    srow = c.fetchone()
    evo_chain_id = None
    growth_rate_name = None
    capture_rate = None
    base_happiness = None
    generation_name = None
    region_name = None

    if srow:
        evo_chain_id = srow["evolution_chain_id"]
        capture_rate = srow["capture_rate"]
        base_happiness = srow["base_happiness"]

        if srow["growth_rate_id"]:
            c.execute(
                """
                SELECT COALESCE(grp.name, gr.identifier) AS name
                FROM growth_rates gr
                LEFT JOIN growth_rate_prose grp
                       ON grp.growth_rate_id = gr.id
                      AND grp.local_language_id = ?
                WHERE gr.id = ?
                LIMIT 1
                """,
                (LANG_EN, srow["growth_rate_id"]),
            )
            gr = c.fetchone()
            if gr:
                growth_rate_name = gr["name"]

        if srow["generation_id"]:
            c.execute(
                """
                SELECT
                    gn.name AS gen_name,
                    rn.name AS region_name
                FROM generations g
                LEFT JOIN generation_names gn
                       ON gn.generation_id = g.id
                      AND gn.local_language_id = ?
                LEFT JOIN regions r
                       ON r.id = g.main_region_id
                LEFT JOIN region_names rn
                       ON rn.region_id = r.id
                      AND rn.local_language_id = ?
                WHERE g.id = ?
                LIMIT 1
                """,
                (LANG_EN, LANG_EN, srow["generation_id"]),
            )
            gr = c.fetchone()
            if gr:
                generation_name = gr["gen_name"]
                region_name = gr["region_name"]

    # --- evolution chain (edge-based, neat rows) -----------------------
    evolution_edges = []

    if evo_chain_id:
        c.execute(
            """
            SELECT
                from_ps.id   AS from_species_id,
                from_ps.identifier AS from_identifier,
                from_psn.name      AS from_name,
                to_ps.id     AS to_species_id,
                to_ps.identifier   AS to_identifier,
                to_psn.name        AS to_name,
                et.identifier      AS trigger_identifier,
                e.minimum_level,
                e.minimum_happiness,
                e.time_of_day,
                itn.name  AS item_name,
                hitn.name AS held_item_name,
                kmn.name  AS known_move_name
            FROM pokemon_evolution e
            JOIN pokemon_species to_ps
                 ON to_ps.id = e.evolved_species_id
            LEFT JOIN pokemon_species from_ps
                 ON from_ps.id = to_ps.evolves_from_species_id
            LEFT JOIN pokemon_species_names to_psn
                 ON to_psn.pokemon_species_id = to_ps.id
                AND to_psn.local_language_id = ?
            LEFT JOIN pokemon_species_names from_psn
                 ON from_psn.pokemon_species_id = from_ps.id
                AND from_psn.local_language_id = ?
            LEFT JOIN evolution_triggers et
                   ON et.id = e.evolution_trigger_id
            LEFT JOIN items it
                   ON it.id = e.trigger_item_id
            LEFT JOIN item_names itn
                   ON itn.item_id = it.id
                  AND itn.local_language_id = ?
            LEFT JOIN items hit
                   ON hit.id = e.held_item_id
            LEFT JOIN item_names hitn
                   ON hitn.item_id = hit.id
                  AND hitn.local_language_id = ?
            LEFT JOIN moves km
                   ON km.id = e.known_move_id
            LEFT JOIN move_names kmn
                   ON kmn.move_id = km.id
                  AND kmn.local_language_id = ?
            WHERE to_ps.evolution_chain_id = ?
            ORDER BY to_ps.id
            """,
            (LANG_EN, LANG_EN, LANG_EN, LANG_EN, LANG_EN, evo_chain_id),
        )

        for row in c.fetchall():
            condition = describe_evo_step(row)
            evolution_edges.append(
                {
                    "from": (
                        {
                            "species_id": row["from_species_id"],
                            "identifier": row["from_identifier"],
                            "name": row["from_name"],
                        }
                        if row["from_species_id"] is not None
                        else None
                    ),
                    "to": {
                        "species_id": row["to_species_id"],
                        "identifier": row["to_identifier"],
                        "name": row["to_name"],
                    },
                    "condition": condition,
                }
            )

    # --- egg groups -----------------------------------------------------
    c.execute(
        """
        SELECT egp.name
        FROM pokemon_egg_groups peg
        JOIN egg_group_prose egp
             ON egp.egg_group_id = peg.egg_group_id
            AND egp.local_language_id = ?
        WHERE peg.species_id = ?
        ORDER BY peg.egg_group_id
        """,
        (LANG_EN, species_id),
    )
    egg_groups = [r["name"] for r in c.fetchall()]

    # --- flavor text ----------------------------------------------------
    c.execute(
        """
        SELECT flavor_text
        FROM pokemon_species_flavor_text
        WHERE species_id = ?
          AND language_id = ?
        ORDER BY version_id DESC
        LIMIT 1
        """,
        (species_id, LANG_EN),
    )
    ft = c.fetchone()
    flavor_text = (
        ft["flavor_text"].replace("\n", " ").replace("\f", " ")
        if ft
        else ""
    )

    # --- sprite (LOCAL, not PokeAPI) -----------------------------------
    # Veekun stores sprites as PNG files on disk, not inside the SQLite DB.
    # Put/copy your Gen V front sprites under:
    #   static/sprites/bw/<pokemon_id>.png
    # and we’ll serve them from there.
    sprite_url = f"/static/sprites/{pokemon_id}.png"

    # --- moves with details (BW, level-up) ------------------------------
    c.execute(
        """
        SELECT
            pm.level,
            m.identifier           AS move_identifier,
            COALESCE(mn.name, m.identifier) AS move_name,
            t.identifier           AS type_identifier,
            tn.name                AS type_name,
            mdc.identifier         AS damage_class_identifier,
            mdcp.name              AS damage_class_name,
            m.power,
            m.accuracy,
            m.pp,
            mep.short_effect
        FROM pokemon_moves pm
        JOIN moves m ON m.id = pm.move_id
        LEFT JOIN move_names mn
               ON mn.move_id = m.id AND mn.local_language_id = ?
        LEFT JOIN types t
               ON t.id = m.type_id
        LEFT JOIN type_names tn
               ON tn.type_id = t.id AND tn.local_language_id = ?
        LEFT JOIN move_damage_classes mdc
               ON mdc.id = m.damage_class_id
        LEFT JOIN move_damage_class_prose mdcp
               ON mdcp.move_damage_class_id = mdc.id
              AND mdcp.local_language_id = ?
        LEFT JOIN move_effect_prose mep
               ON mep.move_effect_id = m.effect_id
              AND mep.local_language_id = ?
        WHERE pm.pokemon_id = ?
          AND pm.version_group_id = ?
          AND pm.pokemon_move_method_id = ?
        ORDER BY pm.level, m.identifier
        """,
        (LANG_EN, LANG_EN, LANG_EN, LANG_EN,
         pokemon_id, BW_VERSION_GROUP_ID, LEVELUP_METHOD_ID),
    )
    moves = []
    for r in c.fetchall():
        effect = (r["short_effect"] or "").replace("\n", " ").replace("\f", " ")
        moves.append(
            {
                "name": r["move_name"].replace("-", " ").title(),
                "level": r["level"],
                "type_identifier": r["type_identifier"],
                "type_name": r["type_name"],
                "category": r["damage_class_name"],
                "power": r["power"],
                "accuracy": r["accuracy"],
                "pp": r["pp"],
                "effect": effect,
            }
        )

    # --- forms (Deoxys, Megas, etc.) -----------------------------------
    c.execute(
        """
        SELECT
            p.identifier,
            COALESCE(pfn.pokemon_name, psn.name) AS display_name,
            p.is_default
        FROM pokemon p
        LEFT JOIN pokemon_forms pf
               ON pf.pokemon_id = p.id
        LEFT JOIN pokemon_form_names pfn
               ON pfn.pokemon_form_id = pf.id
              AND pfn.local_language_id = ?
        JOIN pokemon_species_names psn
             ON psn.pokemon_species_id = p.species_id
            AND psn.local_language_id = ?
        WHERE p.species_id = ?
        ORDER BY p.id
        """,
        (LANG_EN, LANG_EN, species_id),
    )
    forms = [
        {
            "identifier": r["identifier"],
            "name": r["display_name"],
            "is_default": bool(r["is_default"]),
        }
        for r in c.fetchall()
    ]
    if len(forms) <= 1:
        forms = []

    # --- type matchups --------------------------------------------------
    type_matchups = compute_type_matchups(conn, type_rows)

    # --- encounters (where to find) ------------------------------------
    encounter_map = {}
    c.execute(
        """
        SELECT
            vn.name AS version_name,
            ln.name AS location_name
        FROM encounters e
        JOIN location_areas la
             ON la.id = e.location_area_id
        JOIN locations l
             ON l.id = la.location_id
        JOIN location_names ln
             ON ln.location_id = l.id AND ln.local_language_id = ?
        JOIN versions v
             ON v.id = e.version_id
        JOIN version_names vn
             ON vn.version_id = v.id AND vn.local_language_id = ?
        WHERE e.pokemon_id = ?
        LIMIT 40
        """,
        (LANG_EN, LANG_EN, pokemon_id),
    )
    for r in c.fetchall():
        ver = r["version_name"]
        encounter_map.setdefault(ver, set()).add(r["location_name"])

    encounters = []
    for ver, locs in encounter_map.items():
        encounters.append(
            {
                "version": ver,
                "locations": sorted(locs)[:5],
            }
        )
    encounters.sort(key=lambda x: x["version"])

    # --- prev / next (species-based) -----------------------------------
    nav_prev = nav_next = None

    c.execute(
        """
        SELECT ps.id AS species_id,
               ps.identifier,
               psn.name AS name
        FROM pokemon_species ps
        JOIN pokemon_species_names psn
             ON psn.pokemon_species_id = ps.id
            AND psn.local_language_id = ?
        WHERE ps.id < ?
        ORDER BY ps.id DESC
        LIMIT 1
        """,
        (LANG_EN, species_id),
    )
    r = c.fetchone()
    if r:
        nav_prev = {
            "dex": r["species_id"],
            "identifier": r["identifier"],
            "name": r["name"],
        }

    c.execute(
        """
        SELECT ps.id AS species_id,
               ps.identifier,
               psn.name AS name
        FROM pokemon_species ps
        JOIN pokemon_species_names psn
             ON psn.pokemon_species_id = ps.id
            AND psn.local_language_id = ?
        WHERE ps.id > ?
        ORDER BY ps.id ASC
        LIMIT 1
        """,
        (LANG_EN, species_id),
    )
    r = c.fetchone()
    if r:
        nav_next = {
            "dex": r["species_id"],
            "identifier": r["identifier"],
            "name": r["name"],
        }

    conn.close()

    return {
        "identifier": base["identifier"],
        "display_name": base["display_name"],
        "dex": species_id,
        "stats": stats,
        "total": total,
        "types": [{"identifier": t["identifier"], "name": t["name"]} for t in types],
        "abilities": abilities,
        "sprite_url": sprite_url,
        "moves": moves,
        "evolutions": evolution_edges,
        "egg_groups": egg_groups,
        "growth_rate": growth_rate_name,
        "capture_rate": capture_rate,
        "base_happiness": base_happiness,
        "flavor_text": flavor_text,
        "generation": generation_name,
        "region": region_name,
        "type_matchups": type_matchups,
        "forms": forms,
        "nav_prev": nav_prev,
        "nav_next": nav_next,
        "encounters": encounters,
    }


def get_random_species_identifier():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id FROM pokemon_species ORDER BY RANDOM() LIMIT 1")
    row = c.fetchone()
    if not row:
        conn.close()
        return "pikachu"
    species_id = row["id"]
    c.execute(
        """
        SELECT identifier
        FROM pokemon
        WHERE species_id = ? AND is_default = 1
        LIMIT 1
        """,
        (species_id,),
    )
    row2 = c.fetchone()
    conn.close()
    return row2["identifier"] if row2 else "pikachu"


# ---------- routes ----------

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        name = request.form.get("pokemon_name", "").strip().lower()
        if name:
            return redirect(url_for("pokemon_detail", identifier=name))
    return render_template("index.html", data=None, pokemon_name="")


@app.route("/pokemon/<identifier>")
def pokemon_detail(identifier):
    pokemon_name = identifier.lower()
    data = get_pokemon_data(pokemon_name)
    return render_template("index.html", data=data, pokemon_name=pokemon_name)


@app.route("/random")
def random_pokemon():
    ident = get_random_species_identifier()
    return redirect(url_for("pokemon_detail", identifier=ident))


@app.route("/api/pokemon-suggest")
def pokemon_suggest():
    """Autocomplete: default-form Pokémon with nice display names."""
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify(results=[])

    conn = get_db()
    c = conn.cursor()
    like = q.lower() + "%"

    c.execute(
        """
        SELECT
            p.identifier,
            COALESCE(pfn.pokemon_name, psn.name) AS display_name
        FROM pokemon p
        LEFT JOIN pokemon_forms pf
               ON pf.pokemon_id = p.id
        LEFT JOIN pokemon_form_names pfn
               ON pfn.pokemon_form_id = pf.id
              AND pfn.local_language_id = ?
        JOIN pokemon_species_names psn
             ON psn.pokemon_species_id = p.species_id
            AND psn.local_language_id = ?
        WHERE p.is_default = 1
          AND (p.identifier LIKE ? OR psn.name LIKE ?)
        ORDER BY psn.name
        LIMIT 8
        """,
        (LANG_EN, LANG_EN, like, like),
    )

    results = [
        {"id": r["identifier"], "name": r["display_name"]}
        for r in c.fetchall()
    ]
    conn.close()
    return jsonify(results=results)


if __name__ == "__main__":
    app.run(debug=True)
