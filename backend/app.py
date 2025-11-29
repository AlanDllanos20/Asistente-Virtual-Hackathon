# backend/app.py
from flask import Flask, request, jsonify, g, send_from_directory, abort
from flask_cors import CORS
import sqlite3
import time
import os
import subprocess

DB_PATH = os.path.join(os.path.dirname(__file__), "edubot.db")

app = Flask(__name__)
CORS(app)

# ======================================================
# ===============  DATABASE HELPERS  ===================
# ======================================================

def get_db():
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES)
        db.row_factory = sqlite3.Row
    return db

def init_db():
    db = sqlite3.connect(DB_PATH)
    cur = db.cursor()

    # Tabla para logs/eventos
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

    # Tabla para trámites
    cur.execute("""
    CREATE TABLE IF NOT EXISTS tramites (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tipo TEXT,
        nombre TEXT,
        grado TEXT,
        created_at INTEGER
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
    cur.execute("""
        INSERT INTO events (event_type, intent, text, channel, timestamp)
        VALUES (?, ?, ?, ?, ?)
    """, (event_type, intent, text, channel, int(time.time() * 1000)))
    db.commit()


# ======================================================
# ===============  INTENT DETECTOR (MOCK) ==============
# ======================================================

SAMPLE_RESPONSES = [
    {"intent": "horario", "keywords": ["horario", "hora", "clase"], "reply": "El horario escolar es L-V 7:00 - 12:00."},
    {"intent": "matricula", "keywords": ["matrícula", "matricula", "inscripción"], "reply": "Para matricularte necesitas documento de identidad y el formulario de inscripción."},
    {"intent": "constancia", "keywords": ["constancia", "certificado"], "reply": "Puedes solicitar la constancia en la sección 'Trámites'."},
    {"intent": "calendario", "keywords": ["calendario", "fechas", "vacaciones"], "reply": "El calendario académico 2025 inicia el 10 de febrero."},
    {"intent": "ruta", "keywords": ["ruta", "bus", "transporte"], "reply": "Las rutas escolares se publican en secretaría."}
]

def detect_intent(text):
    t = (text or "").lower()
    for s in SAMPLE_RESPONSES:
        for k in s["keywords"]:
            if k in t:
                return s["intent"], s["reply"]
    return "fallback", "Lo siento, no entendí."


# ======================================================
# ====================  ENDPOINTS ======================
# ======================================================

# ---------- Chat simple ----------
@app.route("/api/chat", methods=["POST"])
def api_chat():
    data = request.get_json()
    pregunta = data.get("pregunta", "")

    if "horario" in pregunta.lower():
        respuesta = "El horario escolar es de lunes a viernes de 7:00 am a 2:00 pm."
    elif "matrícula" in pregunta.lower():
        respuesta = "Las matriculas estarán abiertas del 10 al 25 de enero."
    else:
        respuesta = "Lo siento, no tengo esa información. Consulta administración."

    return jsonify({"respuesta": respuesta})


# ---------- Chat con intents ----------
@app.route("/api/message", methods=["POST"])
def api_message():
    payload = request.get_json(force=True)
    text = payload.get("text", "")
    channel = payload.get("channel", "web")

    save_event("message_sent", text=text, channel=channel)

    intent, reply = detect_intent(text)

    save_event("message_received", intent=intent, text=reply, channel=channel)

    return jsonify({"reply": reply, "intent": intent})


# ---------- Registro de Trámite ----------
@app.route("/api/tramite", methods=["POST"])
def api_tramite():
    payload = request.get_json(force=True)
    tipo = payload.get("tipo")
    nombre = payload.get("nombre")
    grado = payload.get("grado")

    if not tipo or not nombre or not grado:
        return jsonify({"ok": False, "error": "Faltan campos"}), 400

    db = get_db()
    cur = db.cursor()
    cur.execute("""
        INSERT INTO tramites (tipo, nombre, grado, created_at)
        VALUES (?, ?, ?, ?)
    """, (tipo, nombre, grado, int(time.time())))
    db.commit()

    save_event("tramite_submitted", intent=tipo, text=f"{tipo}-{nombre}-{grado}")

    return jsonify({"ok": True, "message": "Trámite registrado"})


# ---------- LISTA DE TRÁMITES ----------
@app.route("/api/tramites", methods=["GET"])
def api_list_tramites():
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT * FROM tramites ORDER BY created_at DESC")
    rows = [dict(r) for r in cur.fetchall()]
    return jsonify(rows)


# ---------- Chat con OLLAMA ----------
@app.route("/api/ollama-chat", methods=["POST"])
def api_ollama_chat():
    data = request.get_json()
    pregunta = data.get("pregunta", "")

    if not pregunta:
        return jsonify({"error": "Falta pregunta"}), 400

    try:
        result = subprocess.run(
            ["ollama", "run", "llama3", pregunta],
            capture_output=True,
            text=True
        )

        respuesta = result.stdout.strip()

        save_event("ollama_question", text=pregunta)
        save_event("ollama_answer", text=respuesta)

        return jsonify({"pregunta": pregunta, "respuesta": respuesta})

    except Exception as e:
        return jsonify({"error": "Error llamando a Ollama", "detalle": str(e)}), 500


# ======================================================
# ===============  FRONTEND STATIC FILES  ==============
# ======================================================

FRONTEND_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "frontend"))

@app.route("/", methods=["GET"])
def serve_root():
    for fname in ("pagina.html", "index.html"):
        fpath = os.path.join(FRONTEND_DIR, fname)
        if os.path.exists(fpath):
            return send_from_directory(FRONTEND_DIR, fname)
    return abort(404)

@app.route("/<path:filename>", methods=["GET"])
def serve_frontend_file(filename):
    safe = os.path.join(FRONTEND_DIR, filename)
    if os.path.commonpath([FRONTEND_DIR, os.path.normpath(safe)]) != FRONTEND_DIR:
        return abort(403)
    if os.path.exists(safe):
        return send_from_directory(FRONTEND_DIR, filename)
    return abort(404)


# ======================================================
# =====================  MAIN  =========================
# ======================================================
if __name__ == "__main__":
    init_db()
    print("Iniciando EduBot backend en http://127.0.0.1:5000")
    app.run(debug=True, host="0.0.0.0", port=5000)


def ollama_intent(texto):
    prompt = f"""
Eres un asistente educativo del colegio. Analiza la siguiente pregunta y responde estrictamente en formato JSON con dos campos: 
- intent: la intención del usuario
- reply: la mejor respuesta según la pregunta

Las intenciones válidas son:
- horario
- matricula
- constancia
- calificaciones_doc
- inasistencia_doc
- pazysalvo
- tramites
- calendario
- ruta
- conversacion (para saludos o frases que no pidan información)
- desconocido (si no entiendes)

Pregunta del usuario:
"{texto}"

Responde SOLO el JSON.
"""

    result = subprocess.run(
        ["ollama", "run", "llama3", prompt],
        capture_output=True, text=True
    )

    raw = result.stdout.strip()

    try:
        import json
        data = json.loads(raw)
        return data.get("intent", "desconocido"), data.get("reply", "No entendí la solicitud.")
    except:
        return "desconocido", "No entendí, intenta preguntarlo de otra manera."
