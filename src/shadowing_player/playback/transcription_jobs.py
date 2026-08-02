from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QObject, QThread, QTimer, Signal

from shadowing_player.storage.progress_store import VideoProgress
from shadowing_player.subtitles.models import SubtitleSource
from shadowing_player.transcription.service import TranscriptionService
from shadowing_player.transcription.worker import CancellationToken, TranscriptionWorker


@dataclass(eq=False, slots=True)
class TranscriptionJob:
    video_path: Path
    thread: QThread
    worker: TranscriptionWorker
    token: CancellationToken
    progress: VideoProgress | None
    chinese_source: SubtitleSource | None


class TranscriptionJobManager(QObject):
    """Owns background ASR jobs and a one-slot queue."""

    phase_changed = Signal(str)
    progress_changed = Signal(int)
    job_completed = Signal(object, str)  # job, cache_path
    job_cancelled = Signal(object)
    job_failed = Signal(object, str)
    active_changed = Signal(bool)
    queue_message = Signal(str)

    def __init__(
        self,
        service: TranscriptionService,
        *,
        parent: QObject | None = None,
        current_video: Callable[[], Path | None] | None = None,
        is_closing: Callable[[], bool] | None = None,
        is_torn_down: Callable[[], bool] | None = None,
    ) -> None:
        super().__init__(parent)
        self._service = service
        self._current_video = current_video or (lambda: None)
        self._is_closing = is_closing or (lambda: False)
        self._is_torn_down = is_torn_down or (lambda: False)
        self.active_job: TranscriptionJob | None = None
        self.jobs: list[TranscriptionJob] = []
        self.queued: tuple[Path, VideoProgress | None, SubtitleSource | None] | None = None

    def start(
        self,
        video_path: Path,
        progress: VideoProgress | None = None,
        chinese_source: SubtitleSource | None = None,
    ) -> None:
        resolved = video_path.resolve()
        if (
            self._is_torn_down()
            or self._is_closing()
            or self._current_video() != resolved
        ):
            return
        if self.jobs:
            for running in self.jobs:
                running.token.cancel()
            self.queued = (resolved, progress, chinese_source)
            self.queue_message.emit("queued")
            return

        token = CancellationToken()
        thread = QThread(self)
        worker = TranscriptionWorker(video_path, self._service, token)
        job = TranscriptionJob(
            video_path=resolved,
            thread=thread,
            worker=worker,
            token=token,
            progress=progress,
            chinese_source=chinese_source,
        )
        self.active_job = job
        self.jobs.append(job)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.phase_changed.connect(self._on_phase)
        worker.progress_changed.connect(self._on_progress)
        worker.completed.connect(self._on_completed)
        worker.cancelled.connect(self._on_cancelled)
        worker.failed.connect(self._on_failed)
        worker.completed.connect(thread.quit)
        worker.cancelled.connect(thread.quit)
        worker.failed.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(self._on_thread_finished)
        self.active_changed.emit(True)
        thread.start()

    def cancel_active(self) -> None:
        if self.active_job is not None:
            self.active_job.token.cancel()
        elif self.queued is not None:
            self.queued = None
            self.queue_message.emit("queue_cleared")

    def abandon(self) -> None:
        self.queued = None
        if self.active_job is None:
            return
        self.active_job.token.cancel()
        self.active_job = None
        self.active_changed.emit(False)

    def has_jobs(self) -> bool:
        return bool(self.jobs)

    def _job_for_sender(self) -> TranscriptionJob | None:
        sender = self.sender()
        return next(
            (
                job
                for job in self.jobs
                if job.worker is sender or job.thread is sender
            ),
            None,
        )

    def _on_phase(self, phase: str) -> None:
        if self._job_for_sender() is not self.active_job:
            return
        self.phase_changed.emit(phase)

    def _on_progress(self, value: int) -> None:
        if self._job_for_sender() is not self.active_job:
            return
        self.progress_changed.emit(value)

    def _on_completed(self, cache_path: str) -> None:
        job = self._job_for_sender()
        if job is None:
            return
        if (
            job is not self.active_job
            or self._is_closing()
            or self._current_video() != job.video_path
        ):
            return
        self.job_completed.emit(job, cache_path)
        self._finish_job(job)

    def _on_cancelled(self) -> None:
        job = self._job_for_sender()
        if job is None or job is not self.active_job:
            return
        self.job_cancelled.emit(job)
        self._finish_job(job)

    def _on_failed(self, message: str) -> None:
        job = self._job_for_sender()
        if job is None or job is not self.active_job:
            return
        self.job_failed.emit(job, message)
        self._finish_job(job)

    def _finish_job(self, job: TranscriptionJob) -> None:
        job.thread.quit()
        if job is self.active_job:
            self.active_job = None
            self.active_changed.emit(False)

    def _on_thread_finished(self) -> None:
        job = self._job_for_sender()
        if job is not None:
            if job in self.jobs:
                self.jobs.remove(job)
            if job is self.active_job:
                self.active_job = None
                self.active_changed.emit(False)
        if self._is_closing() and not self.jobs:
            self.queue_message.emit("closed")
            return
        if not self.jobs and self.queued is not None:
            video_path, progress, chinese_source = self.queued
            self.queued = None
            if self._current_video() == video_path:
                QTimer.singleShot(
                    0,
                    lambda: self.start(video_path, progress, chinese_source),
                )
