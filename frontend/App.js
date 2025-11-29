// ===============================
// MENU ACTIVO
// ===============================
const menuButtons = document.querySelectorAll(".menu-item");
const sections = document.querySelectorAll(".content-section");

menuButtons.forEach((btn) => {
  btn.addEventListener("click", () => {
    menuButtons.forEach((item) => item.classList.remove("active"));
    btn.classList.add("active");

    sections.forEach((sec) => sec.classList.remove("active-section"));

    if (btn.textContent.includes("Chat Asistente")) {
      document.getElementById("chat-section").classList.add("active-section");
    }

    if (btn.textContent.includes("Trámites")) {
      document
        .getElementById("tramites-section")
        .classList.add("active-section");
    }
  });
});
// ===============================
// UTILIDADES
// ===============================
function getCurrentTime() {
  const now = new Date();
  let hours = now.getHours();
  const minutes = now.getMinutes().toString().padStart(2, "0");
  const ampm = hours >= 12 ? "p. m." : "a. m.";
  hours = hours % 12 || 12;
  return `${hours}:${minutes} ${ampm}`;
}

const chatWindow = document.querySelector(".chat-window");
const input = document.querySelector(".input-box");
const sendBtn = document.querySelector(".send-btn");

function scrollToBottom() {
  chatWindow.scrollTop = chatWindow.scrollHeight;
}

// ===============================
// MENSAJES
// ===============================
function addUserMessage(text) {
  const message = document.createElement("div");
  message.classList.add("message", "user-message");
  message.innerHTML = `${text}<span class="timestamp">${getCurrentTime()}</span>`;
  chatWindow.appendChild(message);
  scrollToBottom();
}

function addBotMessage(text) {
  const msg = document.createElement("div");
  msg.classList.add("message", "bot-message");
  msg.innerHTML = `
    <div class="bot-avatar">🤖</div>
    <div class="bubble">
      ${text}
      <span class="timestamp">${getCurrentTime()}</span>
    </div>
  `;
  chatWindow.appendChild(msg);
  scrollToBottom();
}

// ===============================
// CHAT CONECTADO A BACKEND FLASK
// ===============================
async function sendMessage() {
  const text = input.value.trim();
  if (!text) return;

  addUserMessage(text);
  input.value = "";

  try {
    const r = await fetch("http://127.0.0.1:5000/api/message", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });

    const data = await r.json();
    addBotMessage(data.reply);
  } catch (error) {
    addBotMessage("⚠ Error de conexión con el servidor.");
  }
}

sendBtn.addEventListener("click", sendMessage);
input.addEventListener("keypress", (e) => {
  if (e.key === "Enter") sendMessage();
});

// ===============================
// OLLAMA CHAT
// ===============================
async function preguntarOllama(texto) {
  const r = await fetch("http://127.0.0.1:5000/api/ollama-chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ pregunta: texto }),
  });

  const data = await r.json();
  addBotMessage(data.respuesta);
}

// ===============================
// TRÁMITES (MODAL)
// ===============================
const modal = document.getElementById("tramite-modal");
const modalTitle = document.getElementById("modal-title");
const extraFields = document.getElementById("extra-fields");
let selectedTramite = null;

document.querySelectorAll(".solicitar-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    selectedTramite = btn.dataset.tramite;
    modal.classList.remove("hidden");
    modalTitle.textContent = "Solicitud de " + formatTramite(selectedTramite);
    loadExtraFields(selectedTramite);
    document.getElementById("tramite-form").reset();
  });
});

document.getElementById("btn-cerrar").addEventListener("click", () => {
  modal.classList.add("hidden");
});

// ===============================
// CAMPOS EXTRAS
// ===============================
function loadExtraFields(type) {
  extraFields.innerHTML = "";

  if (type === "inasistencia") {
    extraFields.innerHTML = `
      <div class="form-group">
        <label>Fecha de inasistencia</label>
        <input type="date" name="fecha_inasistencia" required />
      </div>
      <div class="form-group">
        <label>Motivo</label>
        <textarea name="motivo" required></textarea>
      </div>
    `;
  }

  if (type === "calificaciones") {
    extraFields.innerHTML = `
      <div class="form-group">
        <label>Año escolar</label>
        <input type="number" name="anio" required />
      </div>
    `;
  }
}

function formatTramite(t) {
  return {
    constancia: "Constancia de Estudio",
    calificaciones: "Certificado de Calificaciones",
    inasistencia: "Reporte de Inasistencia",
    pazysalvo: "Paz y Salvo Académico",
  }[t];
}

// ===============================
// ENVIAR TRÁMITE Y DESCARGAR PDF
// ===============================
document.getElementById("btn-descargar").addEventListener("click", async () => {
  const data = Object.fromEntries(
    new FormData(document.getElementById("tramite-form")).entries()
  );

  const r = await fetch("http://127.0.0.1:5000/api/tramite", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ tipo: selectedTramite, ...data }),
  });

  const result = await r.json();

  if (!result.ok) {
    alert("Error al registrar el trámite");
    return;
  }

  // Descargar PDF desde Flask
  window.open(`http://127.0.0.1:5000/api/descargar-pdf/${result.id}`, "_blank");

  modal.classList.add("hidden");
});

// ===============================
// MODAL DE AVISO DE PRIVACIDAD
// ===============================

const avisoModal = document.getElementById("aviso-privacidad-modal");
const checkboxAviso = document.getElementById("acepto-aviso");
const btnCerrarAviso = document.getElementById("btn-cerrar-aviso");

// Mostrar modal al cargar si no ha sido aceptado
window.addEventListener("DOMContentLoaded", () => {
  avisoModal.style.display = "flex";
});

// Habilitar botón solo si acepta
checkboxAviso.addEventListener("change", () => {
  btnCerrarAviso.disabled = !checkboxAviso.checked;
});

// Cerrar y guardar aceptación
btnCerrarAviso.addEventListener("click", () => {
  localStorage.setItem("aviso-privacidad-aceptado", "true");
  avisoModal.style.display = "none";
});

// Función para abrir el modal desde el menú "Privacidad"
function abrirAvisoPrivacidad() {
  avisoModal.style.display = "flex";
}
