"""The JSON schema handed to Claude via structured-output ``output_config``.

Enum lists are derived from the Python enums in :mod:`triage.models`, so the
wire schema and the validation model cannot drift (guarded by
``tests/test_schema.py``). ``id`` / ``channel`` / ``error`` are added by our own
code, never by the model, so they are absent here.
"""

from __future__ import annotations

from typing import Any

from triage.models import MODEL_CATEGORIES, Confidence, Language, Priority

_CATEGORIES = [c.value for c in MODEL_CATEGORIES]
_PRIORITIES = [p.value for p in Priority]
_LANGUAGES = [lang.value for lang in Language]
_CONFIDENCES = [c.value for c in Confidence]

# Properties the model fills. Nullable fields use a ["type", "null"] union and
# stay in ``required`` so the model must actively decide null vs a value rather
# than omitting the key.
EXTRACTION_PROPERTIES: dict[str, Any] = {
    "category": {"type": "string", "enum": _CATEGORIES},
    "target_department": {"type": ["string", "null"]},
    "priority": {"type": "string", "enum": _PRIORITIES},
    "short_summary": {"type": "string"},
    "requested_actions": {"type": "array", "items": {"type": "string"}},
    "needs_clarification": {"type": "boolean"},
    "language": {"type": "string", "enum": _LANGUAGES},
    "confidence": {"type": "string", "enum": _CONFIDENCES},
    "secondary_category": {"type": ["string", "null"], "enum": [*_CATEGORIES, None]},
    "is_actionable": {"type": "boolean"},
}

EXTRACTION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": EXTRACTION_PROPERTIES,
    "required": list(EXTRACTION_PROPERTIES),
    "additionalProperties": False,
}
