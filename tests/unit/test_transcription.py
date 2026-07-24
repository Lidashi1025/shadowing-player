from __future__ import annotations

from pathlib import Path

import pysubs2

from shadowing_player.transcription.postprocessor import (
    TranscriptSegment,
    TranscriptWord,
    postprocess_segments,
)
from shadowing_player.transcription.srt_cache import write_srt_atomic
from shadowing_player.transcription.video_hash import quick_video_hash


def test_quick_video_hash_is_content_based_and_detects_tail_changes(tmp_path: Path) -> None:
    first = tmp_path / "one.mp4"
    second = tmp_path / "renamed.mp4"
    payload = b"a" * (1024 * 1024) + b"middle" + b"z" * (1024 * 1024)
    first.write_bytes(payload)
    second.write_bytes(payload)

    assert quick_video_hash(first) == quick_video_hash(second)

    changed = bytearray(payload)
    changed[-1] = ord("x")
    second.write_bytes(changed)
    assert quick_video_hash(first) != quick_video_hash(second)


def test_short_segment_is_merged_into_next_sentence() -> None:
    result = postprocess_segments(
        [
            TranscriptSegment(0, 700, "Well"),
            TranscriptSegment(900, 2_500, "hello there"),
        ]
    )

    assert [(item.start_ms, item.end_ms, item.text) for item in result] == [
        (0, 2_500, "Well hello there")
    ]


def test_terminal_short_segment_is_merged_into_previous_sentence() -> None:
    result = postprocess_segments(
        [
            TranscriptSegment(0, 2_000, "See you"),
            TranscriptSegment(2_200, 2_800, "soon"),
        ]
    )

    assert [(item.start_ms, item.end_ms, item.text) for item in result] == [
        (0, 2_800, "See you soon")
    ]


def test_long_segment_splits_at_largest_word_pause_before_eight_seconds() -> None:
    words = (
        TranscriptWord(0, 1_000, "One"),
        TranscriptWord(1_100, 3_000, "two"),
        TranscriptWord(4_500, 5_500, "three"),
        TranscriptWord(5_600, 7_500, "four"),
        TranscriptWord(7_600, 9_500, "five"),
    )

    result = postprocess_segments(
        [TranscriptSegment(0, 9_500, "One two three four five", words)]
    )

    assert len(result) == 2
    assert result[0].text == "One two"
    assert result[0].end_ms == 3_000
    assert result[1].text == "three four five"
    assert all(item.duration_ms <= 8_000 for item in result)


def test_srt_cache_is_valid_and_has_no_playback_padding(tmp_path: Path) -> None:
    cache_path = tmp_path / "cache" / "hash.srt"
    sentences = postprocess_segments([TranscriptSegment(1_000, 2_000, "Hello")])

    write_srt_atomic(cache_path, sentences)

    parsed = pysubs2.load(str(cache_path), encoding="utf-8")
    assert [(event.start, event.end, event.plaintext) for event in parsed] == [
        (1_000, 2_000, "Hello")
    ]
    assert not cache_path.with_suffix(".srt.tmp").exists()
