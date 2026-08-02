from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QObject, QThread, Signal

from shadowing_player.playback.subtitle_discover_worker import sync_subtitle_load_enabled
from shadowing_player.subtitles.models import Sentence, SubtitleSource
from shadowing_player.subtitles.subtitle_service import SubtitleError, SubtitleService


@dataclass(frozen=True, slots=True)
class SubtitleLoadRequest:
    generation: int
    video_path: Path | None
    source: SubtitleSource
    chinese_source: SubtitleSource | None
    video_duration_ms: int | None
    source_key: str


@dataclass(frozen=True, slots=True)
class SubtitleLoadResult:
    generation: int
    sentences: list[Sentence]
    source_key: str
    video_path: Path | None


class SubtitleLoadWorker(QObject):
    finished = Signal(object)  # SubtitleLoadResult
    failed = Signal(int, str)  # generation, message

    def __init__(self, service: SubtitleService, request: SubtitleLoadRequest) -> None:
        super().__init__()
        self._service = service
        self._request = request

    def run(self) -> None:
        req = self._request
        try:
            if (
                req.chinese_source is not None
                and hasattr(self._service, "load_bilingual_sentences")
            ):
                sentences = self._service.load_bilingual_sentences(
                    req.source, req.chinese_source, req.video_duration_ms
                )
            else:
                sentences = self._service.load_sentences(
                    req.source, req.video_duration_ms
                )
        except SubtitleError as exc:
            self.failed.emit(req.generation, str(exc))
        except Exception as exc:  # pragma: no cover
            self.failed.emit(req.generation, str(exc) or repr(exc))
        else:
            self.finished.emit(
                SubtitleLoadResult(
                    generation=req.generation,
                    sentences=list(sentences),
                    source_key=req.source_key,
                    video_path=req.video_path,
                )
            )


class SubtitleLoadController(QObject):
    """Load/parse/align subtitles off the UI thread (unless tests force sync)."""

    finished = Signal(object)  # SubtitleLoadResult
    failed = Signal(int, str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._generation = 0
        self._thread: QThread | None = None

    @property
    def generation(self) -> int:
        return self._generation

    def cancel_pending(self) -> None:
        self._generation += 1

    def load(
        self,
        service: SubtitleService,
        *,
        video_path: Path | None,
        source: SubtitleSource,
        chinese_source: SubtitleSource | None,
        video_duration_ms: int | None,
        source_key: str,
    ) -> int:
        self._generation += 1
        generation = self._generation
        request = SubtitleLoadRequest(
            generation=generation,
            video_path=video_path,
            source=source,
            chinese_source=chinese_source,
            video_duration_ms=video_duration_ms,
            source_key=source_key,
        )
        if sync_subtitle_load_enabled():
            worker = SubtitleLoadWorker(service, request)
            worker.finished.connect(self.finished.emit)
            worker.failed.connect(self.failed.emit)
            worker.run()
            return generation

        thread = QThread(self)
        worker = SubtitleLoadWorker(service, request)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)

        def _ok(result: object, gen: int = generation) -> None:
            if isinstance(result, SubtitleLoadResult) and result.generation == self._generation:
                self.finished.emit(result)
            thread.quit()

        def _err(gen: int, message: str) -> None:
            if gen == self._generation:
                self.failed.emit(gen, message)
            thread.quit()

        worker.finished.connect(_ok)
        worker.failed.connect(_err)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        self._thread = thread
        thread.start()
        return generation
