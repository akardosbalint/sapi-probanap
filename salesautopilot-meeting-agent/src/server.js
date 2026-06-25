import express from "express";
import axios from "axios";
import { processMeetingTranscript } from "./agent.js";
import { createMeetingItem } from "./monday.js";

const app = express();
app.use(express.json({ limit: "10mb" }));

// Make.com hívja ezt a végpontot, miután kinyerte a Google Docs szövegét:
//   { transcript, title, drive_link }
//
// Flow:
//   1. Claude elemzés (scoring, szegmens, action items)
//   2. Monday.com item létrehozása
//   3. Make.com webhook trigger → következő scenario indul
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

    // 3. Make.com trigger – következő scenario indítása
    if (process.env.MAKE_WEBHOOK_URL) {
      await axios.post(process.env.MAKE_WEBHOOK_URL, {
        itemId,
        score: analysis.osszesitett_pont,
        ajanlas,
        szegmens: analysis.szegmens,
        title,
        drive_link,
        feldolgozas_datuma: analysis.feldolgozas_datuma,
      });
      console.log("Make.com trigger elküldve.");
    }

    res.json({ success: true, itemId, score: analysis.osszesitett_pont });
  } catch (err) {
    console.error("Hiba:", err.message);
    res.status(500).json({ error: err.message });
  }
});

// GET /health
app.get("/health", (_, res) =>
  res.json({
    status: "ok",
    make_webhook: !!process.env.MAKE_WEBHOOK_URL,
    monday: !!(process.env.MONDAY_API_KEY && process.env.MONDAY_BOARD_ID),
  })
);

export { app };
