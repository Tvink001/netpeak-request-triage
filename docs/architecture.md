# Architecture

A small, synchronous Python CLI. The whole thing is a pipeline:

```
read CSV  ->  for each row: extract via LLM + validate  ->  collect  ->  write outputs
```

Each stage is one module under `triage/`, so the data flow maps directly onto the code:

| module | responsibility |
| --- | --- |
| `inbox.py` | read + validate the CSV into `InputRequest` rows (utf-8-sig, BOM-safe) |
| `prompts.py` | the system prompt — the classification contract and bilingual cue words |
| `schema.py` | the JSON schema handed to the model (enums derived from `models.py`) |
| `extract.py` | call Claude Haiku 4.5, guard the response, validate, or fall back |
| `models.py` | the enums and the `ExtractedRequest` schema (+ its fallback constructor) |
| `pipeline.py` | run the loop, accumulate token usage, estimate cost |
| `report.py` | write `output.json` and render the aggregate `report.md` |
| `telegram.py` | post an optional run digest |
| `evaluation.py` | score a produced `output.json` against the golden set |
| `cli.py` | argument parsing and orchestration |

## Decisions worth noting

**Two layers of validation, not one.** Structured outputs constrain the model to the
schema at generation time; Pydantic re-validates the parsed JSON at runtime. The belt and
the braces catch different things — the schema stops most malformed output at the source,
and Pydantic is the contract the rest of the code relies on. Neither alone is enough,
because the API can return a schema-violating response (a refusal or a truncation) with a
200 status.

**Fail-soft is a contract, not a sprinkling of try/except.** `RequestExtractor.extract`
never raises. Every failure mode resolves to `ExtractedRequest.fallback(...)`, which builds
a *valid* record with a reserved sentinel category (`не оброблено`). Because the sentinel
is a real enum member, the fallback can never fail its own validation — there is no
fallback-of-the-fallback. The batch always finishes; the fallback count is reported.

**One source of truth for the schema.** The enum value lists in `schema.py` are derived
from the Python enums in `models.py` (`[c.value for c in MODEL_CATEGORIES]`), and a test
asserts the schema's properties match the model's model-facing fields exactly. The wire
schema and the validation model cannot drift apart. The sentinel category is deliberately
*excluded* from the schema offered to the model, so the model can never classify a real
request as "unprocessed".

**Synchronous, on purpose.** At this volume (an inbox CSV), a sequential loop is the
clearest correct thing and trivial to test. Concurrency and the Batch API are written up as
the scaling path; the per-row extractor is already isolated, so adding them is a pipeline
change, not a redesign.

**UTF-8 end to end.** The corpus is Ukrainian. The CSV is read `utf-8-sig` (a stray BOM
must not corrupt the `id` column), `output.json` is written with `ensure_ascii=False` so
Cyrillic stays readable, and stdout/stderr are reconfigured to UTF-8 so the tool does not
crash on a non-UTF-8 Windows console.

**Telegram via plain `httpx`.** The digest is a single `sendMessage` POST wrapped in a
best-effort try/except that never aborts the run. A full bot framework would be dead weight
in a batch CLI.

## Testing

The suite mocks the Anthropic SDK (no network) and exercises the fail-soft branches
explicitly — refusal, truncation, malformed JSON, non-object JSON, and API error each
assert a fallback. Pipeline and CLI are covered end-to-end with a stub extractor, so the
file-writing and orchestration paths run without a key. `mypy` is strict.
