"""Read the input inbox CSV into validated :class:`InputRequest` rows."""

from __future__ import annotations

import csv
from pathlib import Path

from triage.models import InputRequest

REQUIRED_COLUMNS = {"id", "channel", "timestamp", "raw_text"}


def read_requests(path: str | Path) -> list[InputRequest]:
    """Load and validate the inbox CSV.

    Opened ``utf-8-sig`` so a byte-order mark on the first header cell cannot
    corrupt the ``id`` column, and ``newline=""`` per the csv module contract.
    """
    path = Path(path)
    with path.open(encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        missing = REQUIRED_COLUMNS - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"{path}: missing required columns: {sorted(missing)}")
        return [
            InputRequest(
                id=(row.get("id") or "").strip(),
                channel=(row.get("channel") or "").strip(),
                timestamp=(row.get("timestamp") or "").strip(),
                raw_text=(row.get("raw_text") or "").strip(),
            )
            for row in reader
        ]
