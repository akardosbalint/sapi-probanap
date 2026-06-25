from __future__ import annotations

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class NewsCategory(str, Enum):
    COMPANY_UPDATE = "company_update"
    PRODUCT_LAUNCH = "product_launch"
    PARTNERSHIP = "partnership"
    FINANCIAL = "financial"
    PERSONNEL = "personnel"
    MARKET_INSIGHT = "market_insight"
    REGULATORY = "regulatory"
    TECHNOLOGY = "technology"
    OTHER = "other"


class NewsPieceStatus(str, Enum):
    APPROVED = "approved"
    REVIEW = "review"
    REJECTED = "rejected"


class NewsPiece(BaseModel):
    title: str = Field(description="Concise news headline (max 100 chars)")
    summary: str = Field(description="2-3 sentence summary of the news item")
    category: NewsCategory = Field(description="Primary category of the news piece")
    source_quote: str = Field(description="Verbatim quote from the transcript supporting this news item")
    mentioned_by: list[str] = Field(default_factory=list, description="Names of people who mentioned this item")
    mentioned_companies: list[str] = Field(default_factory=list, description="Companies mentioned in this news item")
    mentioned_products: list[str] = Field(default_factory=list, description="Products or services mentioned")
    time_sensitivity: str = Field(
        default="normal",
        description="One of: urgent, normal, low — how time-sensitive this news is"
    )
    confidence: float = Field(
        ge=0.0, le=1.0,
        description="Agent confidence in this extraction (0.0-1.0)"
    )


class ExtractionResult(BaseModel):
    news_pieces: list[NewsPiece] = Field(description="All extracted news pieces")
    meeting_context: str = Field(description="Brief description of the meeting (type, participants, date if mentioned)")
    total_items_found: int = Field(description="Total count of distinct news items identified")


class ScoreBreakdown(BaseModel):
    relevance: float = Field(ge=0.0, le=10.0, description="How relevant/newsworthy this item is")
    specificity: float = Field(ge=0.0, le=10.0, description="Level of concrete detail vs vague statement")
    impact: float = Field(ge=0.0, le=10.0, description="Potential business/market impact")
    timeliness: float = Field(ge=0.0, le=10.0, description="Time sensitivity and urgency")
    source_quality: float = Field(ge=0.0, le=10.0, description="Quality/authority of source within meeting")
    total: float = Field(ge=0.0, le=10.0, description="Weighted total score")


class ScoredNewsPiece(BaseModel):
    news_piece: NewsPiece
    score: ScoreBreakdown
    status: NewsPieceStatus
    rejection_reason: Optional[str] = None


class ProcessingResult(BaseModel):
    meeting_context: str
    total_extracted: int
    approved: list[ScoredNewsPiece]
    review: list[ScoredNewsPiece]
    rejected: list[ScoredNewsPiece]
    webhook_sent: int = 0
    webhook_failed: int = 0

    @property
    def sendable(self) -> list[ScoredNewsPiece]:
        return self.approved + self.review


# ── Knowledge-base extraction models ──────────────────────────────────────────

class KnowledgeCategory(str, Enum):
    EMAIL_MARKETING = "Email marketing"
    INTEGRATION = "Integráció"
    AUTOMATION = "Automatizálás"
    STRATEGY = "Stratégia"
    TECHNICAL_SETUP = "Technikai beállítás"


class TudasElem(BaseModel):
    """One self-contained, reusable knowledge piece."""
    cim: str = Field(description="Rövid, tömör cím — önmagában is érthető")
    tartalom: str = Field(description="2-4 mondatos kifejtés, önállóan érthető, kontextus nélkül is")
    kategoria: KnowledgeCategory = Field(description="Tudáselem kategóriája")
    hasznossagi_pont: int = Field(ge=1, le=10, description="Hasznosság 1-10 skálán")
    miert_hasznos: str = Field(description="1 mondat: kinek és miért releváns ez a tudás")


class TudasbazisResult(BaseModel):
    """Full output of the knowledge-extraction agent."""
    tudaselemek: list[TudasElem] = Field(description="Összes kinyert tudáselem, csökkenő hasznossági sorrendben")
    osszesen: int = Field(description="Kinyert tudáselemek száma")
    legfontosabb_tanuls: str = Field(description="A szöveg egyetlen legfontosabb üzenete 1-2 mondatban")
