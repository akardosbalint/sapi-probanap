import express from "express";
import { processMeetingTranscript } from "./agent.js";

const app = express();
app.use(express.json({ limit: "10mb" }));

// Make.com hívja ezt a végpontot a Google Docs szövegével:
//   { transcript, title, drive_link }
// A válasz JSON-t Make.com közvetlenül a következő modulban használja.
app.post("/process-transcript", async (req, res) => {
  const { transcript, title, drive_link } = req.body;

  if (!transcript) {
    return res.status(400).json({ error: "Hiányzó transcript" });
  }

  console.log(`Feldolgozás: ${title}`);

  try {
    const analysis = await processMeetingTranscript(transcript, drive_link);
    const ajanlas = analysis["ajanlás"] ?? analysis["ajanlас"] ?? "";
    console.log(`Score: ${analysis.osszesitett_pont}/100 - ${ajanlas}`);

    res.json({ ...analysis, title });
  } catch (err) {
    console.error("Hiba:", err.message);
    res.status(500).json({ error: err.message });
  }
});

app.get("/health", (_, res) => res.json({ status: "ok" }));

export { app };
