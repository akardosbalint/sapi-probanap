import dotenv from "dotenv";
dotenv.config();

import { app } from "./src/server.js";

const PORT = process.env.PORT || 3000;

if (!process.env.ANTHROPIC_API_KEY) {
  console.error("HIBA: Az ANTHROPIC_API_KEY környezeti változó nincs beállítva.");
  process.exit(1);
}

app.listen(PORT, () => {
  console.log(`SalesAutopilot Meeting Agent fut: http://localhost:${PORT}`);
  console.log("  POST /process-transcript  { transcript, title, drive_link }");
  console.log("  GET  /health");
});
