from __future__ import annotations

from pathlib import Path

from shadowing_player.transcription.service import TranscriptionCancelled
from shadowing_player.transcription.worker import CancellationToken, TranscriptionWorker


class FakeService:
    def __init__(self, result: Path | Exception) -> None:
        self.result = result

    def transcribe(self, _video, on_progress, on_phase, is_cancelled):
        on_phase("transcribing")
        on_progress(42)
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


def test_worker_only_reports_results_through_signals(qtbot, tmp_path: Path) -> None:
    result = tmp_path / "cache.srt"
    worker = TranscriptionWorker(
        tmp_path / "video.mp4", FakeService(result), CancellationToken()
    )
    phases: list[str] = []
    progress: list[int] = []
    completed: list[str] = []
    worker.phase_changed.connect(phases.append)
    worker.progress_changed.connect(progress.append)
    worker.completed.connect(completed.append)

    worker.run()

    assert phases == ["transcribing"]
    assert progress == [42]
    assert completed == [str(result)]


def test_worker_reports_cancelled_without_failure(qtbot, tmp_path: Path) -> None:
    worker = TranscriptionWorker(
        tmp_path / "video.mp4",
        FakeService(TranscriptionCancelled()),
        CancellationToken(),
    )
    cancelled: list[bool] = []
    failures: list[str] = []
    worker.cancelled.connect(lambda: cancelled.append(True))
    worker.failed.connect(failures.append)

    worker.run()

    assert cancelled == [True]
    assert failures == []
