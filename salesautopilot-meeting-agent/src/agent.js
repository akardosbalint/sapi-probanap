import Anthropic from "@anthropic-ai/sdk";
import dotenv from "dotenv";
dotenv.config();

const client = new Anthropic();

const SYSTEM_PROMPT = `You are a JSON-only API. You must respond with raw JSON only. No markdown, no backticks, no explanations. Your entire response must be a single valid JSON object starting with { and ending with }.`;

const KNOWLEDGE_PROMPT = `Az alábbi szövegből gyűjtsd ki az összes önálló, hasznos tudáselemet. Minden tudáselem egy konkrét tanács, módszer, szabály, magyarázat vagy felismerés legyen, amit valaki hasznosítani tud.

NEM kell: napirend, köszöntő, technikai problémák, bemutatkozások, időpont-egyeztetések.
IGEN kell: minden konkrét szakmai tudás, tanács, magyarázat, best practice.

A JSON struktúra:
{
  "tudaselemek": [
    {
      "cim": "Rövid, tömör cím",
      "tartalom": "A tudáselem részletes kifejtése 2-4 mondatban, önállóan érthető formában",
      "kategoria": "pl. Email marketing / Integráció / Automatizálás / Stratégia / Technikai beállítás",
      "hasznossagi_pont": 1-10,
      "miert_hasznos": "1 mondatban: kinek és miért releváns ez a tudás"
    }
  ],
  "osszesen": 0,
  "legfontosabb_tanuls": "A szöveg egyetlen legfontosabb üzenete 1-2 mondatban"
}

Pontozási szabályok:
- 9-10: azonnal alkalmazható, konkrét lépés, általánosan érvényes
- 7-8: fontos tanács, de kontextusfüggő vagy előismeret kell
- 4-6: hasznos magyarázat, de nem közvetlen akció
- 1-3: általános, közismert vagy csak szűk célcsoportnak releváns

Rendezd a tudáselemeket hasznossági pont szerint csökkenő sorrendbe.

Szöveg:`;

export async function processMeetingTranscript(transcriptText, driveLink = "") {
  const message = await client.messages.create({
    model: "claude-sonnet-4-6",
    max_tokens: 4000,
    system: SYSTEM_PROMPT,
    messages: [
      {
        role: "user",
        content: `${KNOWLEDGE_PROMPT}\n${transcriptText}`,
      },
    ],
  });

  const responseText = message.content[0].text;

  const jsonMatch = responseText.match(/\{[\s\S]*\}/);
  if (!jsonMatch) {
    throw new Error(`Nem sikerült JSON-t kinyerni a válaszból:\n${responseText}`);
  }

  const result = JSON.parse(jsonMatch[0]);

  return {
    ...result,
    drive_link: driveLink,
    feldolgozas_datuma: new Date().toISOString(),
  };
}
