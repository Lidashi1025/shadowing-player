from pathlib import Path

from shadowing_player.export.starred_export import (
    export_starred_anki_csv,
    export_starred_srt,
)
from shadowing_player.review.review_controller import ReviewItem
from shadowing_player.subtitles.models import Sentence


def test_export_starred_srt_and_anki(tmp_path: Path) -> None:
    items = [
        ReviewItem(
            tmp_path / "ep1.mp4",
            Sentence(1, 0, 1_500, "Hello", text_zh="你好"),
        ),
        ReviewItem(
            tmp_path / "ep1.mp4",
            Sentence(2, 1_500, 3_000, "World", text_zh="世界"),
        ),
    ]
    srt = export_starred_srt(items, tmp_path / "out.srt")
    text = srt.read_text(encoding="utf-8")
    assert "Hello" in text and "你好" in text
    assert "00:00:00,000 --> 00:00:01,500" in text

    csv_path = export_starred_anki_csv(items, tmp_path / "anki.txt")
    rows = csv_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(rows) == 2
    assert rows[0].startswith("Hello\t你好\t")
