import express from "express";
import { processMeetingTranscript } from "./processor.js";

const app = express();
app.use(express.json({ limit: "10mb" }));

// POST /analyze
// Body: { transcript, drive_link? }
// Response: teljes elemzési JSON – Make.com ezt kapja és továbbítja Monday-nek
app.post("/analyze", async (req, res) => {
  const { transcript, drive_link = "" } = req.body;

  if (!transcript || typeof transcript !== "string" || !transcript.trim()) {
    return res.status(400).json({ error: 'A "transcript" mező kötelező és nem lehet üres.' });
  }

  try {
    const result = await processMeetingTranscript(transcript, drive_link);
    res.json(result);
  } catch (err) {
    console.error("Hiba:", err.message);
    res.status(500).json({ error: err.message });
  }
});

// GET /health
app.get("/health", (_, res) => res.json({ status: "ok" }));

export { app };
