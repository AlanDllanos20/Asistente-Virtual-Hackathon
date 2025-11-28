const sqlite3 = require("sqlite3").verbose();

const db = new sqlite3.Database("./tramites.db", (err) => {
  if (err) console.error(err);
  console.log("📁 Base de datos SQLite conectada");
});

// Crear tabla si no existe
db.run(`
  CREATE TABLE IF NOT EXISTS tramites (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo TEXT,
    nombre TEXT,
    documento TEXT,
    grado TEXT,
    extra JSON,
    fecha TEXT
  )
`);

module.exports = db;
