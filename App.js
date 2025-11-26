// Seleccionar todos los botones del menú
const menuButtons = document.querySelectorAll(".menu-item");

menuButtons.forEach((btn) => {
  btn.addEventListener("click", () => {
    // Remover la clase active de todos
    menuButtons.forEach((b) => b.classList.remove("active"));

    // Agregar active solo al que se clicó
    btn.classList.add("active");
  });
});
