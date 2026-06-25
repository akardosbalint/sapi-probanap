import pytest
import httpx
from pytest_httpx import HTTPXMock

from sapi_probanap.models import (
    NewsCategory, NewsPiece, NewsPieceStatus, ScoreBreakdown, ScoredNewsPiece
)
from sapi_probanap.webhook import MakeWebhookSender, WebhookError


def make_scored_piece(title="Test News") -> ScoredNewsPiece:
    piece = NewsPiece(
        title=title,
        summary="A summary of the test news item for testing purposes with enough words here.",
        category=NewsCategory.PRODUCT_LAUNCH,
        source_quote="This is a verbatim quote from the transcript for testing.",
        mentioned_by=["Alice"],
        mentioned_companies=["TestCorp"],
        mentioned_products=["TestProduct"],
        time_sensitivity="normal",
        confidence=0.85,
    )
    score = ScoreBreakdown(
        relevance=8.0, specificity=7.5, impact=8.0,
        timeliness=6.0, source_quality=7.0, total=7.7
    )
    return ScoredNewsPiece(news_piece=piece, score=score, status=NewsPieceStatus.APPROVED)


class TestMakeWebhookSender:
    def test_empty_url_raises(self):
        with pytest.raises(ValueError):
            MakeWebhookSender("")

    def test_send_success(self, httpx_mock: HTTPXMock):
        httpx_mock.add_response(json={"status": "accepted"})
        sender = MakeWebhookSender("https://hook.make.com/test123")
        result = sender.send(make_scored_piece())
        assert result == {"status": "accepted"}

    def test_send_payload_structure(self, httpx_mock: HTTPXMock):
        captured = {}

        def capture(request: httpx.Request):
            import json
            captured["body"] = json.loads(request.content)
            return httpx.Response(200, json={"ok": True})

        httpx_mock.add_callback(capture)
        sender = MakeWebhookSender("https://hook.make.com/test123")
        sender.send(make_scored_piece("Breaking News"), "Q2 Review meeting")

        body = captured["body"]
        assert body["title"] == "Breaking News"
        assert body["status"] == "approved"
        assert body["meeting_context"] == "Q2 Review meeting"
        assert "score" in body
        assert body["score"]["total"] == 7.7

    def test_send_batch_success(self, httpx_mock: HTTPXMock):
        httpx_mock.add_response(json={"ok": True})
        httpx_mock.add_response(json={"ok": True})
        sender = MakeWebhookSender("https://hook.make.com/test123")
        items = [make_scored_piece(f"Item {i}") for i in range(2)]
        succeeded, failed = sender.send_batch(items)
        assert len(succeeded) == 2
        assert len(failed) == 0

    def test_send_batch_partial_failure(self, httpx_mock: HTTPXMock):
        httpx_mock.add_response(json={"ok": True})
        httpx_mock.add_response(status_code=500)
        httpx_mock.add_response(status_code=500)
        httpx_mock.add_response(status_code=500)
        sender = MakeWebhookSender("https://hook.make.com/test123")
        items = [make_scored_piece(f"Item {i}") for i in range(2)]
        succeeded, failed = sender.send_batch(items)
        assert len(succeeded) == 1
        assert len(failed) == 1

    def test_send_4xx_no_retry(self, httpx_mock: HTTPXMock):
        httpx_mock.add_response(status_code=400, json={"error": "bad request"})
        sender = MakeWebhookSender("https://hook.make.com/test123")
        with pytest.raises(WebhookError):
            sender.send(make_scored_piece())
        # Should have only made 1 request (no retry on 4xx)
        assert len(httpx_mock.get_requests()) == 1
