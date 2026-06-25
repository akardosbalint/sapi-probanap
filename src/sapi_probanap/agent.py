from __future__ import annotations

import json
import logging
from pathlib import Path

import anthropic

from sapi_probanap.models import ExtractionResult, NewsPiece

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are an expert news analyst specializing in extracting newsworthy items from meeting transcripts.

Your task is to identify all distinct, newsworthy information mentioned in the meeting — announcements, decisions, partnerships, product updates, financial information, personnel changes, market insights, or any notable developments.

Guidelines:
- Extract every concrete, factual news item mentioned
- Skip vague or purely internal administrative items (scheduling, logistics)
- Capture the exact verbatim quote that best supports each news item
- Be conservative with confidence scores — only use >0.9 for clear, unambiguous items
- Identify who mentioned each item and any companies/products referenced
- Assess time sensitivity: urgent (breaking news), normal (soon), low (background info)

Return structured output with all extracted news pieces."""


class TranscriptAgent:
    def __init__(self, api_key: str | None = None, model: str = "claude-opus-4-8"):
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model

    def process(self, transcript: str, source_label: str = "meeting") -> ExtractionResult:
        """Extract news pieces from a transcript using Claude with adaptive thinking."""
        logger.info("Processing transcript (%d chars) from '%s'", len(transcript), source_label)

        user_message = f"""Please analyze the following meeting transcript and extract all newsworthy items.

Transcript source: {source_label}
---
{transcript}
---

Extract every distinct newsworthy item as a structured news piece."""

        with self._client.messages.stream(
            model=self._model,
            max_tokens=8000,
            thinking={"type": "adaptive"},
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
            output_config={
                "format": {
                    "type": "json",
                    "json_schema": ExtractionResult.model_json_schema(),
                }
            },
        ) as stream:
            response = stream.get_final_message()

        raw_json = response.content[0].text if response.content else "{}"
        data = json.loads(raw_json)
        result = ExtractionResult.model_validate(data)
        logger.info("Extracted %d news pieces", len(result.news_pieces))
        return result

    def process_file(self, path: str | Path) -> ExtractionResult:
        path = Path(path)
        transcript = path.read_text(encoding="utf-8")
        return self.process(transcript, source_label=path.name)
