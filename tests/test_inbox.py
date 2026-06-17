from __future__ import annotations

from pathlib import Path

import pytest

from triage.inbox import read_requests


def _write(tmp_path: Path, content: str, *, bom: bool) -> Path:
    path = tmp_path / "in.csv"
    path.write_text(content, encoding="utf-8-sig" if bom else "utf-8")
    return path


def test_reads_cyrillic_with_bom(tmp_path: Path) -> None:
    content = "id,channel,timestamp,raw_text\nREQ-001,Slack,2026-06-08 09:14,Привіт треба бот\n"
    rows = read_requests(_write(tmp_path, content, bom=True))
    assert len(rows) == 1
    # The BOM must not corrupt the first column name, or `id` would be empty.
    assert rows[0].id == "REQ-001"
    assert rows[0].channel == "Slack"
    assert rows[0].raw_text == "Привіт треба бот"


def test_missing_columns_raise(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="missing required columns"):
        read_requests(_write(tmp_path, "id,channel\nREQ-001,Slack\n", bom=False))
