from flask import Flask, request, jsonify, render_template
import sqlite3
import os

app = Flask(__name__)
DB = "pizzeria.db"

# Inicialización de la base de datos

def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS pizzas (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre      TEXT    NOT NULL,
            tamaño      TEXT    NOT NULL CHECK(tamaño IN ('chica','mediana','grande')),
            precio      REAL    NOT NULL,
            descripcion TEXT
        );

        CREATE TABLE IF NOT EXISTS ingredientes (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre   TEXT    NOT NULL,
            tipo     TEXT    NOT NULL CHECK(tipo IN ('queso','vegetal','carne','salsa')),
            pizza_id INTEGER NOT NULL,
            FOREIGN KEY (pizza_id) REFERENCES pizzas(id) ON DELETE CASCADE
        );
    """)
    conn.commit()
    conn.close()

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

init_db()


# Frontend

@app.route("/")
def index():
    return render_template("index.html")


## CRUD / PIZZAS ##

@app.route("/pizzas", methods=["GET"])
def get_pizzas():
    try:
        conn = get_db()
        rows = conn.execute("SELECT * FROM pizzas").fetchall()
        conn.close()
        return jsonify([dict(r) for r in rows]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/pizzas/<int:pid>", methods=["GET"])
def get_pizza(pid):
    try:
        conn = get_db()
        pizza = conn.execute("SELECT * FROM pizzas WHERE id=?", (pid,)).fetchone()
        if not pizza:
            conn.close()
            return jsonify({"error": "Pizza no encontrada"}), 404
        ingredientes = conn.execute(
            "SELECT * FROM ingredientes WHERE pizza_id=?", (pid,)
        ).fetchall()
        conn.close()
        result = dict(pizza)
        result["ingredientes"] = [dict(i) for i in ingredientes]
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/pizzas", methods=["POST"])
def create_pizza():
    try:
        data = request.get_json(silent=True)
        if not data:
            return jsonify({"error": "Body JSON inválido o vacío"}), 400
        for campo in ["nombre", "tamaño", "precio"]:
            if campo not in data:
                return jsonify({"error": f"Falta campo: {campo}"}), 400
        if not str(data["nombre"]).strip():
            return jsonify({"error": "nombre no puede estar vacío"}), 400
        if data["tamaño"] not in ("chica", "mediana", "grande"):
            return jsonify({"error": "tamaño debe ser chica, mediana o grande"}), 400
        if not isinstance(data["precio"], (int, float)) or data["precio"] <= 0:
            return jsonify({"error": "precio debe ser un número positivo"}), 400

        conn = get_db()
        cur = conn.execute(
            "INSERT INTO pizzas (nombre, tamaño, precio, descripcion) VALUES (?,?,?,?)",
            (data["nombre"], data["tamaño"], data["precio"], data.get("descripcion", ""))
        )
        conn.commit()
        new_id = cur.lastrowid
        conn.close()
        return jsonify({"mensaje": "Pizza creada", "id": new_id}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/pizzas/<int:pid>", methods=["PUT"])
def update_pizza(pid):
    try:
        data = request.get_json(silent=True)
        if not data:
            return jsonify({"error": "Body JSON inválido o vacío"}), 400
        conn = get_db()
        pizza = conn.execute("SELECT * FROM pizzas WHERE id=?", (pid,)).fetchone()
        if not pizza:
            conn.close()
            return jsonify({"error": "Pizza no encontrada"}), 404

        nombre      = data.get("nombre",      pizza["nombre"])
        tamaño      = data.get("tamaño",      pizza["tamaño"])
        precio      = data.get("precio",      pizza["precio"])
        descripcion = data.get("descripcion", pizza["descripcion"])

        if tamaño not in ("chica", "mediana", "grande"):
            conn.close()
            return jsonify({"error": "tamaño inválido"}), 400

        conn.execute(
            "UPDATE pizzas SET nombre=?, tamaño=?, precio=?, descripcion=? WHERE id=?",
            (nombre, tamaño, precio, descripcion, pid)
        )
        conn.commit()
        conn.close()
        return jsonify({"mensaje": "Pizza actualizada"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/pizzas/<int:pid>", methods=["DELETE"])
def delete_pizza(pid):
    try:
        conn = get_db()
        pizza = conn.execute("SELECT * FROM pizzas WHERE id=?", (pid,)).fetchone()
        if not pizza:
            conn.close()
            return jsonify({"error": "Pizza no encontrada"}), 404
        conn.execute("DELETE FROM pizzas WHERE id=?", (pid,))
        conn.commit()
        conn.close()
        return jsonify({"mensaje": "Pizza eliminada"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


## CRUD / INGREDIENTES##

@app.route("/ingredientes", methods=["GET"])
def get_ingredientes():
    try:
        conn = get_db()
        rows = conn.execute("SELECT * FROM ingredientes").fetchall()
        conn.close()
        return jsonify([dict(r) for r in rows]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/ingredientes/<int:iid>", methods=["GET"])
def get_ingrediente(iid):
    try:
        conn = get_db()
        row = conn.execute("SELECT * FROM ingredientes WHERE id=?", (iid,)).fetchone()
        conn.close()
        if not row:
            return jsonify({"error": "Ingrediente no encontrado"}), 404
        return jsonify(dict(row)), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/ingredientes", methods=["POST"])
def create_ingrediente():
    try:
        data = request.get_json(silent=True)
        if not data:
            return jsonify({"error": "Body JSON inválido o vacío"}), 400
        for campo in ["nombre", "tipo", "pizza_id"]:
            if campo not in data:
                return jsonify({"error": f"Falta campo: {campo}"}), 400
        if not str(data["nombre"]).strip():
            return jsonify({"error": "nombre no puede estar vacío"}), 400
        if data["tipo"] not in ("queso", "vegetal", "carne", "salsa"):
            return jsonify({"error": "tipo debe ser queso, vegetal, carne o salsa"}), 400

        conn = get_db()
        pizza = conn.execute("SELECT id FROM pizzas WHERE id=?", (data["pizza_id"],)).fetchone()
        if not pizza:
            conn.close()
            return jsonify({"error": "pizza_id no existe"}), 400

        cur = conn.execute(
            "INSERT INTO ingredientes (nombre, tipo, pizza_id) VALUES (?,?,?)",
            (data["nombre"], data["tipo"], data["pizza_id"])
        )
        conn.commit()
        new_id = cur.lastrowid
        conn.close()
        return jsonify({"mensaje": "Ingrediente creado", "id": new_id}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/ingredientes/<int:iid>", methods=["PUT"])
def update_ingrediente(iid):
    try:
        data = request.get_json(silent=True)
        if not data:
            return jsonify({"error": "Body JSON inválido o vacío"}), 400
        conn = get_db()
        ing = conn.execute("SELECT * FROM ingredientes WHERE id=?", (iid,)).fetchone()
        if not ing:
            conn.close()
            return jsonify({"error": "Ingrediente no encontrado"}), 404

        nombre   = data.get("nombre",   ing["nombre"])
        tipo     = data.get("tipo",     ing["tipo"])
        pizza_id = data.get("pizza_id", ing["pizza_id"])

        if tipo not in ("queso", "vegetal", "carne", "salsa"):
            conn.close()
            return jsonify({"error": "tipo inválido"}), 400

        if pizza_id != ing["pizza_id"]:
            pizza = conn.execute("SELECT id FROM pizzas WHERE id=?", (pizza_id,)).fetchone()
            if not pizza:
                conn.close()
                return jsonify({"error": "pizza_id no existe"}), 400

        conn.execute(
            "UPDATE ingredientes SET nombre=?, tipo=?, pizza_id=? WHERE id=?",
            (nombre, tipo, pizza_id, iid)
        )
        conn.commit()
        conn.close()
        return jsonify({"mensaje": "Ingrediente actualizado"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/ingredientes/<int:iid>", methods=["DELETE"])
def delete_ingrediente(iid):
    try:
        conn = get_db()
        ing = conn.execute("SELECT * FROM ingredientes WHERE id=?", (iid,)).fetchone()
        if not ing:
            conn.close()
            return jsonify({"error": "Ingrediente no encontrado"}), 404
        conn.execute("DELETE FROM ingredientes WHERE id=?", (iid,))
        conn.commit()
        conn.close()
        return jsonify({"mensaje": "Ingrediente eliminado"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)