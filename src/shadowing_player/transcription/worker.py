from __future__ import annotations

import threading
from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot

from shadowing_player.transcription.service import (
    TranscriptionCancelled,
    TranscriptionService,
)


class CancellationToken:
    def __init__(self) -> None:
        self._event = threading.Event()

    def cancel(self) -> None:
        self._event.set()

    def is_cancelled(self) -> bool:
        return self._event.is_set()


class TranscriptionWorker(QObject):
    phase_changed = Signal(str)
    progress_changed = Signal(int)
    completed = Signal(str)
    cancelled = Signal()
    failed = Signal(str)

    def __init__(
        self,
        video_path: Path,
        service: TranscriptionService,
        cancellation: CancellationToken,
    ) -> None:
        super().__init__()
        self.video_path = video_path
        self.service = service
        self.cancellation = cancellation

    @Slot()
    def run(self) -> None:
        try:
            output = self.service.transcribe(
                self.video_path,
                on_progress=self.progress_changed.emit,
                on_phase=self.phase_changed.emit,
                is_cancelled=self.cancellation.is_cancelled,
            )
        except TranscriptionCancelled:
            self.cancelled.emit()
        except Exception as exc:
            self.failed.emit(str(exc))
        else:
            self.completed.emit(str(output))
