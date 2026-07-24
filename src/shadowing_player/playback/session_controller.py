from __future__ import annotations

import math
import time
from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from PySide6.QtCore import QObject, QTimer, Signal

from shadowing_player.subtitles.models import Sentence


class PlaybackMode(str, Enum):
    WATCH = "watch"
    SENTENCE_PRACTICE = "sentence_practice"
    SINGLE_LOOP = "single_loop"
    SHADOWING = "shadowing"


class SessionPhase(str, Enum):
    PAUSED = "paused"
    PLAYING = "playing"
    BLANK = "blank"
    COMPLETED = "completed"


@dataclass(slots=True)
class PracticeConfig:
    blank_multiplier: float = 1.5
    plays_per_sentence: int = 1
    loop_count: int | None = 3
    auto_advance: bool = True


class PlayerPort(Protocol):
    def seek_ms(self, position_ms: int) -> None: ...
    def play(self) -> None: ...
    def pause(self) -> None: ...


class CountdownPort(Protocol):
    def start(self, duration_ms: int, on_tick, on_finished) -> None: ...
    def cancel(self) -> None: ...
    def pause(self) -> None: ...
    def resume(self) -> None: ...


class QtCountdownTimer:
    def __init__(self) -> None:
        self._timer = QTimer()
        self._timer.setInterval(100)
        self._timer.timeout.connect(self._update)
        self._remaining_ms = 0
        self._deadline = 0.0
        self._on_tick = lambda _remaining: None
        self._on_finished = lambda: None
        self._paused = False

    def start(self, duration_ms: int, on_tick, on_finished) -> None:
        self.cancel()
        self._remaining_ms = max(0, int(duration_ms))
        self._on_tick = on_tick
        self._on_finished = on_finished
        self._paused = False
        self._deadline = time.monotonic() + self._remaining_ms / 1000.0
        self._on_tick(self._remaining_ms)
        self._timer.start()

    def cancel(self) -> None:
        self._timer.stop()
        self._remaining_ms = 0
        self._paused = False

    def pause(self) -> None:
        if not self._timer.isActive():
            return
        self._remaining_ms = max(0, int((self._deadline - time.monotonic()) * 1000))
        self._timer.stop()
        self._paused = True

    def resume(self) -> None:
        if not self._paused or self._remaining_ms <= 0:
            return
        self._paused = False
        self._deadline = time.monotonic() + self._remaining_ms / 1000.0
        self._timer.start()

    def _update(self) -> None:
        self._remaining_ms = max(0, int((self._deadline - time.monotonic()) * 1000))
        self._on_tick(self._remaining_ms)
        if self._remaining_ms > 0:
            return
        callback = self._on_finished
        self.cancel()
        callback()


class SessionController(QObject):
    current_changed = Signal(int, object)
    mode_changed = Signal(object)
    prompt_changed = Signal(str)
    phase_changed = Signal(str)
    completed = Signal()

    def __init__(
        self,
        player: PlayerPort,
        timer: CountdownPort | None = None,
        config: PracticeConfig | None = None,
    ) -> None:
        super().__init__()
        self.player = player
        self.timer = timer or QtCountdownTimer()
        self.config = config or PracticeConfig()
        self.sentences: list[Sentence] = []
        self.video_duration_ms: int | None = None
        self.current_index = -1
        self.mode = PlaybackMode.WATCH
        self.phase = SessionPhase.PAUSED
        self._iteration = 0
        self._timer_generation = 0
        self._blank_paused = False

    @property
    def current_sentence(self) -> Sentence | None:
        if 0 <= self.current_index < len(self.sentences):
            return self.sentences[self.current_index]
        return None

    @property
    def blank_paused(self) -> bool:
        return self._blank_paused

    def load_sentences(self, sentences: list[Sentence], video_duration_ms: int | None = None) -> None:
        self._invalidate_timer()
        self.sentences = list(sentences)
        self.video_duration_ms = video_duration_ms
        self.current_index = 0 if sentences else -1
        self._iteration = 0
        self._set_phase(SessionPhase.PAUSED)
        if self.current_sentence is not None:
            self.current_changed.emit(self.current_index, self.current_sentence)

    def set_mode(self, mode: PlaybackMode) -> None:
        self._invalidate_timer()
        self.mode = mode
        self.mode_changed.emit(mode)
        self._iteration = 0
        self._set_phase(SessionPhase.PAUSED)
        self.prompt_changed.emit("")

    def select_sentence(self, index: int, autoplay: bool = False) -> None:
        if not self.sentences:
            return
        self._invalidate_timer()
        self.current_index = min(max(0, index), len(self.sentences) - 1)
        self._iteration = 0
        self.current_changed.emit(self.current_index, self.current_sentence)
        if autoplay:
            if self.mode in {PlaybackMode.WATCH, PlaybackMode.SHADOWING}:
                start, _end = self.current_sentence.play_window(
                    self.video_duration_ms
                )
                self.player.seek_ms(start)
            self.play_current()
        else:
            start, _end = self.current_sentence.play_window(self.video_duration_ms)
            self.player.seek_ms(start)
            self.player.pause()
            self._set_phase(SessionPhase.PAUSED)

    def play_current(self) -> None:
        self._invalidate_timer()
        self._iteration = 0
        if self.mode in {PlaybackMode.WATCH, PlaybackMode.SHADOWING}:
            self.player.play()
            self._set_phase(SessionPhase.PLAYING)
            return
        sentence = self.current_sentence
        if sentence is None:
            return
        self._start_iteration()

    def repeat_current(self) -> None:
        sentence = self.current_sentence
        if sentence is None:
            return
        if self.mode in {PlaybackMode.WATCH, PlaybackMode.SHADOWING}:
            self._invalidate_timer()
            start, _end = sentence.play_window(self.video_duration_ms)
            self.player.seek_ms(start)
            self.player.play()
            self._set_phase(SessionPhase.PLAYING)
            return
        self.play_current()

    def next_sentence(self, autoplay: bool = True) -> None:
        if self.current_index + 1 >= len(self.sentences):
            self.player.pause()
            self._set_phase(SessionPhase.COMPLETED)
            self.completed.emit()
            return
        self.select_sentence(self.current_index + 1, autoplay=autoplay)

    def previous_sentence(self, autoplay: bool = True) -> None:
        self.select_sentence(max(0, self.current_index - 1), autoplay=autoplay)

    def on_position_ms(self, position_ms: int) -> None:
        if not self.sentences:
            return
        if self.mode in {PlaybackMode.WATCH, PlaybackMode.SHADOWING}:
            index = self._index_at_position(position_ms)
            if index != self.current_index:
                self.current_index = index
                self.current_changed.emit(index, self.current_sentence)
            return
        sentence = self.current_sentence
        if sentence is None or self.phase is not SessionPhase.PLAYING:
            return
        _start, end = sentence.play_window(self.video_duration_ms)
        if position_ms >= end:
            self._finish_iteration()

    def sync_background_load(self, position_ms: int, *, playing: bool) -> None:
        """Align newly loaded sentences without seeking or changing mpv playback."""
        if not self.sentences:
            return
        index = self._index_at_position(position_ms)
        if index != self.current_index:
            self.current_index = index
            self.current_changed.emit(index, self.current_sentence)
        self._set_phase(
            SessionPhase.PLAYING if playing else SessionPhase.PAUSED
        )

    def toggle_pause(self) -> None:
        if self.phase is SessionPhase.BLANK:
            if self._blank_paused:
                self.timer.resume()
                self._blank_paused = False
            else:
                self.timer.pause()
                self._blank_paused = True
            self.phase_changed.emit(self.phase.value)
            return
        if self.phase is SessionPhase.PLAYING:
            self.player.pause()
            self._set_phase(SessionPhase.PAUSED)
        else:
            self.player.play()
            self._set_phase(SessionPhase.PLAYING)

    def _start_iteration(self) -> None:
        sentence = self.current_sentence
        if sentence is None:
            return
        start, _end = sentence.play_window(self.video_duration_ms)
        self.player.seek_ms(start)
        self.player.play()
        self._set_phase(SessionPhase.PLAYING)

    def _finish_iteration(self) -> None:
        self._set_phase(SessionPhase.PAUSED)
        self._iteration += 1
        if self.mode is PlaybackMode.SENTENCE_PRACTICE:
            if self._iteration < self.config.plays_per_sentence:
                self._start_iteration()
            else:
                self._begin_blank()
            return
        if self.mode is PlaybackMode.SINGLE_LOOP:
            if self.config.loop_count is None or self._iteration < self.config.loop_count:
                self._start_iteration()
            else:
                self.player.pause()

    def _begin_blank(self) -> None:
        sentence = self.current_sentence
        if sentence is None:
            return
        self._blank_paused = False
        self.player.pause()
        self._set_phase(SessionPhase.BLANK)
        duration_ms = max(1, round(sentence.duration_ms * self.config.blank_multiplier))
        self._timer_generation += 1
        generation = self._timer_generation
        self.timer.start(
            duration_ms,
            lambda remaining: self._on_blank_tick(generation, remaining),
            lambda: self._finish_blank(generation),
        )

    def _on_blank_tick(self, generation: int, remaining_ms: int) -> None:
        if generation != self._timer_generation:
            return
        seconds = max(0, math.ceil(remaining_ms / 1000))
        self.prompt_changed.emit(f"轮到你说！ {seconds} 秒")

    def _finish_blank(self, generation: int) -> None:
        if generation != self._timer_generation:
            return
        self.prompt_changed.emit("")
        if not self.config.auto_advance:
            self.player.pause()
            self._set_phase(SessionPhase.PAUSED)
            return
        self.next_sentence(autoplay=True)

    def _invalidate_timer(self) -> None:
        self._timer_generation += 1
        self.timer.cancel()
        self._blank_paused = False

    def _index_at_position(self, position_ms: int) -> int:
        index = 0
        for candidate, sentence in enumerate(self.sentences):
            if position_ms < sentence.start_ms:
                break
            index = candidate
        return index

    def _set_phase(self, phase: SessionPhase) -> None:
        self.phase = phase
        self.phase_changed.emit(phase.value)
