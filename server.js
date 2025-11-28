const express = require("express");
const cors = require("cors");
const db = require("./backend/database");

const app = express();

// ⭐ Recomendado: permitir solo tu frontend
app.use(
  cors({
    origin: "http://127.0.0.1:5500",
  })
);

app.use(express.json());

// -------------------------------------
// GUARDAR TRÁMITE
// -------------------------------------
app.post("/api/guardar-tramite", (req, res) => {
  const { tipo, nombre, documento, grado, extra } = req.body;

  if (!tipo) {
    return res.status(400).json({ error: "Falta el campo: tipo" });
  }

  const fecha = new Date().toISOString();

  const sql = `
    INSERT INTO tramites (tipo, nombre, documento, grado, extra, fecha)
    VALUES (?, ?, ?, ?, ?, ?)
  `;

  db.run(
    sql,
    [
      tipo,
      nombre || "",
      documento || "",
      grado || "",
      JSON.stringify(extra) || "{}",
      fecha,
    ],
    function (err) {
      if (err) {
        console.error("❌ Error guardando trámite:", err);
        return res.status(500).json({ error: "Error al guardar trámite" });
      }

      res.json({ success: true, id: this.lastID });
    }
  );
});

// -------------------------------------
// PUERTO
// -------------------------------------
app.listen(3000, () => {
  console.log("🚀 Servidor backend escuchando en http://localhost:3000");
});
