import Anthropic from "@anthropic-ai/sdk";
import dotenv from "dotenv";
dotenv.config();

const client = new Anthropic();

const SCORING_PROMPT = `Te egy SalesAutopilot tartalomstratégiai asszisztens vagy.
Az alábbi meeting transcript egy partner/integrációs megbeszélésről készült.

FELADATOD - válaszolj KIZÁRÓLAG valid JSON formátumban, semmi más szöveg:

{
  "osszefoglalas": "max 150 szó: ki volt jelen, mi volt a cél, 3 legfontosabb pont",
  "szegmens": "A|B|C|D",
  "szegmens_indoklas": "1-2 mondat miért",
  "tartalmi_scoring": {
    "use_case": { "pont": 0-15, "indok": "..." },
    "iparagi_insight": { "pont": 0-15, "indok": "..." },
    "actionable_tipp": { "pont": 0-10, "indok": "..." },
    "szegmens_relevancia": { "pont": 0-10, "indok": "..." },
    "reszosszeg": 0-50
  },
  "minosegi_scoring": {
    "konkrektsag": { "pont": 0-20, "indok": "..." },
    "ujszeruseg": { "pont": 0-15, "indok": "..." },
    "hitelessegi_forras": { "pont": 0-15, "indok": "..." },
    "reszosszeg": 0-50
  },
  "osszesitett_pont": 0-100,
  "ajanlас": "Hírlevélbe mehet|Átdolgozás kell|Nem releváns",
  "hirlevel_angle": "2-3 mondat a javasolt feldolgozási irányról",
  "action_items": ["item1", "item2"]
}`;

export async function processMeetingTranscript(transcriptText, driveLink = "") {
  const message = await client.messages.create({
    model: "claude-sonnet-4-6",
    max_tokens: 2000,
    messages: [
      {
        role: "user",
        content: `${SCORING_PROMPT}\n\nTRANSCRIPT:\n${transcriptText}`,
      },
    ],
  });

  const responseText = message.content[0].text;

  // JSON blokk kinyerése, ha a model mégis szöveget rak köré
  const jsonMatch = responseText.match(/\{[\s\S]*\}/);
  if (!jsonMatch) {
    throw new Error(`Nem sikerült JSON-t kinyerni a válaszból:\n${responseText}`);
  }

  const result = JSON.parse(jsonMatch[0]);

  // Számított összeg validáció
  const tartalmiOsszeg =
    (result.tartalmi_scoring?.use_case?.pont ?? 0) +
    (result.tartalmi_scoring?.iparagi_insight?.pont ?? 0) +
    (result.tartalmi_scoring?.actionable_tipp?.pont ?? 0) +
    (result.tartalmi_scoring?.szegmens_relevancia?.pont ?? 0);

  const minosegi =
    (result.minosegi_scoring?.konkrektsag?.pont ?? 0) +
    (result.minosegi_scoring?.ujszeruseg?.pont ?? 0) +
    (result.minosegi_scoring?.hitelessegi_forras?.pont ?? 0);

  return {
    ...result,
    tartalmi_scoring: {
      ...result.tartalmi_scoring,
      reszosszeg: tartalmiOsszeg,
    },
    minosegi_scoring: {
      ...result.minosegi_scoring,
      reszosszeg: minosegi,
    },
    osszesitett_pont: tartalmiOsszeg + minosegi,
    drive_link: driveLink,
    feldolgozas_datuma: new Date().toISOString(),
  };
}
