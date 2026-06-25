from __future__ import annotations

import logging
from pathlib import Path

from sapi_probanap.agent import TranscriptAgent
from sapi_probanap.models import NewsPieceStatus, ProcessingResult, ScoredNewsPiece
from sapi_probanap.scorer import NewsScorer
from sapi_probanap.webhook import MakeWebhookSender

logger = logging.getLogger(__name__)


class TranscriptPipeline:
    """Orchestrates the full transcript → extract → score → send pipeline."""

    def __init__(
        self,
        agent: TranscriptAgent,
        scorer: NewsScorer,
        webhook: MakeWebhookSender | None = None,
        send_approved: bool = True,
        send_review: bool = True,
    ):
        self._agent = agent
        self._scorer = scorer
        self._webhook = webhook
        self._send_approved = send_approved
        self._send_review = send_review

    def run(self, transcript: str, source_label: str = "meeting") -> ProcessingResult:
        extraction = self._agent.process(transcript, source_label)
        scored = self._scorer.score_all(extraction.news_pieces)

        approved = [s for s in scored if s.status == NewsPieceStatus.APPROVED]
        review = [s for s in scored if s.status == NewsPieceStatus.REVIEW]
        rejected = [s for s in scored if s.status == NewsPieceStatus.REJECTED]

        result = ProcessingResult(
            meeting_context=extraction.meeting_context,
            total_extracted=extraction.total_items_found,
            approved=approved,
            review=review,
            rejected=rejected,
        )

        if self._webhook:
            to_send: list[ScoredNewsPiece] = []
            if self._send_approved:
                to_send.extend(approved)
            if self._send_review:
                to_send.extend(review)

            if to_send:
                succeeded, failed = self._webhook.send_batch(to_send, extraction.meeting_context)
                result.webhook_sent = len(succeeded)
                result.webhook_failed = len(failed)
            else:
                logger.info("No items to send to webhook")

        return result

    def run_file(self, path: str | Path) -> ProcessingResult:
        path = Path(path)
        return self.run(path.read_text(encoding="utf-8"), source_label=path.name)
