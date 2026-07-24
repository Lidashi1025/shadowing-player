from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class SubtitleKind(str, Enum):
    EXTERNAL = "external"
    EMBEDDED = "embedded"


@dataclass(frozen=True, slots=True)
class Sentence:
    index: int
    start_ms: int
    end_ms: int
    text: str
    text_zh: str = ""
    starred: bool = False
    id: int | None = None
    video_id: int | None = None

    @property
    def duration_ms(self) -> int:
        return max(0, self.end_ms - self.start_ms)

    def play_window(
        self,
        video_duration_ms: int | None = None,
        padding_ms: int = 250,
    ) -> tuple[int, int]:
        start = max(0, self.start_ms - padding_ms)
        end = self.end_ms + padding_ms
        if video_duration_ms is not None:
            end = min(video_duration_ms, end)
        return start, end


@dataclass(frozen=True, slots=True)
class SubtitleSource:
    kind: SubtitleKind
    path: Path
    stream_index: int | None = None
    codec_name: str = ""
    language: str = ""
    title: str = ""

    @classmethod
    def external(cls, path: Path) -> "SubtitleSource":
        return cls(kind=SubtitleKind.EXTERNAL, path=path)

    @classmethod
    def embedded(
        cls,
        video_path: Path,
        stream_index: int,
        codec_name: str,
        language: str = "",
        title: str = "",
    ) -> "SubtitleSource":
        return cls(
            kind=SubtitleKind.EMBEDDED,
            path=video_path,
            stream_index=stream_index,
            codec_name=codec_name,
            language=language,
            title=title,
        )

    @property
    def identifier(self) -> str:
        if self.kind is SubtitleKind.EXTERNAL:
            return f"external:{self.path.resolve()}"
        return f"embedded:{self.stream_index}"

    @property
    def label(self) -> str:
        if self.kind is SubtitleKind.EXTERNAL:
            return f"外部字幕：{self.path.name}"
        details = self.title or self.language or self.codec_name
        return f"内嵌字幕 {self.stream_index}：{details}"
