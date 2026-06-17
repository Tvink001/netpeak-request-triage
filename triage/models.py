"""Domain models: the input row and the validated triage schema."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class Category(str, Enum):
    AUTOMATION = "автоматизація"
    INTEGRATION = "інтеграція"
    REPORT_ANALYTICS = "звіт/аналітика"
    BUG_SUPPORT = "баг/підтримка"
    QUESTION_CONSULTATION = "питання/консультація"
    OUT_OF_SCOPE = "поза скоупом"
    # Reserved fail-soft sentinel. NEVER offered to the model (see schema.py);
    # used only by ExtractedRequest.fallback for rows the model could not process.
    UNPROCESSED = "не оброблено"


class Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Language(str, Enum):
    UK = "uk"
    EN = "en"
    MIXED = "mixed"


class Confidence(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


# The categories the model may choose from (the six mandated by the brief).
MODEL_CATEGORIES: tuple[Category, ...] = tuple(c for c in Category if c is not Category.UNPROCESSED)

# ExtractedRequest fields that are NOT produced by the model.
IDENTITY_FIELDS: tuple[str, ...] = ("id", "channel")
BOOKKEEPING_FIELDS: tuple[str, ...] = ("error",)


class InputRequest(BaseModel):
    """One row of the input inbox CSV."""

    id: str
    channel: str
    timestamp: str
    raw_text: str


class ExtractedRequest(BaseModel):
    """The validated triage result for one request.

    Field order matches the desired ``output.json`` layout: identity first, then
    the model-produced fields, then the optional fail-soft ``error``.
    """

    id: str
    channel: str

    category: Category
    target_department: str | None
    priority: Priority
    short_summary: str
    requested_actions: list[str] = Field(default_factory=list)
    needs_clarification: bool
    language: Language
    confidence: Confidence
    secondary_category: Category | None = None
    is_actionable: bool

    error: str | None = None

    @classmethod
    def fallback(cls, *, id: str, channel: str, error: str) -> ExtractedRequest:
        """A safe, valid record for a request the model could not process.

        The last line of defence: one unparseable or refused row must never
        abort the batch. The reserved ``UNPROCESSED`` category keeps the record
        valid while surfacing the failure in the aggregates.
        """
        return cls(
            id=id,
            channel=channel,
            category=Category.UNPROCESSED,
            target_department=None,
            priority=Priority.LOW,
            short_summary=f"[extraction failed: {error}]",
            requested_actions=[],
            needs_clarification=True,
            language=Language.MIXED,
            confidence=Confidence.LOW,
            secondary_category=None,
            is_actionable=False,
            error=error,
        )
