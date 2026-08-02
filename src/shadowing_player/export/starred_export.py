from __future__ import annotations

import csv
from pathlib import Path

from shadowing_player.review.review_controller import ReviewItem


def _ms_to_srt_time(milliseconds: int) -> str:
    total = max(0, int(milliseconds))
    hours, rem = divmod(total, 3_600_000)
    minutes, rem = divmod(rem, 60_000)
    seconds, ms = divmod(rem, 1_000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{ms:03d}"


def export_starred_srt(items: list[ReviewItem], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    for index, item in enumerate(items, start=1):
        sentence = item.sentence
        body = sentence.text
        if sentence.text_zh:
            body = f"{sentence.text}\n{sentence.text_zh}"
        lines.extend(
            [
                str(index),
                f"{_ms_to_srt_time(sentence.start_ms)} --> {_ms_to_srt_time(sentence.end_ms)}",
                body,
                "",
            ]
        )
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def export_starred_anki_csv(items: list[ReviewItem], path: Path) -> Path:
    """Anki-friendly CSV: front, back, tags (tab-separated, no header)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        for item in items:
            sentence = item.sentence
            front = sentence.text.strip()
            back = (sentence.text_zh or "").strip()
            tag = item.video_path.stem.replace(" ", "_")
            writer.writerow([front, back, f"shadowing {tag}"])
    return path
