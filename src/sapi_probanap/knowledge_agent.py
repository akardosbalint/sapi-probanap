from __future__ import annotations

import json
import logging
from pathlib import Path

import anthropic

from sapi_probanap.models import TudasbazisResult

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You are a JSON-only API. You must respond with raw JSON only. "
    "No markdown, no backticks, no explanations. "
    "Your entire response must be a single valid JSON object starting with { and ending with }."
)

_USER_TEMPLATE = """\
Az alábbi szövegből gyűjtsd ki az összes önálló, hasznos tudáselemet.
Minden tudáselem egy konkrét tanács, módszer, szabály, magyarázat vagy felismerés legyen,
amit valaki hasznosítani tud.

NEM kell: napirend, köszöntő, technikai problémák, bemutatkozások,
időpont-egyeztetések, szervező szöveg.

IGEN kell: minden konkrét szakmai tudás, tanács, magyarázat,
best practice, döntési szabály, figyelmeztetés.

A JSON struktúra:
{{
  "tudaselemek": [
    {{
      "cim": "Rövid, tömör cím",
      "tartalom": "A tudáselem részletes kifejtése 2-4 mondatban, önállóan érthető formában",
      "kategoria": "Email marketing | Integráció | Automatizálás | Stratégia | Technikai beállítás",
      "hasznossagi_pont": 1-10,
      "miert_hasznos": "1 mondatban: kinek és miért releváns ez a tudás"
    }}
  ],
  "osszesen": 0,
  "legfontosabb_tanuls": "A szöveg egyetlen legfontosabb üzenete 1-2 mondatban"
}}

Pontozási szabályok:
- 9-10: azonnal alkalmazható, konkrét lépés, általánosan érvényes
- 7-8: fontos tanács, de kontextusfüggő vagy előismeret kell
- 4-6: hasznos magyarázat, de nem közvetlen akció
- 1-3: általános, közismert vagy csak szűk célcsoportnak releváns

Rendezd a tudáselemeket hasznossági pont szerint csökkenő sorrendbe.

Szöveg:
{text}"""


class TudasbazisAgent:
    """Extract structured, reusable knowledge pieces from any text."""

    def __init__(self, api_key: str | None = None, model: str = "claude-sonnet-4-6"):
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model

    def process(self, text: str, source_label: str = "document") -> TudasbazisResult:
        logger.info("Extracting knowledge from '%s' (%d chars)", source_label, len(text))

        response = self._client.messages.create(
            model=self._model,
            max_tokens=4000,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": _USER_TEMPLATE.format(text=text)}],
        )

        raw = response.content[0].text if response.content else "{}"
        data = json.loads(raw)

        # Ensure osszesen matches actual list length
        data.setdefault("osszesen", len(data.get("tudaselemek", [])))
        result = TudasbazisResult.model_validate(data)

        # Guarantee descending sort (model may not always comply perfectly)
        result.tudaselemek.sort(key=lambda e: e.hasznossagi_pont, reverse=True)
        result.osszesen = len(result.tudaselemek)

        logger.info("Extracted %d knowledge pieces", result.osszesen)
        return result

    def process_file(self, path: str | Path) -> TudasbazisResult:
        path = Path(path)
        return self.process(path.read_text(encoding="utf-8"), source_label=path.name)
