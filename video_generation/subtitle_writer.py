"""SRT subtitle generation for video guide narration/captions."""

from __future__ import annotations

from pathlib import Path


def _timestamp(seconds: float) -> str:
    millis = int(round(seconds * 1000))
    hours, rem = divmod(millis, 3_600_000)
    minutes, rem = divmod(rem, 60_000)
    secs, ms = divmod(rem, 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{ms:03}"


def write_srt(lines: list[str], output_path: str | Path, duration_seconds: int) -> str:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    clean_lines = [line.strip() for line in lines if line and line.strip()]
    if not clean_lines:
        clean_lines = ["Follow your doctor's prescription."]
    segment = max(1.0, duration_seconds / len(clean_lines))
    blocks = []
    for index, line in enumerate(clean_lines, start=1):
        start = (index - 1) * segment
        end = min(duration_seconds, index * segment)
        blocks.append(f"{index}\n{_timestamp(start)} --> {_timestamp(end)}\n{line}\n")
    path.write_text("\n".join(blocks), encoding="utf-8")
    return str(path)
