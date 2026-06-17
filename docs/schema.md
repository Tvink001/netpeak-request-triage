# Output schema

## The record

Every request becomes one `ExtractedRequest` (see `triage/models.py`). Fields are written
to `output.json` in this order:

| field | type | produced by |
| --- | --- | --- |
| `id` | string | carried from the input row |
| `channel` | string | carried from the input row |
| `category` | enum | model |
| `target_department` | string \| null | model |
| `priority` | enum (`low`/`medium`/`high`) | model |
| `short_summary` | string | model |
| `requested_actions` | string[] | model |
| `needs_clarification` | bool | model |
| `language` | enum (`uk`/`en`/`mixed`) | model |
| `confidence` | enum (`low`/`medium`/`high`) | model |
| `secondary_category` | enum \| null | model |
| `is_actionable` | bool | model |
| `error` | string \| null | set only on a fail-soft fallback |

`category` values (the six from the brief): `автоматизація`, `інтеграція`, `звіт/аналітика`,
`баг/підтримка`, `питання/консультація`, `поза скоупом`. A seventh value, `не оброблено`,
is **reserved for fallback records** and is never offered to the model.

## The JSON schema handed to the model

`triage/schema.py` builds the schema passed to Anthropic's `output_config`. Only the
model-produced fields appear (`id`, `channel`, `error` are added by our code). Nullable
fields use `anyOf` with a `null` branch — structured outputs require a single `type`
alongside `enum`, so a nullable enum cannot use a `["string", "null"]` type array. Every
field stays in `required`, so the model must actively decide null vs. a value rather than
omitting the key:

```json
{
  "type": "object",
  "additionalProperties": false,
  "required": ["category", "target_department", "priority", "short_summary",
               "requested_actions", "needs_clarification", "language",
               "confidence", "secondary_category", "is_actionable"],
  "properties": {
    "category":            {"type": "string", "enum": ["автоматизація", "..."]},
    "target_department":   {"anyOf": [{"type": "string"}, {"type": "null"}]},
    "priority":            {"type": "string", "enum": ["low", "medium", "high"]},
    "short_summary":       {"type": "string"},
    "requested_actions":   {"type": "array", "items": {"type": "string"}},
    "needs_clarification": {"type": "boolean"},
    "language":            {"type": "string", "enum": ["uk", "en", "mixed"]},
    "confidence":          {"type": "string", "enum": ["low", "medium", "high"]},
    "secondary_category":  {"anyOf": [{"type": "string", "enum": ["автоматизація", "..."]},
                                      {"type": "null"}]},
    "is_actionable":       {"type": "boolean"}
  }
}
```

## Example record

```json
{
  "id": "REQ-010",
  "channel": "Slack",
  "category": "автоматизація",
  "target_department": "Marketing",
  "priority": "medium",
  "short_summary": "Збір згадок про Netpeak у Telegram у щоденний дайджест плюс алерт на негатив.",
  "requested_actions": [
    "Налаштувати щоденний дайджест згадок про Netpeak у Telegram-каналах",
    "Додати окремий алерт на негативні згадки"
  ],
  "needs_clarification": false,
  "language": "uk",
  "confidence": "high",
  "secondary_category": "інтеграція",
  "is_actionable": true,
  "error": null
}
```

The rationale for the four non-mandated fields (`language`, `confidence`,
`secondary_category`, `is_actionable`) is in the [README](../README.md#why-these-four-extensions).
