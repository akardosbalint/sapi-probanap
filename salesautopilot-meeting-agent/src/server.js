import express from "express";
import { processMeetingTranscript } from "./agent.js";
import { createMeetingItem } from "./monday.js";

const app = express();
app.use(express.json({ limit: "10mb" }));

// Make.com ezt a végpontot hívja: transcript elemzés + Monday item létrehozás egy lépésben
app.post("/process-transcript", async (req, res) => {
  const { transcript, title, drive_link } = req.body;

  if (!transcript) {
    return res.status(400).json({ error: "Hiányzó transcript" });
  }

  console.log(`Feldolgozás: ${title}`);

  try {
    // 1. Claude agent elemzés
    const analysis = await processMeetingTranscript(transcript, drive_link);
    const ajanlas = analysis["ajanlás"] ?? analysis["ajanlас"] ?? "";
    console.log(`Score: ${analysis.osszesitett_pont}/100 - ${ajanlas}`);

    // 2. Monday.com item létrehozása
    const itemId = await createMeetingItem(analysis, title);
    console.log(`Monday item létrehozva: ${itemId}`);

    res.json({ success: true, itemId, score: analysis.osszesitett_pont });
  } catch (err) {
    console.error("Hiba:", err.message);
    res.status(500).json({ error: err.message });
  }
});

// GET /health
app.get("/health", (_, res) => res.json({ status: "ok" }));

export { app };
