from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, Signal

from shadowing_player.review.review_controller import ReviewController, ReviewItem
from shadowing_player.subtitles.models import Sentence


class FakeBackend(QObject):
    file_loaded = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.opened: list[str] = []

    def open_file(self, path: str) -> None:
        self.opened.append(path)
        self.file_loaded.emit(path)


class FakeSession(QObject):
    completed = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.loaded: list[list[Sentence]] = []
        self.play_count = 0
        self.modes: list[object] = []

    def set_mode(self, mode) -> None:
        self.modes.append(mode)

    def load_sentences(self, sentences, video_duration_ms=None) -> None:
        self.loaded.append(sentences)

    def play_current(self) -> None:
        self.play_count += 1


def test_review_controller_continues_across_two_videos(qtbot, tmp_path: Path) -> None:
    first = tmp_path / "one.mp4"
    second = tmp_path / "two.mp4"
    first.touch()
    second.touch()
    items = [
        ReviewItem(first, Sentence(0, 1_000, 2_000, "One", id=1)),
        ReviewItem(second, Sentence(0, 3_000, 4_000, "Two", id=2)),
    ]
    backend = FakeBackend()
    session = FakeSession()
    controller = ReviewController(backend, session)

    controller.start(items)
    session.completed.emit()

    assert backend.opened == [str(first), str(second)]
    assert [loaded[0].text for loaded in session.loaded] == ["One", "Two"]
    assert session.play_count == 2


def test_review_controller_skips_missing_video_and_reports_it(qtbot, tmp_path: Path) -> None:
    missing = tmp_path / "missing.mp4"
    existing = tmp_path / "existing.mp4"
    existing.touch()
    backend = FakeBackend()
    session = FakeSession()
    controller = ReviewController(backend, session)
    warnings: list[str] = []
    controller.warning.connect(warnings.append)

    controller.start(
        [
            ReviewItem(missing, Sentence(0, 0, 1_000, "Missing", id=1)),
            ReviewItem(existing, Sentence(0, 0, 1_000, "Existing", id=2)),
        ]
    )

    assert backend.opened == [str(existing)]
    assert session.loaded[0][0].text == "Existing"
    assert warnings and "已移动" in warnings[0]
