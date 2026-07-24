import json
import subprocess
from pathlib import Path

import pytest

from shadowing_player.subtitles.models import Sentence, SubtitleKind, SubtitleSource
from shadowing_player.subtitles.subtitle_service import (
    SubtitleService,
    UnsupportedSubtitleError,
)


def completed(command: list[str], stdout: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(command, 0, stdout=stdout, stderr="")


def test_discovers_same_name_subtitles_for_mp4_with_srt_first(tmp_path: Path) -> None:
    movie = tmp_path / "episode.mp4"
    movie.touch()
    srt = tmp_path / "episode.srt"
    ass = tmp_path / "episode.ass"
    srt.touch()
    ass.touch()
    runner = lambda command: completed(command, '{"streams": []}')
    service = SubtitleService(tmp_path / "cache", runner=runner)

    sources = service.discover(movie)

    assert [(source.kind, source.path) for source in sources] == [
        (SubtitleKind.EXTERNAL, srt),
        (SubtitleKind.EXTERNAL, ass),
    ]


def test_discovers_embedded_text_subtitles_and_prefers_english(tmp_path: Path) -> None:
    movie = tmp_path / "episode.mkv"
    movie.touch()
    probe = {
        "streams": [
            {"index": 2, "codec_name": "ass", "codec_type": "subtitle", "tags": {"language": "jpn"}},
            {"index": 3, "codec_name": "subrip", "codec_type": "subtitle", "tags": {"language": "eng", "title": "English"}},
        ]
    }
    runner = lambda command: completed(command, json.dumps(probe))
    service = SubtitleService(tmp_path / "cache", runner=runner)

    sources = service.discover(movie)

    assert [source.stream_index for source in sources] == [2, 3]
    assert service.choose_default(sources).stream_index == 3


def test_reports_image_only_embedded_subtitles(tmp_path: Path) -> None:
    movie = tmp_path / "episode.mkv"
    movie.touch()
    probe = {
        "streams": [
            {"index": 4, "codec_name": "hdmv_pgs_subtitle", "codec_type": "subtitle", "tags": {}}
        ]
    }
    service = SubtitleService(
        tmp_path / "cache",
        runner=lambda command: completed(command, json.dumps(probe)),
    )

    with pytest.raises(UnsupportedSubtitleError, match="图片字幕"):
        service.discover(movie)


def test_loads_srt_as_clean_sentences_with_playback_padding(tmp_path: Path) -> None:
    subtitle = tmp_path / "episode.srt"
    subtitle.write_text(
        "1\n00:00:01,000 --> 00:00:02,000\n<i>Hello</i>   world\n\n"
        "2\n00:00:03,000 --> 00:00:04,500\nHow are you?\n",
        encoding="utf-8",
    )
    source = SubtitleSource.external(subtitle)
    service = SubtitleService(tmp_path / "cache", runner=lambda command: completed(command))

    sentences = service.load_sentences(source, video_duration_ms=4_600)

    assert sentences == [
        Sentence(index=0, start_ms=1_000, end_ms=2_000, text="Hello world"),
        Sentence(index=1, start_ms=3_000, end_ms=4_500, text="How are you?"),
    ]
    assert sentences[0].play_window(video_duration_ms=4_600) == (750, 2_250)
    assert sentences[1].play_window(video_duration_ms=4_600) == (2_750, 4_600)


def test_extracts_embedded_subtitle_once_then_reuses_cache(tmp_path: Path) -> None:
    movie = tmp_path / "episode.mp4"
    movie.write_bytes(b"movie")
    calls: list[list[str]] = []

    def runner(command: list[str]) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        if command[0] == "ffmpeg":
            Path(command[-1]).write_text(
                "1\n00:00:00,000 --> 00:00:01,000\nHello\n",
                encoding="utf-8",
            )
        return completed(command)

    source = SubtitleSource.embedded(
        movie,
        stream_index=2,
        codec_name="mov_text",
        language="eng",
        title="English",
    )
    service = SubtitleService(tmp_path / "cache", runner=runner)

    first = service.load_sentences(source)
    second = service.load_sentences(source)

    assert first == second == [Sentence(0, 0, 1_000, "Hello")]
    ffmpeg_calls = [command for command in calls if command[0] == "ffmpeg"]
    assert len(ffmpeg_calls) == 1
    assert ffmpeg_calls[0][ffmpeg_calls[0].index("-map") + 1] == "0:2"


def test_discovers_language_suffixed_external_subtitles(tmp_path: Path) -> None:
    movie = tmp_path / "episode.mp4"
    movie.touch()
    english = tmp_path / "episode.en.srt"
    chinese = tmp_path / "episode.zh-CN.srt"
    english.touch()
    chinese.touch()
    service = SubtitleService(
        tmp_path / "cache",
        runner=lambda command: completed(command, '{"streams": []}'),
    )

    english_source, chinese_source = service.choose_language_sources(
        service.discover(movie)
    )

    assert english_source is not None and english_source.path == english
    assert chinese_source is not None and chinese_source.path == chinese


def test_only_chinese_source_does_not_fall_back_to_english(
    tmp_path: Path,
) -> None:
    movie = tmp_path / "episode.mp4"
    movie.touch()
    chinese = tmp_path / "episode.srt"
    chinese.write_text(
        "1\n00:00:00,000 --> 00:00:01,000\n你好，特工。\n",
        encoding="utf-8",
    )
    service = SubtitleService(
        tmp_path / "cache",
        runner=lambda command: completed(command, '{"streams": []}'),
    )
    sources = service.discover(movie)

    english_source, chinese_source = service.choose_language_sources(sources)

    assert english_source is None
    assert chinese_source is not None and chinese_source.path == chinese


def test_second_untagged_embedded_track_is_chinese_fallback(tmp_path: Path) -> None:
    movie = tmp_path / "episode.mkv"
    movie.touch()
    probe = {
        "streams": [
            {"index": 2, "codec_name": "subrip", "codec_type": "subtitle"},
            {"index": 3, "codec_name": "ass", "codec_type": "subtitle"},
        ]
    }
    service = SubtitleService(
        tmp_path / "cache",
        runner=lambda command: completed(command, json.dumps(probe)),
    )

    english_source, chinese_source = service.choose_language_sources(
        service.discover(movie)
    )

    assert english_source is not None and english_source.stream_index == 2
    assert chinese_source is not None and chinese_source.stream_index == 3


def test_same_name_chinese_srt_pairs_with_embedded_english(tmp_path: Path) -> None:
    movie = tmp_path / "episode.mkv"
    movie.touch()
    chinese = tmp_path / "episode.srt"
    chinese.write_text(
        "1\n00:00:00,000 --> 00:00:01,000\n你好，世界\n",
        encoding="utf-8",
    )
    probe = {
        "streams": [
            {
                "index": 2,
                "codec_name": "subrip",
                "codec_type": "subtitle",
                "tags": {"language": "eng"},
            }
        ]
    }
    service = SubtitleService(
        tmp_path / "cache",
        runner=lambda command: completed(command, json.dumps(probe)),
    )

    english_source, chinese_source = service.choose_language_sources(
        service.discover(movie)
    )

    assert english_source is not None and english_source.stream_index == 2
    assert chinese_source is not None and chinese_source.path == chinese


def test_chinese_only_tagged_source_is_reserved_for_bilingual_companion(
    tmp_path: Path,
) -> None:
    movie = tmp_path / "episode.mp4"
    movie.touch()
    chinese = tmp_path / "episode.zh.srt"
    chinese.write_text(
        "1\n00:00:00,000 --> 00:00:01,000\n只有中文\n",
        encoding="utf-8",
    )
    service = SubtitleService(
        tmp_path / "cache",
        runner=lambda command: completed(command, '{"streams": []}'),
    )

    english_source, chinese_source = service.choose_language_sources(
        service.discover(movie)
    )

    assert english_source is None
    assert chinese_source is not None and chinese_source.path == chinese
