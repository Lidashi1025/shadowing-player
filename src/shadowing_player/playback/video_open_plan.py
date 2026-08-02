from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from shadowing_player.storage.progress_store import VideoProgress
from shadowing_player.subtitles.models import SubtitleSource


class PlanKind(str, Enum):
    CACHE_ERROR = "cache_error"
    NO_SOURCES_USE_CACHE = "no_sources_use_cache"
    NO_SOURCES_PROMPT = "no_sources_prompt"
    CHINESE_ONLY_USE_CACHE = "chinese_only_use_cache"
    CHINESE_ONLY_TRANSCRIBE = "chinese_only_transcribe"
    USE_SOURCE = "use_source"
    NO_USABLE = "no_usable"


@dataclass(slots=True)
class VideoOpenPlan:
    kind: PlanKind
    sources: list[SubtitleSource] = field(default_factory=list)
    selected: SubtitleSource | None = None
    chinese_source: SubtitleSource | None = None
    message: str | None = None


FindCache = Callable[[Path], Path | None]
ChooseLanguage = Callable[
    [list[SubtitleSource]], tuple[SubtitleSource | None, SubtitleSource | None]
]
ChooseDefault = Callable[[list[SubtitleSource]], SubtitleSource | None]


def plan_after_discover(
    sources: list[SubtitleSource],
    *,
    progress: VideoProgress | None,
    video_path: Path,
    find_cache: FindCache,
    choose_language_sources: ChooseLanguage | None,
    choose_default: ChooseDefault,
) -> VideoOpenPlan:
    """Decide the next open-video step after subtitle discovery."""
    if not sources:
        try:
            cached = find_cache(video_path)
        except OSError as exc:
            return VideoOpenPlan(kind=PlanKind.CACHE_ERROR, message=str(exc))
        if cached is not None and cached.is_file():
            source = SubtitleSource.external(cached)
            return VideoOpenPlan(
                kind=PlanKind.NO_SOURCES_USE_CACHE,
                sources=[source],
                selected=source,
            )
        return VideoOpenPlan(kind=PlanKind.NO_SOURCES_PROMPT, sources=[])

    restored_source = next(
        (
            source
            for source in sources
            if progress is not None and source.identifier == progress.subtitle_source_id
        ),
        None,
    )
    default_source = restored_source
    chinese_source: SubtitleSource | None = None

    if choose_language_sources is not None:
        english_source, chinese_source = choose_language_sources(sources)
        if english_source is None and chinese_source is not None:
            try:
                cached = find_cache(video_path)
            except OSError as exc:
                return VideoOpenPlan(
                    kind=PlanKind.CACHE_ERROR,
                    sources=sources,
                    message=str(exc),
                )
            if cached is not None and cached.is_file():
                generated = SubtitleSource.external(cached)
                combined = [generated, *sources]
                return VideoOpenPlan(
                    kind=PlanKind.CHINESE_ONLY_USE_CACHE,
                    sources=combined,
                    selected=generated,
                    chinese_source=chinese_source,
                )
            return VideoOpenPlan(
                kind=PlanKind.CHINESE_ONLY_TRANSCRIBE,
                sources=sources,
                selected=chinese_source,
                chinese_source=chinese_source,
            )
        if default_source is chinese_source:
            default_source = None
        default_source = default_source or english_source

    default_source = default_source or choose_default(sources)
    if default_source is None:
        return VideoOpenPlan(
            kind=PlanKind.NO_USABLE,
            sources=sources,
            chinese_source=chinese_source,
        )
    return VideoOpenPlan(
        kind=PlanKind.USE_SOURCE,
        sources=sources,
        selected=default_source,
        chinese_source=chinese_source,
    )
