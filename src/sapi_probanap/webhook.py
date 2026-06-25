from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import httpx

from sapi_probanap.models import ScoredNewsPiece

logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT = 30.0
_MAX_RETRIES = 3


class WebhookError(Exception):
    pass


class MakeWebhookSender:
    def __init__(self, webhook_url: str, timeout: float = _DEFAULT_TIMEOUT):
        if not webhook_url:
            raise ValueError("webhook_url must not be empty")
        self._url = webhook_url
        self._timeout = timeout

    def send(self, item: ScoredNewsPiece, meeting_context: str = "") -> dict[str, Any]:
        """Send a single scored news piece to Make.com. Returns the response body."""
        payload = self._build_payload(item, meeting_context)
        return self._post(payload)

    def send_batch(
        self, items: list[ScoredNewsPiece], meeting_context: str = ""
    ) -> tuple[list[ScoredNewsPiece], list[tuple[ScoredNewsPiece, Exception]]]:
        """Send all items individually. Returns (succeeded, failed) lists."""
        succeeded: list[ScoredNewsPiece] = []
        failed: list[tuple[ScoredNewsPiece, Exception]] = []

        for item in items:
            try:
                self.send(item, meeting_context)
                succeeded.append(item)
                logger.info("Sent: %s (score=%.1f, status=%s)",
                            item.news_piece.title, item.score.total, item.status.value)
            except Exception as exc:
                failed.append((item, exc))
                logger.warning("Failed to send '%s': %s", item.news_piece.title, exc)

        return succeeded, failed

    # ------------------------------------------------------------------

    def _build_payload(self, item: ScoredNewsPiece, meeting_context: str) -> dict[str, Any]:
        np = item.news_piece
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "meeting_context": meeting_context,
            "status": item.status.value,
            "title": np.title,
            "summary": np.summary,
            "category": np.category.value,
            "source_quote": np.source_quote,
            "mentioned_by": np.mentioned_by,
            "mentioned_companies": np.mentioned_companies,
            "mentioned_products": np.mentioned_products,
            "time_sensitivity": np.time_sensitivity,
            "agent_confidence": np.confidence,
            "score": {
                "total": item.score.total,
                "relevance": item.score.relevance,
                "specificity": item.score.specificity,
                "impact": item.score.impact,
                "timeliness": item.score.timeliness,
                "source_quality": item.score.source_quality,
            },
        }

    def _post(self, payload: dict[str, Any]) -> dict[str, Any]:
        last_exc: Exception | None = None
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                response = httpx.post(
                    self._url,
                    json=payload,
                    timeout=self._timeout,
                    headers={"Content-Type": "application/json"},
                )
                response.raise_for_status()
                try:
                    return response.json()
                except Exception:
                    return {"raw": response.text}
            except httpx.HTTPStatusError as exc:
                last_exc = exc
                logger.warning("HTTP %s on attempt %d: %s", exc.response.status_code, attempt, exc)
                if exc.response.status_code < 500:
                    break  # Don't retry 4xx
            except httpx.RequestError as exc:
                last_exc = exc
                logger.warning("Request error on attempt %d: %s", attempt, exc)

        raise WebhookError(f"Webhook failed after {_MAX_RETRIES} attempts") from last_exc
