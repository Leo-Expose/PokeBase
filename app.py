from flask import Flask, render_template, request, jsonify, redirect, url_for
import db  # new db.py module

app = Flask(__name__)

# ── Main routes ──────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/pokemon/<identifier>")
def pokemon_detail(identifier):
    data = db.get_pokemon(identifier.lower())
    if not data:
        return render_template("404.html", identifier=identifier), 404
    return render_template("pokemon.html", data=data)

@app.route("/random")
def random_pokemon():
    ident = db.get_random_pokemon()
    return redirect(url_for("pokemon_detail", identifier=ident))

@app.route("/browse")
def browse():
    gen    = request.args.get("gen", "all")
    type_  = request.args.get("type", "all")
    page   = int(request.args.get("page", 1))
    data   = db.browse_pokemon(gen=gen, type_=type_, page=page)
    return render_template("browse.html", data=data, gen=gen, type_=type_, page=page)

@app.route("/type-calc")
def type_calc():
    return render_template("type_calc.html")

@app.route("/compare")
def compare():
    a = request.args.get("a", "")
    b = request.args.get("b", "")
    data_a = db.get_pokemon(a) if a else None
    data_b = db.get_pokemon(b) if b else None
    return render_template("compare.html", a=data_a, b=data_b)

# ── API routes ────────────────────────────────────────────────────────────────

@app.route("/api/suggest")
def suggest():
    q = request.args.get("q", "").strip()
    return jsonify(db.search_pokemon(q))

@app.route("/api/moves/<identifier>")
def moves_api(identifier):
    """Return move pool for a Pokémon for a given version group."""
    version_group = request.args.get("vg", "scarlet-violet")
    learn_method  = request.args.get("method", "level-up")
    return jsonify(db.get_moves(identifier, version_group, learn_method))

@app.route("/api/type-effectiveness")
def type_effectiveness_api():
    """
    GET /api/type-effectiveness?attacking=fire,flying&defending=grass,steel
    Returns full multiplier breakdown.
    """
    attacking = request.args.get("attacking", "").split(",")
    defending = request.args.get("defending", "").split(",")
    from type_calc import calculate
    return jsonify(calculate(attacking=[t for t in attacking if t],
                             defending=[t for t in defending if t]))

@app.route("/api/generations")
def generations():
    return jsonify(db.get_generations())

@app.route("/api/types")
def types():
    return jsonify(db.get_all_types())

if __name__ == "__main__":
    app.run(debug=True)
