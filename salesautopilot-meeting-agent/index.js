require('dotenv').config();
const { app } = require('./src/server');

const PORT = process.env.PORT || 3000;

if (!process.env.ANTHROPIC_API_KEY) {
  console.error('HIBA: Az ANTHROPIC_API_KEY környezeti változó nincs beállítva.');
  process.exit(1);
}

app.listen(PORT, () => {
  console.log(`SalesAutopilot Meeting Agent fut: http://localhost:${PORT}`);
  console.log('Elérhető végpontok:');
  console.log('  POST /analyze   – transcript elemzése');
  console.log('  POST /followup  – folytató kérdés');
  console.log('  DELETE /session/:id – session törlése');
  console.log('  GET  /health    – státusz');
});
