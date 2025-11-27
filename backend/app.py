# backend/app.py
from flask import Flask, request, jsonify, g
from flask_cors import CORS
import sqlite3
import time
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "edubot.db")

app = Flask(__name__)
CORS(app)  # permite llamadas desde el frontend

# -------------------------
# Helpers de DB (SQLite)
# -------------------------
def get_db():
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES)
        db.row_factory = sqlite3.Row
    return db

def init_db():
    db = sqlite3.connect(DB_PATH)
    cur = db.cursor()
    # tabla simple para eventos (mensajes y tramites)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_type TEXT NOT NULL,
        intent TEXT,
        text TEXT,
        channel TEXT,
        timestamp INTEGER
    )
    """)
    db.commit()
    db.close()

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, "_database", None)
    if db is not None:
        db.close()

def save_event(event_type, intent=None, text=None, channel="web"):
    db = get_db()
    cur = db.cursor()
    cur.execute(
        "INSERT INTO events (event_type, intent, text, channel, timestamp) VALUES (?, ?, ?, ?, ?)",
        (event_type, intent, text, channel, int(time.time() * 1000))
    )
    db.commit()

# -------------------------
# Mock de respuestas (simple)
# -------------------------
SAMPLE_RESPONSES = [
    {"intent": "horario", "keywords": ["horario", "hora", "clase"], "reply": "El horario escolar es L-V 7:00 - 12:00."},
    {"intent": "matricula", "keywords": ["matrícula", "matricula", "inscripción"], "reply": "Para matricularte necesitas documento de identidad y el formulario de inscripción."},
    {"intent": "constancia", "keywords": ["constancia", "certificado"], "reply": "Puedes solicitar la constancia a través del gestor de trámites en la sección 'Trámites'."},
    {"intent": "calendario", "keywords": ["calendario", "fechas", "vacaciones"], "reply": "El calendario académico 2025 inicia el 10 de febrero."},
    {"intent": "ruta", "keywords": ["ruta", "bus", "ruta escolar"], "reply": "Las rutas escolares se publican en la secretaría. ¿Quieres el enlace?"}
]

def detect_intent(text):
    t = (text or "").lower()
    for s in SAMPLE_RESPONSES:
        for k in s["keywords"]:
            if k in t:
                return s["intent"], s["reply"]
    return "fallback", "Lo siento, no entendí. Prueba: horario, matrícula, constancia, calendario, ruta."

# -------------------------
# Endpoints
# -------------------------
@app.route("/api/message", methods=["POST"])
def api_message():
    payload = request.get_json(force=True)
    text = payload.get("text", "")
    channel = payload.get("channel", "web")
    # guardar evento de entrada
    save_event("message_sent", intent=None, text=text, channel=channel)
    # detectar intent (mock)
    intent, reply = detect_intent(text)
    # guardar evento de respuesta
    save_event("message_received", intent=intent, text=reply, channel=channel)
    return jsonify({"reply": reply, "intent": intent})

@app.route("/api/tramite", methods=["POST"])
def api_tramite():
    payload = request.get_json(force=True)
    tipo = payload.get("tipo")
    nombre = payload.get("nombre")
    grado = payload.get("grado")
    channel = payload.get("channel", "web")
    if not tipo or not nombre or not grado:
        return jsonify({"ok": False, "error": "Faltan campos: tipo, nombre o grado"}), 400

    text = f"{tipo} - {nombre} - {grado}"
    save_event("tramite_submitted", intent=tipo, text=text, channel=channel)
    return jsonify({"ok": True, "message": "Trámite registrado (simulado)"}), 201

@app.route("/api/logs", methods=["GET"])
def api_logs():
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT id, event_type, intent, text, channel, timestamp FROM events ORDER BY timestamp DESC LIMIT 1000")
    rows = cur.fetchall()
    result = [dict(r) for r in rows]
    return jsonify(result)



# --- servir archivos estáticos del frontend (opcional) ---
# Asume que la carpeta `frontend` está UN NIVEL arriba de `backend`
from flask import send_from_directory, abort

FRONTEND_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "frontend"))

@app.route("/", methods=["GET"])
def serve_root():
    # Si existe pagina.html o index.html, la servimos
    for fname in ("pagina.html", "index.html"):
        fpath = os.path.join(FRONTEND_DIR, fname)
        if os.path.exists(fpath):
            return send_from_directory(FRONTEND_DIR, fname)
    return abort(404)

@app.route("/<path:filename>", methods=["GET"])
def serve_frontend_file(filename):
    # Evita servir rutas fuera de la carpeta frontend
    safe_path = os.path.join(FRONTEND_DIR, filename)
    if os.path.commonpath([FRONTEND_DIR, os.path.normpath(safe_path)]) != FRONTEND_DIR:
        return abort(403)
    if os.path.exists(safe_path):
        return send_from_directory(FRONTEND_DIR, filename)
    return abort(404)

# -------------------------
# Main
# -------------------------
if __name__ == "__main__":
    # Asegurarnos de que la DB exista y la tabla también
    init_db()
    print("Iniciando EduBot backend en http://127.0.0.1:5000")
    app.run(debug=True, host="0.0.0.0", port=5000)

# -------------------------
# Creacion Endpoint Api-chat para conectar con el frontend del JS
#------------------------- 
@app.route("/api/chat", methods=["POST"])
def api_chat():
    data = request.get_json()
    pregunta = data.get("pregunta", "")

#--------------------------
# Simulacion de respuestas simple    
#-------------------------
    if "horario" in pregunta.lower():
        respuesta = "El horario escolar es de lunes a viernes de 7:00 am. 2:00 p.m."
    elif "matrícula" in pregunta.lower():
        respuesta = "Las matriculas estaran abiertas del 10 al 25 de enero."
    else:
        respuesta = "Lo siento, no tengo la información que buscas. Por favor, contacta a la administración."
    return jsonify({"respuesta": respuesta})