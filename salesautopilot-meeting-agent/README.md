# SalesAutopilot Meeting Agent

Meeting transcript-eket elemző AI asszisztens, amely SalesAutopilot tartalomstratégiai szempontból értékeli a felvételeket.

## Telepítés

```bash
npm install
cp .env.example .env
# Töltsd ki az .env fájlban az ANTHROPIC_API_KEY értékét
```

## Használat

### REST API szerver

```bash
npm start
# Fut: http://localhost:3000
```

**Végpontok:**

```
POST /analyze
  Body: { "transcript": "...", "sessionId": "opcionális" }
  → Elemzi a transcript-et, visszaadja a strukturált riportot

POST /followup
  Body: { "question": "...", "sessionId": "opcionális" }
  → Folytató kérdés az előző elemzés kontextusában

DELETE /session/:id
  → Session törlése (új elemzéshez)

GET /health
  → Szerver státusz
```

**Példa hívás:**

```bash
curl -X POST http://localhost:3000/analyze \
  -H "Content-Type: application/json" \
  -d '{"transcript": "Speaker1: Sziasztok!...", "sessionId": "session1"}'
```

### Parancssori (CLI) mód

```bash
# Fájlból
npm run cli -- transcript.txt

# Interaktív (beillesztés stdin-re)
npm run cli
```

## Kimeneti struktúra

Az agent minden transcript-hez az alábbi 7 pontot elemzi:

1. **Összefoglalás** – résztvevők, cél, top 3 pont (max 150 szó)
2. **Szegmens besorolás** – A/B/C/D kategória indoklással
3. **Tartalmi scoring** – 0–50 pont (use-case, insight, tipp, relevancia)
4. **Minőségi scoring** – 0–50 pont (konkrétság, újszerűség, hitelességi forrás)
5. **Összesített pontszám** – 0–100 + ajánlás
6. **Hírlevél angle** – főüzenet és célcsoport javaslat
7. **Action items** – követő lépések táblázatosan

## Architektúra

```
salesautopilot-meeting-agent/
├── index.js          # HTTP szerver belépési pont
├── cli.js            # Parancssori felület
├── src/
│   ├── agent.js      # SalesAutopilotAgent osztály (Anthropic SDK, multi-turn)
│   ├── server.js     # Express route-ok és session kezelés
│   └── systemPrompt.js  # Agent személyisége és output formátum
├── .env.example
└── package.json
```
