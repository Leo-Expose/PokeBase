"""
type_calc.py — Standalone type effectiveness calculator
Covers Gen 1–9 including Fairy type.
This is a static lookup — no DB needed.
"""

# Full Gen 2–9 type chart (attacker → defender → multiplier)
# 0 = immune, 0.5 = not very effective, 2 = super effective
TYPE_CHART = {
    "normal":   {"rock": 0.5, "ghost": 0, "steel": 0.5},
    "fire":     {"fire": 0.5, "water": 0.5, "grass": 2, "ice": 2,
                 "bug": 2, "rock": 0.5, "dragon": 0.5, "steel": 2},
    "water":    {"fire": 2, "water": 0.5, "grass": 0.5, "ground": 2,
                 "rock": 2, "dragon": 0.5},
    "electric": {"water": 2, "electric": 0.5, "grass": 0.5, "ground": 0,
                 "flying": 2, "dragon": 0.5},
    "grass":    {"fire": 0.5, "water": 2, "grass": 0.5, "poison": 0.5,
                 "ground": 2, "flying": 0.5, "bug": 0.5, "rock": 2,
                 "dragon": 0.5, "steel": 0.5},
    "ice":      {"water": 0.5, "grass": 2, "ice": 0.5, "ground": 2,
                 "flying": 2, "dragon": 2, "steel": 0.5, "fire": 0.5},
    "fighting": {"normal": 2, "ice": 2, "poison": 0.5, "flying": 0.5,
                 "psychic": 0.5, "bug": 0.5, "rock": 2, "ghost": 0,
                 "dark": 2, "steel": 2, "fairy": 0.5},
    "poison":   {"grass": 2, "poison": 0.5, "ground": 0.5, "rock": 0.5,
                 "ghost": 0.5, "steel": 0, "fairy": 2},
    "ground":   {"fire": 2, "electric": 2, "grass": 0.5, "poison": 2,
                 "flying": 0, "bug": 0.5, "rock": 2, "steel": 2},
    "flying":   {"electric": 0.5, "grass": 2, "fighting": 2, "bug": 2,
                 "rock": 0.5, "steel": 0.5},
    "psychic":  {"fighting": 2, "poison": 2, "psychic": 0.5,
                 "dark": 0, "steel": 0.5},
    "bug":      {"fire": 0.5, "grass": 2, "fighting": 0.5, "poison": 0.5,
                 "flying": 0.5, "psychic": 2, "ghost": 0.5, "dark": 2,
                 "steel": 0.5, "fairy": 0.5},
    "rock":     {"fire": 2, "ice": 2, "fighting": 0.5, "ground": 0.5,
                 "flying": 2, "bug": 2, "steel": 0.5},
    "ghost":    {"normal": 0, "psychic": 2, "ghost": 2, "dark": 0.5},
    "dragon":   {"dragon": 2, "steel": 0.5, "fairy": 0},
    "dark":     {"fighting": 0.5, "psychic": 2, "ghost": 2,
                 "dark": 0.5, "fairy": 0.5},
    "steel":    {"fire": 0.5, "water": 0.5, "electric": 0.5, "ice": 2,
                 "rock": 2, "steel": 0.5, "fairy": 2},
    "fairy":    {"fire": 0.5, "fighting": 2, "poison": 0.5, "dragon": 2,
                 "dark": 2, "steel": 0.5},
}

ALL_TYPES = list(TYPE_CHART.keys())

def get_multiplier(attacker: str, defender: str) -> float:
    """Return effectiveness of attacker type against defender type."""
    return TYPE_CHART.get(attacker, {}).get(defender, 1.0)

def calculate(attacking: list, defending: list) -> dict:
    """
    Calculate full breakdown for a move/attacker against a defending Pokémon.

    attacking: list of 1 attacking move type (or 1–2 for combined)
    defending: list of 1–2 defender types

    Returns:
      {
        "multiplier": 4.0,
        "label": "×4",
        "category": "super_effective" | "not_very" | "immune" | "normal",
        "breakdown": [{"attacker": "fire", "defender": "grass", "mult": 2.0}, ...]
      }
    """
    total = 1.0
    breakdown = []

    for atk in attacking:
        for dfn in defending:
            m = get_multiplier(atk, dfn)
            total *= m
            breakdown.append({"attacker": atk, "defender": dfn, "mult": m})

    total = round(total, 4)

    if total == 0:
        cat = "immune"
    elif total >= 2:
        cat = "super_effective"
    elif total < 1:
        cat = "not_very"
    else:
        cat = "normal"

    label = f"×{total:g}"

    return {
        "multiplier": total,
        "label": label,
        "category": cat,
        "breakdown": breakdown,
    }

def defender_chart(defending: list) -> dict:
    """
    Full defensive type chart — what every attacking type does to this defender.
    Used for the Pokémon detail page matchup section.
    """
    weak, resist, immune, normal = [], [], [], []

    for atk in ALL_TYPES:
        result = calculate([atk], defending)
        m = result["multiplier"]
        entry = {"type": atk, "multiplier": m, "label": result["label"]}
        if m == 0:
            immune.append(entry)
        elif m >= 2:
            weak.append(entry)
        elif m < 1:
            resist.append(entry)
        else:
            normal.append(entry)

    weak.sort(key=lambda x: -x["multiplier"])
    resist.sort(key=lambda x: x["multiplier"])

    return {"weak": weak, "resist": resist, "immune": immune, "normal": normal}
