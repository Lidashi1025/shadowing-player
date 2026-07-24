from __future__ import annotations

import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Any

from shadowing_player.transcription.model_manager import ModelManager
from shadowing_player.transcription.postprocessor import (
    TranscriptSegment,
    TranscriptWord,
    postprocess_segments,
)
from shadowing_player.transcription.srt_cache import write_srt_atomic
from shadowing_player.transcription.video_hash import quick_video_hash


class TranscriptionCancelled(RuntimeError):
    pass


def _default_model_factory(path: str, **kwargs: Any):
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise RuntimeError(
            "缺少 faster-whisper，请执行：python -m pip install faster-whisper"
        ) from exc
    return WhisperModel(path, **kwargs)


class TranscriptionService:
    def __init__(
        self,
        cache_dir: Path,
        model_manager: ModelManager,
        model_factory: Callable[..., Any] | None = None,
        fallback_cache_dirs: tuple[Path, ...] = (),
    ) -> None:
        self.cache_dir = cache_dir
        self.model_manager = model_manager
        self._model_factory = model_factory or _default_model_factory
        self.fallback_cache_dirs = tuple(fallback_cache_dirs)

    def cache_path_for(self, video_path: Path) -> Path:
        return self.cache_dir / f"{quick_video_hash(video_path)}.srt"

    def existing_cache_path_for(self, video_path: Path) -> Path | None:
        output = self.cache_path_for(video_path)
        if output.is_file():
            return output
        return self._promote_fallback_cache(output)

    def transcribe(
        self,
        video_path: Path,
        on_progress: Callable[[int], None] | None = None,
        on_phase: Callable[[str], None] | None = None,
        is_cancelled: Callable[[], bool] | None = None,
    ) -> Path:
        progress = on_progress or (lambda _value: None)
        phase = on_phase or (lambda _value: None)
        cancelled = is_cancelled or (lambda: False)

        phase("checking_cache")
        if cancelled():
            raise TranscriptionCancelled()
        output = self.cache_path_for(video_path)
        existing = self.existing_cache_path_for(video_path)
        if existing is not None:
            progress(100)
            phase("completed")
            return existing

        available = getattr(self.model_manager, "is_available", lambda: False)()
        phase("loading_model" if available else "downloading_model")
        model_path = self.model_manager.ensure_model()
        if cancelled():
            raise TranscriptionCancelled()
        phase("loading_model")
        model = self._model_factory(
            str(model_path),
            device="cpu",
            compute_type="int8",
        )
        if cancelled():
            raise TranscriptionCancelled()

        phase("transcribing")
        segments, info = model.transcribe(
            str(video_path),
            language="en",
            word_timestamps=True,
            vad_filter=True,
        )
        duration = max(0.001, float(getattr(info, "duration", 0.0) or 0.0))
        transcript: list[TranscriptSegment] = []
        for segment in segments:
            if cancelled():
                raise TranscriptionCancelled()
            words = tuple(
                TranscriptWord(
                    start_ms=round(float(word.start) * 1000),
                    end_ms=round(float(word.end) * 1000),
                    text=str(word.word).strip(),
                )
                for word in (getattr(segment, "words", None) or ())
                if getattr(word, "start", None) is not None
                and getattr(word, "end", None) is not None
            )
            transcript.append(
                TranscriptSegment(
                    start_ms=round(float(segment.start) * 1000),
                    end_ms=round(float(segment.end) * 1000),
                    text=str(segment.text).strip(),
                    words=words,
                )
            )
            progress(min(99, max(0, round(float(segment.end) / duration * 100))))

        if cancelled():
            raise TranscriptionCancelled()
        phase("postprocessing")
        sentences = postprocess_segments(transcript)
        if cancelled():
            raise TranscriptionCancelled()
        write_srt_atomic(output, sentences)
        progress(100)
        phase("completed")
        return output

    def _promote_fallback_cache(self, output: Path) -> Path | None:
        for directory in self.fallback_cache_dirs:
            legacy = directory / output.name
            if not legacy.is_file():
                continue
            temporary = output.with_suffix(output.suffix + ".importing")
            try:
                output.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(legacy, temporary)
                temporary.replace(output)
            except OSError:
                temporary.unlink(missing_ok=True)
                return legacy
            return output
        return None
