from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from collections.abc import Callable
from pathlib import Path

import pysubs2

from shadowing_player.subtitles.models import Sentence, SubtitleKind, SubtitleSource
from shadowing_player.subtitles.bilingual_aligner import align_bilingual


TEXT_SUBTITLE_CODECS = {
    "ass",
    "mov_text",
    "ssa",
    "subrip",
    "text",
    "webvtt",
}


class SubtitleError(RuntimeError):
    pass


class UnsupportedSubtitleError(SubtitleError):
    pass


CommandRunner = Callable[[list[str]], subprocess.CompletedProcess[str]]


def _run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
    creation_flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    return subprocess.run(
        command,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=creation_flags,
    )


class SubtitleService:
    def __init__(self, cache_dir: Path, runner: CommandRunner = _run_command) -> None:
        self.cache_dir = cache_dir
        self._runner = runner

    def discover(self, video_path: Path) -> list[SubtitleSource]:
        video = video_path.resolve()
        sources = self._external_sources(video)
        try:
            probe = self._runner(
                [
                    "ffprobe",
                    "-v",
                    "error",
                    "-select_streams",
                    "s",
                    "-show_entries",
                    "stream=index,codec_name,codec_type:stream_tags=language,title",
                    "-of",
                    "json",
                    str(video),
                ]
            )
            payload = json.loads(probe.stdout or "{}")
        except (FileNotFoundError, subprocess.SubprocessError, json.JSONDecodeError) as exc:
            if sources:
                return sources
            raise SubtitleError("无法运行 ffprobe 检查内嵌字幕，请确认 ffprobe 已加入 PATH") from exc

        subtitle_streams = [
            stream
            for stream in payload.get("streams", [])
            if stream.get("codec_type", "subtitle") == "subtitle"
        ]
        text_streams = [
            stream for stream in subtitle_streams if stream.get("codec_name", "") in TEXT_SUBTITLE_CODECS
        ]
        for stream in text_streams:
            tags = stream.get("tags") or {}
            sources.append(
                SubtitleSource.embedded(
                    video,
                    stream_index=int(stream["index"]),
                    codec_name=str(stream.get("codec_name", "")),
                    language=str(tags.get("language", "")),
                    title=str(tags.get("title", "")),
                )
            )
        if not sources and subtitle_streams and not text_streams:
            raise UnsupportedSubtitleError(
                "视频只包含图片字幕，当前版本仅支持文字字幕（SRT/ASS/内嵌文字轨）"
            )
        return sources

    def choose_default(self, sources: list[SubtitleSource]) -> SubtitleSource | None:
        if not sources:
            return None
        external = next((item for item in sources if item.kind is SubtitleKind.EXTERNAL), None)
        if external is not None:
            return external
        english = next(
            (
                item
                for item in sources
                if item.language.lower() in {"en", "eng", "english"}
            ),
            None,
        )
        return english or sources[0]

    def choose_language_sources(
        self, sources: list[SubtitleSource]
    ) -> tuple[SubtitleSource | None, SubtitleSource | None]:
        if not sources:
            return None, None
        chinese_codes = {"zh", "zho", "chi", "chs", "cht", "cn", "zh-cn", "zh-tw"}
        english_codes = {"en", "eng", "english"}
        chinese = next(
            (item for item in sources if item.language.lower() in chinese_codes), None
        )
        english = next(
            (item for item in sources if item.language.lower() in english_codes), None
        )
        if english is None:
            english = next(
                (
                    item
                    for item in sources
                    if item is not chinese
                    and item.language.lower() not in chinese_codes
                ),
                None,
            )
        if chinese is None:
            embedded = [
                item
                for item in sources
                if item.kind is SubtitleKind.EMBEDDED and item is not english
            ]
            chinese = embedded[0] if embedded else None
        return english, chinese

    def load_bilingual_sentences(
        self,
        english_source: SubtitleSource,
        chinese_source: SubtitleSource | None,
        video_duration_ms: int | None = None,
    ) -> list[Sentence]:
        english = self.load_sentences(english_source, video_duration_ms)
        if chinese_source is None:
            return english
        chinese = self.load_sentences(chinese_source, video_duration_ms)
        return align_bilingual(english, chinese)

    def load_sentences(
        self,
        source: SubtitleSource,
        video_duration_ms: int | None = None,
    ) -> list[Sentence]:
        subtitle_path = source.path
        if source.kind is SubtitleKind.EMBEDDED:
            subtitle_path = self._extract_embedded(source)
        try:
            subtitles = pysubs2.load(str(subtitle_path), encoding="utf-8")
        except Exception as exc:
            raise SubtitleError(f"无法解析字幕：{subtitle_path.name}") from exc

        sentences: list[Sentence] = []
        for event in subtitles:
            text = re.sub(r"\s+", " ", event.plaintext).strip()
            start_ms = max(0, int(event.start))
            end_ms = int(event.end)
            if video_duration_ms is not None:
                end_ms = min(video_duration_ms, end_ms)
            if not text or end_ms <= start_ms:
                continue
            sentences.append(Sentence(len(sentences), start_ms, end_ms, text))
        return sentences

    def _external_sources(self, video: Path) -> list[SubtitleSource]:
        candidates = [
            item
            for item in video.parent.iterdir()
            if item.is_file()
            and item.suffix.lower() in {".srt", ".ass"}
            and (
                item.stem.casefold() == video.stem.casefold()
                or item.stem.casefold().startswith(video.stem.casefold() + ".")
            )
        ]
        candidates.sort(
            key=lambda item: (
                0 if item.stem.casefold() == video.stem.casefold() else 1,
                0 if item.suffix.lower() == ".srt" else 1,
                item.name.casefold(),
            )
        )
        sources: list[SubtitleSource] = []
        for candidate in candidates:
            language = self._language_from_external_name(video, candidate)
            if not language:
                language = self._language_from_content(candidate)
            sources.append(
                SubtitleSource(
                    kind=SubtitleKind.EXTERNAL,
                    path=candidate,
                    language=language,
                )
            )
        return sources

    @staticmethod
    def _language_from_external_name(video: Path, subtitle: Path) -> str:
        remainder = subtitle.stem[len(video.stem) :].lstrip(".").casefold()
        token = remainder.split(".", 1)[0]
        if token in {"en", "eng", "english"}:
            return "en"
        if token in {"zh", "zho", "chi", "chs", "cht", "cn", "zh-cn", "zh-tw"}:
            return "zh"
        return ""

    @staticmethod
    def _language_from_content(subtitle: Path) -> str:
        try:
            sample = subtitle.read_text(encoding="utf-8-sig", errors="ignore")[:65_536]
        except OSError:
            return ""
        cjk_count = len(re.findall(r"[\u3400-\u9fff]", sample))
        latin_count = len(re.findall(r"[A-Za-z]", sample))
        if cjk_count >= 2 and cjk_count >= latin_count * 0.2:
            return "zh"
        if latin_count >= 4 and cjk_count == 0:
            return "en"
        return ""

    def _extract_embedded(self, source: SubtitleSource) -> Path:
        if source.stream_index is None:
            raise SubtitleError("内嵌字幕缺少轨道编号")
        stat = source.path.stat()
        fingerprint = hashlib.sha256(
            f"{source.path.resolve()}|{stat.st_size}|{stat.st_mtime_ns}|{source.stream_index}".encode("utf-8")
        ).hexdigest()
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        output = self.cache_dir / f"{fingerprint}.srt"
        if output.is_file():
            return output
        try:
            result = self._runner(
                [
                    "ffmpeg",
                    "-v",
                    "error",
                    "-y",
                    "-i",
                    str(source.path),
                    "-map",
                    f"0:{source.stream_index}",
                    str(output),
                ]
            )
            if result.returncode != 0:
                raise subprocess.CalledProcessError(result.returncode, result.args, result.stdout, result.stderr)
        except (FileNotFoundError, subprocess.SubprocessError) as exc:
            output.unlink(missing_ok=True)
            raise SubtitleError("无法用 ffmpeg 抽取内嵌文字字幕，请确认 ffmpeg 已加入 PATH") from exc
        if not output.is_file():
            raise SubtitleError("ffmpeg 未生成字幕文件")
        return output
