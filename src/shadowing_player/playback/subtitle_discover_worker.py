from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import QObject, QThread, Signal

from shadowing_player.subtitles.models import SubtitleSource
from shadowing_player.subtitles.subtitle_service import SubtitleError, SubtitleService


def sync_subtitle_load_enabled() -> bool:
    """Tests set SHADOWING_SYNC_SUBTITLE_LOAD=1 to keep open/load synchronous."""
    return os.environ.get("SHADOWING_SYNC_SUBTITLE_LOAD", "").strip().lower() in {
        "1",
        "true",
        "yes",
    }


class SubtitleDiscoverWorker(QObject):
    finished = Signal(object)  # list[SubtitleSource]
    failed = Signal(str)

    def __init__(self, service: SubtitleService, video_path: Path) -> None:
        super().__init__()
        self._service = service
        self._video_path = video_path

    def run(self) -> None:
        try:
            sources = self._service.discover(self._video_path)
        except SubtitleError as exc:
            self.failed.emit(str(exc))
        except Exception as exc:  # pragma: no cover - defensive
            self.failed.emit(str(exc) or repr(exc))
        else:
            self.finished.emit(sources)


class SubtitleDiscoverController(QObject):
    """Runs discover() off the UI thread unless sync mode is forced."""

    finished = Signal(int, object)  # generation, sources
    failed = Signal(int, str)  # generation, message

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._generation = 0
        self._thread: QThread | None = None

    @property
    def generation(self) -> int:
        return self._generation

    def cancel_pending(self) -> None:
        self._generation += 1

    def discover(self, service: SubtitleService, video_path: Path) -> int:
        self._generation += 1
        generation = self._generation
        if sync_subtitle_load_enabled():
            try:
                sources = service.discover(video_path)
            except SubtitleError as exc:
                self.failed.emit(generation, str(exc))
            except Exception as exc:  # pragma: no cover
                self.failed.emit(generation, str(exc) or repr(exc))
            else:
                self.finished.emit(generation, sources)
            return generation

        thread = QThread(self)
        worker = SubtitleDiscoverWorker(service, video_path)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)

        def _ok(sources: object, gen: int = generation) -> None:
            if gen == self._generation:
                self.finished.emit(gen, sources)
            thread.quit()

        def _err(message: str, gen: int = generation) -> None:
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
