# Netpeak Request Triage

Classifies a free-form inbox of internal requests (Ukrainian/English, arriving via
Slack/Telegram/Email) into a **strict, validated schema** using Claude Haiku 4.5, then
emits a structured `output.json` and an aggregate `report.md`. Built to triage what is
today a manual sorting job: what is each request about, which department, how urgent,
and what exactly is being asked.

## What it does

Reads `input_requests.csv` → for every row, asks Claude Haiku 4.5 (with **structured
outputs**) to extract category, target department, priority, a one-line summary, the
concrete requested actions, and whether the request is too vague to action → **validates
every field** and fails soft on bad model output → writes `output.json` (all rows) and a
human-readable `report.md` with the aggregates and the list that needs clarification.
Optionally posts a compact digest to Telegram.

## Quick start

```bash
pip install -e .
cp .env.example .env          # then fill ANTHROPIC_API_KEY
python -m triage test-data/input_requests.csv
```

See **Configuration**, **Limitations**, and **Evaluation** below.

<!-- Sections (run, env, architecture diagram, schema + why, limitations, evaluation,
     what's next) are completed in the final pass. -->
