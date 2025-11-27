// -------------------------------
// MENU ACTIVO
// -------------------------------
// --------- CONTROL DE MENÚ Y SECCIONES ---------

const menuButtons = document.querySelectorAll(".menu-item");
const sections = document.querySelectorAll(".content-section");

menuButtons.forEach((btn) => {
  btn.addEventListener("click", () => {
    // Quitar activo a todos
    menuButtons.forEach((item) => item.classList.remove("active"));

    // Activar botón seleccionado
    btn.classList.add("active");

    // Mostrar sección correspondiente
    sections.forEach((sec) => sec.classList.remove("active-section"));

    const text = btn.textContent.trim();

    if (text.includes("Chat Asistente")) {
      document.getElementById("chat-section").classList.add("active-section");
    }

    if (text.includes("Trámites")) {
      document
        .getElementById("tramites-section")
        .classList.add("active-section");
    }
  });
});

// -------------------------------
// UTILIDADES
// -------------------------------

// Función que devuelve la hora actual en formato "hh:mm a. m."
function getCurrentTime() {
  const now = new Date();
  let hours = now.getHours();
  const minutes = now.getMinutes().toString().padStart(2, "0");

  const ampm = hours >= 12 ? "p. m." : "a. m.";
  hours = hours % 12 || 12;

  return `${hours}:${minutes} ${ampm}`;
}

// Obtiene el contenedor del chat
const chatWindow = document.querySelector(".chat-window");

// Input y botón
const input = document.querySelector(".input-box");
const sendBtn = document.querySelector(".send-btn");

// -------------------------------
// FUNCIÓN PARA AGREGAR MENSAJE DEL USUARIO
// -------------------------------
function addUserMessage(text) {
  const message = document.createElement("div");
  message.classList.add("message", "user-message");

  message.innerHTML = `
    ${text}
    <span class="timestamp">${getCurrentTime()}</span>
  `;

  chatWindow.appendChild(message);
  scrollToBottom();
}

// -------------------------------
// FUNCIÓN PARA AGREGAR MENSAJE DEL BOT
// -------------------------------
function addBotMessage(text) {
  const message = document.createElement("div");
  message.classList.add("message", "bot-message");

  message.innerHTML = `
    <div class="bot-avatar">🤖</div>
    <div class="bubble">
      ${text}
      <span class="timestamp">${getCurrentTime()}</span>
    </div>
  `;

  chatWindow.appendChild(message);
  scrollToBottom();
}

// -------------------------------
// BOT RESPUESTAS SIMULADAS
// -------------------------------
function botReply(userText) {
  userText = userText.toLowerCase();

  if (userText.includes("horario")) {
    return "El horario escolar es de lunes a viernes de 7:00 a.m. a 2:00 p.m.";
  }
  if (userText.includes("matrícula")) {
    return "La matrícula se realiza en línea a través del portal educativo oficial.";
  }
  if (userText.includes("constancia")) {
    return "Puedes solicitar constancias en la oficina administrativa o en línea.";
  }
  if (userText.includes("calendario")) {
    return "El calendario escolar está disponible en el sitio web oficial.";
  }

  return "Puedo ayudarte con información sobre matrículas, horarios, constancias, rutas y más.";
}

// -------------------------------
// ENVIAR MENSAJE
// -------------------------------
function sendMessage() {
  const text = input.value.trim();
  if (text === "") return;

  addUserMessage(text);

  // Respuesta del bot luego de una breve espera
  setTimeout(() => {
    const reply = botReply(text);
    addBotMessage(reply);
  }, 600);

  input.value = "";
}

// -------------------------------
// EVENTOS
// -------------------------------
sendBtn.addEventListener("click", sendMessage);

input.addEventListener("keypress", function (e) {
  if (e.key === "Enter") sendMessage();
});

// Mantener el scroll abajo siempre
function scrollToBottom() {
  chatWindow.scrollTop = chatWindow.scrollHeight;
}

// -------------------------------
// PONER HORA AL MENSAJE INICIAL
// -------------------------------
document.querySelectorAll(".timestamp").forEach((ts) => {
  ts.textContent = getCurrentTime();
});

// -------------------------------
// Conectar Frontend con Backend
// -------------------------------
async function enviarMensaje(texto) {
  const respuesta = await fetch("/api/chat", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ pregunta: texto }),
  });
  return respuesta.json();
}
