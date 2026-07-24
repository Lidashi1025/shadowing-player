from __future__ import annotations

from shadowing_player.subtitles.bilingual_aligner import align_bilingual
from shadowing_player.subtitles.models import Sentence


def test_chinese_cues_are_assigned_by_largest_time_overlap() -> None:
    english = [
        Sentence(0, 0, 2_000, "Hello"),
        Sentence(1, 2_000, 4_000, "How are you?"),
    ]
    chinese = [
        Sentence(0, 100, 1_900, "你好"),
        Sentence(1, 2_100, 2_800, "你"),
        Sentence(2, 2_900, 3_900, "好吗？"),
    ]

    aligned = align_bilingual(english, chinese)

    assert [item.text_zh for item in aligned] == ["你好", "你好吗？"]


def test_unmatched_chinese_cue_leaves_translation_empty() -> None:
    english = [Sentence(0, 0, 1_000, "Hello")]
    chinese = [Sentence(0, 2_000, 3_000, "太晚了")]

    assert align_bilingual(english, chinese)[0].text_zh == ""
