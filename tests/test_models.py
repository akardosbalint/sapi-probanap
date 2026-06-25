import pytest
from pydantic import ValidationError

from sapi_probanap.models import (
    ExtractionResult, NewsCategory, NewsPiece, NewsPieceStatus,
    ProcessingResult, ScoreBreakdown, ScoredNewsPiece
)


def make_news_piece(**kwargs) -> NewsPiece:
    defaults = dict(
        title="Test headline",
        summary="A meaningful summary with enough detail to be useful.",
        category=NewsCategory.COMPANY_UPDATE,
        source_quote="Verbatim quote from the transcript.",
        confidence=0.8,
    )
    defaults.update(kwargs)
    return NewsPiece(**defaults)


def make_scored(status=NewsPieceStatus.APPROVED, total=8.0) -> ScoredNewsPiece:
    piece = make_news_piece()
    score = ScoreBreakdown(
        relevance=8.0, specificity=8.0, impact=8.0,
        timeliness=8.0, source_quality=8.0, total=total
    )
    return ScoredNewsPiece(news_piece=piece, score=score, status=status)


class TestNewsPiece:
    def test_valid_piece(self):
        p = make_news_piece()
        assert p.title == "Test headline"
        assert p.confidence == 0.8

    def test_confidence_bounds(self):
        with pytest.raises(ValidationError):
            make_news_piece(confidence=1.5)
        with pytest.raises(ValidationError):
            make_news_piece(confidence=-0.1)

    def test_defaults(self):
        p = make_news_piece()
        assert p.mentioned_by == []
        assert p.mentioned_companies == []
        assert p.mentioned_products == []
        assert p.time_sensitivity == "normal"


class TestProcessingResult:
    def test_sendable_property(self):
        approved = make_scored(NewsPieceStatus.APPROVED)
        review = make_scored(NewsPieceStatus.REVIEW)
        rejected = make_scored(NewsPieceStatus.REJECTED)

        result = ProcessingResult(
            meeting_context="Test meeting",
            total_extracted=3,
            approved=[approved],
            review=[review],
            rejected=[rejected],
        )

        assert len(result.sendable) == 2
        assert approved in result.sendable
        assert review in result.sendable
        assert rejected not in result.sendable

    def test_webhook_counts_default_zero(self):
        result = ProcessingResult(
            meeting_context="Test",
            total_extracted=0,
            approved=[],
            review=[],
            rejected=[],
        )
        assert result.webhook_sent == 0
        assert result.webhook_failed == 0


class TestExtractionResult:
    def test_valid_extraction(self):
        result = ExtractionResult(
            news_pieces=[make_news_piece()],
            meeting_context="Weekly team sync",
            total_items_found=1,
        )
        assert len(result.news_pieces) == 1
        assert result.total_items_found == 1
