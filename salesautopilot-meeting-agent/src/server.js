import express from "express";
import axios from "axios";
import { processMeetingTranscript } from "./agent.js";

const app = express();
app.use(express.json({ limit: "10mb" }));

// Make.com hívja ezt a végpontot a Google Docs szövegével:
//   { transcript, title, drive_link }
//
// Flow:
//   1. Claude elemzés (scoring, szegmens, action items)
//   2. Make.com webhook trigger → következő scenario indul
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

    if (process.env.MAKE_WEBHOOK_URL) {
      await axios.post(process.env.MAKE_WEBHOOK_URL, {
        ...analysis,
        title,
      });
      console.log("Make.com trigger elküldve.");
    }

    res.json({ success: true, score: analysis.osszesitett_pont });
  } catch (err) {
    console.error("Hiba:", err.message);
    res.status(500).json({ error: err.message });
  }
});

app.get("/health", (_, res) =>
  res.json({ status: "ok", make_webhook: !!process.env.MAKE_WEBHOOK_URL })
);

export { app };
