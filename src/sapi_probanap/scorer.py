from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

from sapi_probanap.models import (
    NewsPiece,
    NewsPieceStatus,
    ScoreBreakdown,
    ScoredNewsPiece,
)

logger = logging.getLogger(__name__)

_DEFAULT_CONFIG: dict[str, Any] = {
    "weights": {
        "relevance": 0.30,
        "specificity": 0.25,
        "impact": 0.25,
        "timeliness": 0.10,
        "source_quality": 0.10,
    },
    "thresholds": {"approved": 7.0, "review": 4.0},
    "confidence_filter": {"min_confidence": 0.5},
    "category_boosts": {},
    "time_sensitivity_boosts": {"urgent": 1.15, "normal": 1.0, "low": 0.90},
    "reject_rules": [
        {"min_summary_words": 10},
        {"min_source_quote_chars": 20},
    ],
}


def _deep_merge(base: dict, override: dict) -> dict:
    result = dict(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(result.get(k), dict):
            result[k] = _deep_merge(result[k], v)
        else:
            result[k] = v
    return result


class NewsScorer:
    def __init__(self, config_path: str | Path | None = None):
        cfg = dict(_DEFAULT_CONFIG)
        if config_path:
            loaded = yaml.safe_load(Path(config_path).read_text())
            if loaded:
                cfg = _deep_merge(cfg, loaded)
        self._cfg = cfg
        logger.debug("Scorer loaded config: %s", cfg)

    def score(self, piece: NewsPiece) -> ScoredNewsPiece:
        rejection_reason = self._hard_reject(piece)
        if rejection_reason:
            breakdown = self._zero_breakdown()
            return ScoredNewsPiece(
                news_piece=piece,
                score=breakdown,
                status=NewsPieceStatus.REJECTED,
                rejection_reason=rejection_reason,
            )

        breakdown = self._compute_breakdown(piece)
        status = self._determine_status(breakdown.total, piece)

        return ScoredNewsPiece(
            news_piece=piece,
            score=breakdown,
            status=status,
        )

    def score_all(self, pieces: list[NewsPiece]) -> list[ScoredNewsPiece]:
        return [self.score(p) for p in pieces]

    # ------------------------------------------------------------------

    def _hard_reject(self, piece: NewsPiece) -> str | None:
        cf = self._cfg.get("confidence_filter", {})
        min_conf = cf.get("min_confidence", 0.0)
        if piece.confidence < min_conf:
            return f"confidence {piece.confidence:.2f} below minimum {min_conf}"

        for rule in self._cfg.get("reject_rules", []):
            if "min_summary_words" in rule:
                words = len(piece.summary.split())
                if words < rule["min_summary_words"]:
                    return f"summary too short ({words} words, min {rule['min_summary_words']})"
            if "min_source_quote_chars" in rule:
                chars = len(piece.source_quote)
                if chars < rule["min_source_quote_chars"]:
                    return f"source quote too short ({chars} chars, min {rule['min_source_quote_chars']})"

        return None

    def _compute_breakdown(self, piece: NewsPiece) -> ScoreBreakdown:
        relevance = self._score_relevance(piece)
        specificity = self._score_specificity(piece)
        impact = self._score_impact(piece)
        timeliness = self._score_timeliness(piece)
        source_quality = self._score_source_quality(piece)

        weights = self._cfg["weights"]
        raw_total = (
            relevance * weights["relevance"]
            + specificity * weights["specificity"]
            + impact * weights["impact"]
            + timeliness * weights["timeliness"]
            + source_quality * weights["source_quality"]
        )

        # Apply category and time sensitivity boosts
        cat_boost = self._cfg.get("category_boosts", {}).get(piece.category.value, 1.0)
        ts_boost = self._cfg.get("time_sensitivity_boosts", {}).get(piece.time_sensitivity, 1.0)
        total = min(10.0, raw_total * cat_boost * ts_boost)

        return ScoreBreakdown(
            relevance=round(relevance, 2),
            specificity=round(specificity, 2),
            impact=round(impact, 2),
            timeliness=round(timeliness, 2),
            source_quality=round(source_quality, 2),
            total=round(total, 2),
        )

    def _score_relevance(self, piece: NewsPiece) -> float:
        # Base from agent confidence + category weight
        base = piece.confidence * 7.0
        high_value_categories = {
            "product_launch", "financial", "partnership", "regulatory", "personnel"
        }
        if piece.category.value in high_value_categories:
            base = min(10.0, base + 1.5)
        return min(10.0, base)

    def _score_specificity(self, piece: NewsPiece) -> float:
        score = 5.0
        # Reward concrete entities
        if piece.mentioned_companies:
            score += min(2.0, len(piece.mentioned_companies) * 0.5)
        if piece.mentioned_products:
            score += min(1.5, len(piece.mentioned_products) * 0.5)
        # Reward a longer source quote (more context = more specific)
        quote_len = len(piece.source_quote)
        if quote_len > 200:
            score += 1.5
        elif quote_len > 100:
            score += 0.75
        return min(10.0, score)

    def _score_impact(self, piece: NewsPiece) -> float:
        impact_map = {
            "financial": 9.0,
            "regulatory": 8.5,
            "product_launch": 8.0,
            "partnership": 7.5,
            "personnel": 7.0,
            "company_update": 6.5,
            "market_insight": 6.0,
            "technology": 5.5,
            "other": 4.0,
        }
        return impact_map.get(piece.category.value, 5.0)

    def _score_timeliness(self, piece: NewsPiece) -> float:
        ts_map = {"urgent": 9.0, "normal": 6.0, "low": 3.0}
        return ts_map.get(piece.time_sensitivity, 6.0)

    def _score_source_quality(self, piece: NewsPiece) -> float:
        if not piece.mentioned_by:
            return 5.0
        # More speakers mentioning the same item → higher confidence
        return min(10.0, 5.0 + len(piece.mentioned_by) * 1.5)

    def _determine_status(self, total: float, piece: NewsPiece) -> NewsPieceStatus:
        thresholds = self._cfg["thresholds"]
        if total >= thresholds["approved"]:
            return NewsPieceStatus.APPROVED
        if total >= thresholds["review"]:
            return NewsPieceStatus.REVIEW
        return NewsPieceStatus.REJECTED

    @staticmethod
    def _zero_breakdown() -> ScoreBreakdown:
        return ScoreBreakdown(
            relevance=0.0, specificity=0.0, impact=0.0,
            timeliness=0.0, source_quality=0.0, total=0.0
        )
