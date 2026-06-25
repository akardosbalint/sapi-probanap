import pytest
from sapi_probanap.models import NewsCategory, NewsPiece, NewsPieceStatus
from sapi_probanap.scorer import NewsScorer


def make_piece(**kwargs) -> NewsPiece:
    defaults = dict(
        title="Company X launches new product",
        summary="Company X announced the launch of their flagship product at the annual event. "
                "The product targets enterprise customers and includes advanced analytics features. "
                "Pricing will be announced next week.",
        category=NewsCategory.PRODUCT_LAUNCH,
        source_quote="We are officially launching our flagship product targeting enterprise customers with advanced analytics.",
        mentioned_by=["Jane Doe"],
        mentioned_companies=["Company X"],
        mentioned_products=["Flagship Product"],
        time_sensitivity="normal",
        confidence=0.9,
    )
    defaults.update(kwargs)
    return NewsPiece(**defaults)


class TestNewsScorer:
    def setup_method(self):
        self.scorer = NewsScorer()

    def test_high_confidence_product_launch_approved(self):
        piece = make_piece(confidence=0.95, time_sensitivity="urgent")
        scored = self.scorer.score(piece)
        assert scored.status == NewsPieceStatus.APPROVED
        assert scored.score.total >= 7.0

    def test_low_confidence_rejected(self):
        piece = make_piece(confidence=0.3)
        scored = self.scorer.score(piece)
        assert scored.status == NewsPieceStatus.REJECTED
        assert "confidence" in scored.rejection_reason

    def test_short_summary_rejected(self):
        piece = make_piece(summary="Too short.")
        scored = self.scorer.score(piece)
        assert scored.status == NewsPieceStatus.REJECTED
        assert "summary" in scored.rejection_reason

    def test_short_quote_rejected(self):
        piece = make_piece(source_quote="Brief.")
        scored = self.scorer.score(piece)
        assert scored.status == NewsPieceStatus.REJECTED
        assert "source quote" in scored.rejection_reason

    def test_medium_confidence_gets_review(self):
        piece = make_piece(
            confidence=0.65,
            category=NewsCategory.OTHER,
            time_sensitivity="low",
            mentioned_companies=[],
            mentioned_by=[],
        )
        scored = self.scorer.score(piece)
        # Should be in review or rejected, not approved
        assert scored.status in (NewsPieceStatus.REVIEW, NewsPieceStatus.REJECTED)

    def test_score_all_returns_correct_count(self):
        pieces = [make_piece(title=f"Item {i}") for i in range(5)]
        scored = self.scorer.score_all(pieces)
        assert len(scored) == 5

    def test_financial_category_high_impact(self):
        piece = make_piece(category=NewsCategory.FINANCIAL, confidence=0.9)
        scored = self.scorer.score(piece)
        assert scored.score.impact >= 9.0

    def test_custom_config_lowers_threshold(self, tmp_path):
        config = tmp_path / "scoring.yaml"
        config.write_text("thresholds:\n  approved: 3.0\n  review: 1.0\n")
        scorer = NewsScorer(config_path=config)
        piece = make_piece(confidence=0.6, category=NewsCategory.OTHER, time_sensitivity="low")
        scored = scorer.score(piece)
        # With very low threshold, low-scoring items should still get approved
        assert scored.status in (NewsPieceStatus.APPROVED, NewsPieceStatus.REVIEW)

    def test_score_breakdown_weights_sum(self):
        scorer = NewsScorer()
        weights = scorer._cfg["weights"]
        total = sum(weights.values())
        assert abs(total - 1.0) < 1e-9, f"Weights must sum to 1.0, got {total}"
