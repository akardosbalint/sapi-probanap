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
  // analysisResult.ajanlас (cirill с) és ajanlás (ékezetes á) is előfordulhat –
  // mindkét kulcsot elfogadjuk
  const ajanlasRaw = analysisResult["ajanlás"] ?? analysisResult["ajanlас"] ?? "";
  const statusLabel = AJANLAS_MAP[ajanlasRaw] ?? "Folyamatban";

  // 1. Item létrehozása
  const createMutation = `
    mutation ($boardId: ID!, $itemName: String!) {
      create_item(board_id: $boardId, item_name: $itemName) {
        id
      }
    }`;

  const createRes = await mondayRequest(createMutation, {
    boardId: BOARD_ID,
    itemName: meetingTitle,
  });

  const apiErrors = createRes.data.errors;
  if (apiErrors?.length) {
    throw new Error(`Monday API hiba (create_item): ${JSON.stringify(apiErrors)}`);
  }

  const itemId = createRes.data.data.create_item.id;

  // 2. Oszlopok feltöltése
  const tartalmiDetail =
    `Tartalmi scoring:\n` +
    `  Use-case: ${analysisResult.tartalmi_scoring.use_case.pont}/15 – ${analysisResult.tartalmi_scoring.use_case.indok}\n` +
    `  Iparági insight: ${analysisResult.tartalmi_scoring.iparagi_insight.pont}/15 – ${analysisResult.tartalmi_scoring.iparagi_insight.indok}\n` +
    `  Actionable tipp: ${analysisResult.tartalmi_scoring.actionable_tipp.pont}/10 – ${analysisResult.tartalmi_scoring.actionable_tipp.indok}\n` +
    `  Szegmens-relevancia: ${analysisResult.tartalmi_scoring.szegmens_relevancia.pont}/10 – ${analysisResult.tartalmi_scoring.szegmens_relevancia.indok}`;

  const minosegi =
    `Minőségi scoring:\n` +
    `  Konkrétság: ${analysisResult.minosegi_scoring.konkrektsag.pont}/20 – ${analysisResult.minosegi_scoring.konkrektsag.indok}\n` +
    `  Újszerűség: ${analysisResult.minosegi_scoring.ujszeruseg.pont}/15 – ${analysisResult.minosegi_scoring.ujszeruseg.indok}\n` +
    `  Hitelességi forrás: ${analysisResult.minosegi_scoring.hitelessegi_forras.pont}/15 – ${analysisResult.minosegi_scoring.hitelessegi_forras.indok}`;

  const columnValues = JSON.stringify({
    szegmens: { label: analysisResult.szegmens },
    tartalmi_score: analysisResult.tartalmi_scoring.reszosszeg,
    minosegi_score: analysisResult.minosegi_scoring.reszosszeg,
    osszesitett_score: analysisResult.osszesitett_pont,
    ajanlas: { label: statusLabel },
    indoklas: `${analysisResult.szegmens_indoklas}\n\n${tartalmiDetail}\n\n${minosegi}`,
    hirlevel_angle: analysisResult.hirlevel_angle,
    action_items: `• ${analysisResult.action_items.join("\n• ")}`,
    osszefoglalas: analysisResult.osszefoglalas,
    drive_link: analysisResult.drive_link
      ? { url: analysisResult.drive_link, text: "Transcript" }
      : undefined,
  });

  const updateMutation = `
    mutation ($itemId: ID!, $columnValues: JSON!) {
      change_multiple_column_values(
        item_id: $itemId,
        board_id: ${BOARD_ID},
        column_values: $columnValues
      ) { id }
    }`;

  const updateRes = await mondayRequest(updateMutation, { itemId, columnValues });

  const updateErrors = updateRes.data.errors;
  if (updateErrors?.length) {
    throw new Error(`Monday API hiba (change_multiple_column_values): ${JSON.stringify(updateErrors)}`);
  }

  return itemId;
}
