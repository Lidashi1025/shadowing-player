from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, Signal

from shadowing_player.playback.session_controller import PlaybackMode
from shadowing_player.subtitles.models import Sentence


@dataclass(frozen=True, slots=True)
class ReviewItem:
    video_path: Path
    sentence: Sentence


class ReviewController(QObject):
    warning = Signal(str)
    current_changed = Signal(int, object)
    completed = Signal()

    def __init__(self, backend: Any, session: Any) -> None:
        super().__init__()
        self.backend = backend
        self.session = session
        self.items: list[ReviewItem] = []
        self.index = -1
        self.active = False
        self._current_video: Path | None = None
        self._waiting_video: Path | None = None
        self.backend.file_loaded.connect(self._on_file_loaded)
        self.session.completed.connect(self._on_sentence_completed)

    def start(self, items: list[ReviewItem]) -> None:
        self.items = list(items)
        self.index = 0
        self.active = True
        self._advance_to_available()

    def stop(self) -> None:
        self.active = False
        self._waiting_video = None

    def _advance_to_available(self) -> None:
        while self.active and self.index < len(self.items):
            item = self.items[self.index]
            if item.video_path.is_file():
                self._prepare(item)
                return
            self.warning.emit(
                f"源视频已移动，已跳过：{item.video_path.name}"
            )
            self.index += 1
        if self.active:
            self.active = False
            self.completed.emit()

    def _prepare(self, item: ReviewItem) -> None:
        target = item.video_path.resolve()
        if self._current_video != target:
            self._current_video = target
            self._waiting_video = target
            self.backend.open_file(str(target))
            return
        self._play(item)

    def _on_file_loaded(self, path: str) -> None:
        if not self.active or self._waiting_video is None:
            return
        loaded = Path(path).resolve()
        if loaded != self._waiting_video:
            return
        self._waiting_video = None
        self._play(self.items[self.index])

    def _play(self, item: ReviewItem) -> None:
        self.session.set_mode(PlaybackMode.SENTENCE_PRACTICE)
        self.session.load_sentences([item.sentence])
        self.current_changed.emit(self.index, item)
        self.session.play_current()

    def _on_sentence_completed(self) -> None:
        if not self.active:
            return
        self.index += 1
        self._advance_to_available()
