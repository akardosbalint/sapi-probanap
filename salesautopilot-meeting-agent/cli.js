#!/usr/bin/env node
require('dotenv').config();
const fs = require('fs');
const readline = require('readline');
const { SalesAutopilotAgent } = require('./src/agent');

async function main() {
  if (!process.env.ANTHROPIC_API_KEY) {
    console.error('HIBA: Az ANTHROPIC_API_KEY környezeti változó nincs beállítva.');
    process.exit(1);
  }

  const agent = new SalesAutopilotAgent();
  const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
  const ask = (q) => new Promise((resolve) => rl.question(q, resolve));

  console.log('=== SalesAutopilot Tartalomstratégiai Asszisztens ===\n');

  // Transcript forrása: fájl argumentumból vagy stdin
  let transcript = '';
  const filePath = process.argv[2];

  if (filePath) {
    if (!fs.existsSync(filePath)) {
      console.error(`Fájl nem található: ${filePath}`);
      process.exit(1);
    }
    transcript = fs.readFileSync(filePath, 'utf-8');
    console.log(`Transcript betöltve: ${filePath} (${transcript.length} karakter)\n`);
  } else {
    console.log('Illeszd be a transcript szövegét (zárd le egy üres sorral + "END" beírásával):');
    const lines = [];
    for await (const line of rl) {
      if (line.trim() === 'END') break;
      lines.push(line);
    }
    transcript = lines.join('\n');
  }

  if (!transcript.trim()) {
    console.error('Üres transcript. Kilépés.');
    rl.close();
    process.exit(1);
  }

  console.log('\nElemzés folyamatban...\n');
  try {
    const result = await agent.analyzeTranscript(transcript);
    console.log(result.analysis);
    console.log(`\n[Token használat – input: ${result.usage.input_tokens}, output: ${result.usage.output_tokens}]`);
  } catch (err) {
    console.error('Elemzési hiba:', err.message);
    rl.close();
    process.exit(1);
  }

  // Interaktív folytató kérdések
  console.log('\n--- Folytató kérdések (üres sor = kilépés) ---');
  while (true) {
    const question = await ask('\nKérdés: ');
    if (!question.trim()) break;

    try {
      const result = await agent.followUp(question);
      console.log('\n' + result.answer);
      console.log(`[Token: +${result.usage.output_tokens}]`);
    } catch (err) {
      console.error('Hiba:', err.message);
    }
  }

  console.log('\nViszlát!');
  rl.close();
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
