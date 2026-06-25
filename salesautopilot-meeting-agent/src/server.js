import express from "express";
import { processMeetingTranscript } from "./processor.js";
import { createMeetingItem } from "./monday.js";

const app = express();
app.use(express.json({ limit: "10mb" }));

// POST /analyze
// Body: { transcript, drive_link?, meeting_title?, monday?: true }
app.post("/analyze", async (req, res) => {
  const {
    transcript,
    drive_link = "",
    meeting_title = `Meeting – ${new Date().toLocaleDateString("hu-HU")}`,
    monday = false,
  } = req.body;

  if (!transcript || typeof transcript !== "string" || !transcript.trim()) {
    return res.status(400).json({ error: 'A "transcript" mező kötelező és nem lehet üres.' });
  }

  try {
    const result = await processMeetingTranscript(transcript, drive_link);

    if (monday) {
      const mondayItemId = await createMeetingItem(result, meeting_title);
      result.monday_item_id = mondayItemId;
    }

    res.json(result);
  } catch (err) {
    console.error("Hiba:", err.message);
    res.status(500).json({ error: err.message });
  }
});

// GET /health
app.get("/health", (_, res) => {
  res.json({
    status: "ok",
    monday: !!(process.env.MONDAY_API_KEY && process.env.MONDAY_BOARD_ID),
  });
});

export { app };
