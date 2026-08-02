from pathlib import Path

from shadowing_player.playback.video_open_plan import PlanKind, plan_after_discover
from shadowing_player.subtitles.models import SubtitleKind, SubtitleSource


def test_plan_no_sources_prompts_when_no_cache(tmp_path: Path) -> None:
    plan = plan_after_discover(
        [],
        progress=None,
        video_path=tmp_path / "a.mp4",
        find_cache=lambda _p: None,
        choose_language_sources=None,
        choose_default=lambda sources: sources[0] if sources else None,
    )
    assert plan.kind is PlanKind.NO_SOURCES_PROMPT


def test_plan_no_sources_uses_cache(tmp_path: Path) -> None:
    cache = tmp_path / "cached.srt"
    cache.write_text("1\n00:00:00,000 --> 00:00:01,000\nHi\n", encoding="utf-8")
    plan = plan_after_discover(
        [],
        progress=None,
        video_path=tmp_path / "a.mp4",
        find_cache=lambda _p: cache,
        choose_language_sources=None,
        choose_default=lambda sources: sources[0] if sources else None,
    )
    assert plan.kind is PlanKind.NO_SOURCES_USE_CACHE
    assert plan.selected is not None
    assert plan.selected.path == cache


def test_plan_chinese_only_transcribe(tmp_path: Path) -> None:
    zh = SubtitleSource(
        kind=SubtitleKind.EXTERNAL, path=tmp_path / "zh.srt", language="zh"
    )
    plan = plan_after_discover(
        [zh],
        progress=None,
        video_path=tmp_path / "a.mp4",
        find_cache=lambda _p: None,
        choose_language_sources=lambda _sources: (None, zh),
        choose_default=lambda sources: sources[0],
    )
    assert plan.kind is PlanKind.CHINESE_ONLY_TRANSCRIBE
    assert plan.chinese_source is zh


def test_plan_uses_english_default(tmp_path: Path) -> None:
    en = SubtitleSource(
        kind=SubtitleKind.EXTERNAL, path=tmp_path / "en.srt", language="en"
    )
    zh = SubtitleSource(
        kind=SubtitleKind.EXTERNAL, path=tmp_path / "zh.srt", language="zh"
    )
    plan = plan_after_discover(
        [en, zh],
        progress=None,
        video_path=tmp_path / "a.mp4",
        find_cache=lambda _p: None,
        choose_language_sources=lambda _sources: (en, zh),
        choose_default=lambda sources: sources[0],
    )
    assert plan.kind is PlanKind.USE_SOURCE
    assert plan.selected is en
    assert plan.chinese_source is zh
