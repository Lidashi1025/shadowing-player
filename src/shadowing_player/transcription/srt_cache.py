from __future__ import annotations

from pathlib import Path

import pysubs2

from shadowing_player.subtitles.models import Sentence


def write_srt_atomic(path: Path, sentences: list[Sentence]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    subtitles = pysubs2.SSAFile()
    for sentence in sentences:
        subtitles.append(
            pysubs2.SSAEvent(
                start=sentence.start_ms,
                end=sentence.end_ms,
                text=sentence.text,
            )
        )
    try:
        subtitles.save(str(temporary), format_="srt", encoding="utf-8")
        temporary.replace(path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
