#!/usr/bin/env node
import dotenv from "dotenv";
dotenv.config();

import fs from "fs";
import readline from "readline";
import { processMeetingTranscript } from "./src/agent.js";

if (!process.env.ANTHROPIC_API_KEY) {
  console.error("HIBA: Az ANTHROPIC_API_KEY környezeti változó nincs beállítva.");
  process.exit(1);
}

function formatResult(result) {
  const t = result.tartalmi_scoring;
  const m = result.minosegi_scoring;
  const ajanlas = result["ajanlás"] ?? result["ajanlас"] ?? "–";

  return `
=== SALESAUTOPILOT TARTALOMSTRATÉGIAI ELEMZÉS ===
Feldolgozás : ${result.feldolgozas_datuma}
${result.drive_link ? `Drive link  : ${result.drive_link}` : ""}

1. ÖSSZEFOGLALÁS
${result.osszefoglalas}

2. SZEGMENS: (${result.szegmens})
${result.szegmens_indoklas}

3. TARTALMI SCORING
   Use-case/esettanulmány : ${t.use_case.pont}/15  – ${t.use_case.indok}
   Iparági insight        : ${t.iparagi_insight.pont}/15  – ${t.iparagi_insight.indok}
   Actionable tipp        : ${t.actionable_tipp.pont}/10  – ${t.actionable_tipp.indok}
   Szegmens-relevancia    : ${t.szegmens_relevancia.pont}/10  – ${t.szegmens_relevancia.indok}
   RÉSZÖSSZEG             : ${t.reszosszeg}/50

4. MINŐSÉGI SCORING
   Konkrétság             : ${m.konkrektsag.pont}/20  – ${m.konkrektsag.indok}
   Újszerűség             : ${m.ujszeruseg.pont}/15  – ${m.ujszeruseg.indok}
   Hitelességi forrás     : ${m.hitelessegi_forras.pont}/15  – ${m.hitelessegi_forras.indok}
   RÉSZÖSSZEG             : ${m.reszosszeg}/50

5. ÖSSZESÍTETT PONT: ${result.osszesitett_pont}/100
   AJÁNLÁS: ${ajanlas}

6. HÍRLEVÉL ANGLE
${result.hirlevel_angle}

7. ACTION ITEMS
${result.action_items.map((item, i) => `   ${i + 1}. ${item}`).join("\n")}
`.trim();
}

async function main() {
  const filePath = process.argv[2];
  const driveLink = process.argv[3] || "";

  const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
  const ask = (q) => new Promise((resolve) => rl.question(q, resolve));

  let transcript = "";

  if (filePath) {
    if (!fs.existsSync(filePath)) {
      console.error(`Fájl nem található: ${filePath}`);
      process.exit(1);
    }
    transcript = fs.readFileSync(filePath, "utf-8");
    console.log(`Transcript betöltve: ${filePath} (${transcript.length} karakter)\n`);
  } else {
    console.log('Illeszd be a transcript szövegét (zárd le "END" sorral):');
    const lines = [];
    for await (const line of rl) {
      if (line.trim() === "END") break;
      lines.push(line);
    }
    transcript = lines.join("\n");
  }

  if (!transcript.trim()) {
    console.error("Üres transcript. Kilépés.");
    rl.close();
    process.exit(1);
  }

  console.log("\nElemzés folyamatban...\n");

  try {
    const result = await processMeetingTranscript(transcript, driveLink);
    console.log(formatResult(result));

    const saveFile = await ask("\nMentsük JSON-ba? (fájlnév vagy üres = nem): ");
    if (saveFile.trim()) {
      fs.writeFileSync(saveFile.trim(), JSON.stringify(result, null, 2), "utf-8");
      console.log(`Mentve: ${saveFile.trim()}`);
    }
  } catch (err) {
    console.error("Hiba:", err.message);
  }

  rl.close();
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
