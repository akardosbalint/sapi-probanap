import axios from "axios";

const MONDAY_API_KEY = process.env.MONDAY_API_KEY;
const BOARD_ID = process.env.MONDAY_BOARD_ID;

const AJANLAS_MAP = {
  "Hírlevélbe mehet": "Kész",
  "Átdolgozás kell": "Folyamatban",
  "Nem releváns": "Nem releváns",
};

function mondayRequest(q, variables = {}) {
  if (!MONDAY_API_KEY) throw new Error("MONDAY_API_KEY nincs beállítva.");
  if (!BOARD_ID) throw new Error("MONDAY_BOARD_ID nincs beállítva.");

  return axios.post(
    "https://api.monday.com/v2",
    { query: q, variables },
    {
      headers: {
        Authorization: MONDAY_API_KEY,
        "Content-Type": "application/json",
      },
    }
  );
}

export async function createMeetingItem(analysisResult, meetingTitle) {
  // ajanlás / ajanlас (mindkét írásmód) elfogadása
  const ajanlasRaw = analysisResult["ajanlás"] ?? analysisResult["ajanlас"] ?? "";
  const statusLabel = AJANLAS_MAP[ajanlasRaw] ?? "Folyamatban";

  // 1. Item létrehozása
  const createRes = await mondayRequest(
    `mutation ($boardId: ID!, $itemName: String!) {
       create_item(board_id: $boardId, item_name: $itemName) { id }
     }`,
    { boardId: BOARD_ID, itemName: meetingTitle }
  );

  const createErrors = createRes.data.errors;
  if (createErrors?.length) {
    throw new Error(`Monday API hiba (create_item): ${JSON.stringify(createErrors)}`);
  }

  const itemId = createRes.data.data.create_item.id;

  // 2. Oszlopok feltöltése
  const t = analysisResult.tartalmi_scoring;
  const m = analysisResult.minosegi_scoring;

  const columnValues = JSON.stringify({
    szegmens: { label: analysisResult.szegmens },
    tartalmi_score: t.reszosszeg,
    minosegi_score: m.reszosszeg,
    osszesitett_score: analysisResult.osszesitett_pont,
    ajanlas: { label: statusLabel },
    indoklas:
      `${analysisResult.szegmens_indoklas}\n\n` +
      `Tartalmi scoring:\n` +
      `  Use-case: ${t.use_case.pont}/15 – ${t.use_case.indok}\n` +
      `  Iparági insight: ${t.iparagi_insight.pont}/15 – ${t.iparagi_insight.indok}\n` +
      `  Actionable tipp: ${t.actionable_tipp.pont}/10 – ${t.actionable_tipp.indok}\n` +
      `  Szegmens-relevancia: ${t.szegmens_relevancia.pont}/10 – ${t.szegmens_relevancia.indok}\n\n` +
      `Minőségi scoring:\n` +
      `  Konkrétság: ${m.konkrektsag.pont}/20 – ${m.konkrektsag.indok}\n` +
      `  Újszerűség: ${m.ujszeruseg.pont}/15 – ${m.ujszeruseg.indok}\n` +
      `  Hitelességi forrás: ${m.hitelessegi_forras.pont}/15 – ${m.hitelessegi_forras.indok}`,
    hirlevel_angle: analysisResult.hirlevel_angle,
    action_items: `• ${analysisResult.action_items.join("\n• ")}`,
    osszefoglalas: analysisResult.osszefoglalas,
    ...(analysisResult.drive_link && {
      drive_link: { url: analysisResult.drive_link, text: "Transcript" },
    }),
  });

  const updateRes = await mondayRequest(
    `mutation ($itemId: ID!, $columnValues: JSON!) {
       change_multiple_column_values(
         item_id: $itemId,
         board_id: ${BOARD_ID},
         column_values: $columnValues
       ) { id }
     }`,
    { itemId, columnValues }
  );

  const updateErrors = updateRes.data.errors;
  if (updateErrors?.length) {
    throw new Error(`Monday API hiba (change_multiple_column_values): ${JSON.stringify(updateErrors)}`);
  }

  return itemId;
}
