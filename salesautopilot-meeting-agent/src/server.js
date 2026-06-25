const express = require('express');
const { SalesAutopilotAgent } = require('./agent');

const app = express();
app.use(express.json({ limit: '10mb' }));

const sessions = new Map();

function getOrCreateSession(sessionId) {
  if (!sessions.has(sessionId)) {
    sessions.set(sessionId, new SalesAutopilotAgent());
  }
  return sessions.get(sessionId);
}

// POST /analyze – transcript elemzés
app.post('/analyze', async (req, res) => {
  const { transcript, sessionId = 'default' } = req.body;

  if (!transcript || typeof transcript !== 'string' || transcript.trim().length === 0) {
    return res.status(400).json({ error: 'A "transcript" mező kötelező és nem lehet üres.' });
  }

  const agent = getOrCreateSession(sessionId);
  agent.resetConversation();

  try {
    const result = await agent.analyzeTranscript(transcript);
    res.json({ sessionId, ...result });
  } catch (err) {
    console.error('Elemzési hiba:', err.message);
    res.status(500).json({ error: err.message });
  }
});

// POST /followup – folytató kérdés ugyanabban a session-ben
app.post('/followup', async (req, res) => {
  const { question, sessionId = 'default' } = req.body;

  if (!question || typeof question !== 'string' || question.trim().length === 0) {
    return res.status(400).json({ error: 'A "question" mező kötelező és nem lehet üres.' });
  }

  const agent = getOrCreateSession(sessionId);

  try {
    const result = await agent.followUp(question);
    res.json({ sessionId, ...result });
  } catch (err) {
    console.error('Folytatókérdés hiba:', err.message);
    res.status(500).json({ error: err.message });
  }
});

// DELETE /session/:id – session törlése
app.delete('/session/:id', (req, res) => {
  const { id } = req.params;
  sessions.delete(id);
  res.json({ message: `Session "${id}" törölve.` });
});

// GET /health
app.get('/health', (_, res) => {
  res.json({ status: 'ok', sessions: sessions.size });
});

module.exports = { app };
