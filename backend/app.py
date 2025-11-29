# backend/app.py
from flask import Flask, request, jsonify, g, send_from_directory, abort
from flask_cors import CORS
import sqlite3
import time
import os
import subprocess
import re
import json
import logging

# Configuración básica
logging.basicConfig(level=logging.INFO)
DB_PATH = os.path.join(os.path.dirname(__file__), "edubot.db")
TRAMITES_DB_PATH = os.path.join(os.path.dirname(__file__), "tramites.db")
PDF_DIR = os.path.join(os.path.dirname(__file__), "pdfs")
os.makedirs(PDF_DIR, exist_ok=True)

app = Flask(__name__, static_folder=None)
CORS(app)

# -----------------------
# Helpers SQLite
# -----------------------
def get_db():
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES)
        db.row_factory = sqlite3.Row
    return db

def get_tramites_db():
    db = sqlite3.connect(TRAMITES_DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES)
    db.row_factory = sqlite3.Row
    return db

def init_db():
    db = sqlite3.connect(DB_PATH)
    cur = db.cursor()
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

def init_tramites_db():
    db = sqlite3.connect(TRAMITES_DB_PATH)
    cur = db.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS tramites (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tipo TEXT,
        nombre TEXT,
        grado TEXT,
        extra TEXT,
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
    try:
        db = get_db()
        cur = db.cursor()
        cur.execute("""
            INSERT INTO events (event_type, intent, text, channel, timestamp)
            VALUES (?, ?, ?, ?, ?)
        """, (event_type, intent, text, channel, int(time.time() * 1000)))
        db.commit()
    except Exception as e:
        logging.exception("Error guardando evento: %s", e)

# -----------------------
# Intent detector (mock)
# -----------------------
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

# -----------------------
# Ollama helper (robusto)
# -----------------------
def ollama_intent(texto):
    prompt = f"""
Eres un asistente educativo amable, claro y directo.
Responde de forma breve y precisa a la siguiente pregunta sin hacer preguntas de vuelta.
Pregunta: {texto}
Respuesta:
"""

    try:
        result = subprocess.run(
            ["ollama", "run", "llama3.2:1b", "--", prompt],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            timeout=45,
            env={**os.environ, "OLLAMA_OPTIONS": "{\"num_predict\": 100}"}
        )

        raw = result.stdout.strip()
        return "respuesta_directa", raw

    except subprocess.TimeoutExpired:
        return "error", "Lo siento, el modelo tardó demasiado en responder."

    except Exception as e:
        print("Error en Ollama:", e)
        return "error", "Hubo un problema con el servicio de IA."

# -----------------------
# PDF generator (simple)
# -----------------------
def generate_tramite_pdf(tramite_id, tipo, data):
    pdf_path = os.path.join(PDF_DIR, f"tramite_{tramite_id}.pdf")
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
        c = canvas.Canvas(pdf_path, pagesize=A4)
        width, height = A4

        c.setFont("Helvetica-Bold", 14)
        c.drawString(40, height - 60, "Gestor de Trámites - Institución Educativa")
        c.setFont("Helvetica", 10)
        c.drawString(40, height - 80, f"Trámite: {tipo}")
        c.drawString(40, height - 95, f"Fecha: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        c.line(40, height - 100, width - 40, height - 100)

        y = height - 130
        c.setFont("Helvetica", 11)
        for k, v in (data or {}).items():
            c.drawString(50, y, f"{k}: {v}")
            y -= 18
            if y < 60:
                c.showPage()
                y = height - 60

        c.showPage()
        c.save()
        return pdf_path
    except Exception as e:
        logging.warning("No se pudo generar PDF con reportlab: %s. Guardando fallback.", e)
        with open(pdf_path, "w", encoding="utf-8") as f:
            f.write("Gestor de Trámites - Documento (fallback)\n\n")
            f.write(f"Trámite: {tipo}\n")
            f.write(f"Fecha: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            for k, v in (data or {}).items():
                f.write(f"{k}: {v}\n")
        return pdf_path

# -----------------------
# Endpoints
# -----------------------

@app.route("/api/chat", methods=["POST"])
def api_chat():
    payload = request.get_json() or {}
    pregunta = payload.get("pregunta", "")
    if "horario" in pregunta.lower():
        respuesta = "El horario escolar es de lunes a viernes de 7:00 am a 2:00 pm."
    elif "matrícula" in pregunta.lower() or "matricula" in pregunta.lower():
        respuesta = "Las matrículas estarán abiertas del 10 al 25 de enero."
    else:
        respuesta = "Lo siento, no tengo esa información. Consulta administración."
    return jsonify({"respuesta": respuesta})

@app.route("/api/message", methods=["POST"])
def api_message():
    payload = request.get_json(force=True) or {}
    text = payload.get("text", "")
    channel = payload.get("channel", "web")

    save_event("message_sent", text=text, channel=channel)

    intent, reply = ollama_intent(text)
    if intent == "desconocido" and reply.strip() == "":
        intent, reply = detect_intent(text)

    save_event("message_received", intent=intent, text=reply, channel=channel)

    return jsonify({"reply": reply, "intent": intent})

# ✅ NUEVO: Usa tramites.db en lugar de edubot.db
@app.route("/api/tramite", methods=["POST"])
def api_tramite():
    payload = request.get_json(force=True) or {}
    tipo = payload.get("tipo")
    nombre = payload.get("nombre")
    grado = payload.get("grado")
    extra = payload.copy()
    for k in ("tipo", "nombre", "grado"):
        extra.pop(k, None)

    if not tipo or not nombre or not grado:
        return jsonify({"ok": False, "error": "Faltan campos: tipo, nombre o grado"}), 400

    try:
        db = get_tramites_db()
        cur = db.cursor()
        cur.execute("""
            INSERT INTO tramites (tipo, nombre, grado, extra, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (tipo, nombre, grado, json.dumps(extra), int(time.time())))
        tramite_id = cur.lastrowid
        db.commit()
        db.close()

        save_event("tramite_submitted", intent=tipo, text=f"{tipo}-{nombre}-{grado}")

        pdf_path = generate_tramite_pdf(tramite_id, tipo, {"nombre": nombre, "grado": grado, **extra})

        logging.info("Trámite %s guardado en tramites.db. PDF: %s", tramite_id, pdf_path)
        return jsonify({"ok": True, "id": tramite_id, "pdf": os.path.basename(pdf_path)})
    except Exception as e:
        logging.exception("Error registrando trámite: %s", e)
        return jsonify({"ok": False, "error": "Error interno al registrar trámite"}), 500

# ✅ NUEVO: Usa tramites.db
@app.route("/api/tramites", methods=["GET"])
def api_list_tramites():
    try:
        db = get_tramites_db()
        cur = db.cursor()
        cur.execute("SELECT id, tipo, nombre, grado, extra, created_at FROM tramites ORDER BY created_at DESC")
        rows = [dict(r) for r in cur.fetchall()]
        db.close()
        return jsonify(rows)
    except Exception as e:
        logging.exception("Error listando trámites: %s", e)
        return jsonify([]), 500

@app.route("/api/logs", methods=["GET"])
def api_logs():
    try:
        db = get_db()
        cur = db.cursor()
        cur.execute("SELECT id, event_type, intent, text, channel, timestamp FROM events ORDER BY timestamp DESC LIMIT 1000")
        rows = [dict(r) for r in cur.fetchall()]
        return jsonify(rows)
    except Exception as e:
        logging.exception("Error obteniendo logs: %s", e)
        return jsonify([]), 500

@app.route("/api/ollama-chat", methods=["POST"])
def api_ollama_chat():
    payload = request.get_json(force=True) or {}
    pregunta = payload.get("pregunta", "")
    if not pregunta:
        return jsonify({"error": "Falta pregunta"}), 400

    intent, respuesta = ollama_intent(pregunta)
    save_event("ollama_question", text=pregunta)
    save_event("ollama_answer", text=respuesta)
    return jsonify({"pregunta": pregunta, "respuesta": respuesta, "intent": intent})

@app.route("/api/descargar-pdf/<int:tramite_id>", methods=["GET"])
def descargar_pdf(tramite_id):
    pdf_filename = f"tramite_{tramite_id}.pdf"
    pdf_path = os.path.join(PDF_DIR, pdf_filename)
    if not os.path.exists(pdf_path):
        return jsonify({"error": "PDF no encontrado"}), 404
    return send_from_directory(PDF_DIR, pdf_filename, as_attachment=True)

# -----------------------
# Servir frontend estático (opcional)
# -----------------------
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

# -----------------------
# MAIN
# -----------------------
if __name__ == "__main__":
    init_db()
    init_tramites_db()
    logging.info("Iniciando EduBot backend en http://127.0.0.1:5000 ")
    app.run(debug=True, host="0.0.0.0", port=5000)