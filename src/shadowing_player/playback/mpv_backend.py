from __future__ import annotations

import importlib
import logging
from pathlib import Path
from types import ModuleType
from typing import Any

from PySide6.QtCore import QObject, Signal


LOGGER = logging.getLogger(__name__)


class MpvBackend(QObject):
    """将 python-mpv 回调转换成可安全跨线程传递的 Qt 信号。"""

    pause_changed = Signal(bool)
    file_loaded = Signal(str)
    position_changed = Signal(float)
    duration_changed = Signal(float)
    error = Signal(str)

    def __init__(self, window_id: int, mpv_module: ModuleType | Any | None = None) -> None:
        super().__init__()
        module = mpv_module or importlib.import_module("mpv")
        self._player = module.MPV(
            wid=str(window_id),
            input_default_bindings=False,
            input_vo_keyboard=False,
            osc=False,
            idle="yes",
            keep_open="yes",
            hr_seek="yes",
            audio_pitch_correction="yes",
            speed=0.75,
            sid="no",
            log_handler=self._handle_mpv_log,
            loglevel="v",
        )
        self._shutdown = False
        self._player.observe_property("pause", self._on_pause)
        self._player.observe_property("time-pos", self._on_time_position)
        self._player.observe_property("duration", self._on_duration)

    def open_file(self, path: str | Path) -> None:
        movie = str(Path(path))
        try:
            self._player.command("loadfile", movie, "replace")
            self._player.pause = False
            self.file_loaded.emit(movie)
            LOGGER.info("已打开视频：%s", movie)
        except Exception as exc:  # python-mpv exposes several backend exception types
            message = f"无法打开视频：{exc}"
            LOGGER.exception(message)
            self.error.emit(message)

    def toggle_pause(self) -> None:
        self._player.pause = not bool(self._player.pause)

    def play(self) -> None:
        self._player.pause = False

    def pause(self) -> None:
        self._player.pause = True

    def seek_ms(self, position_ms: int) -> None:
        self._player.command("seek", max(0, position_ms) / 1000.0, "absolute+exact")

    @property
    def position_ms(self) -> int:
        return int(float(self._player.time_pos or 0.0) * 1000)

    @property
    def duration_ms(self) -> int:
        return int(float(self._player.duration or 0.0) * 1000)

    @property
    def is_paused(self) -> bool:
        return bool(self._player.pause)

    def set_speed(self, speed: float) -> None:
        self._player.speed = float(speed)
        LOGGER.info("播放速度：%.2fx；音调校正已启用", speed)

    def audio_filters(self) -> Any:
        try:
            return self._player.af
        except Exception:
            return []

    def shutdown(self) -> None:
        if self._shutdown:
            return
        self._shutdown = True
        self._player.terminate()

    def _on_pause(self, _name: str, value: bool | None) -> None:
        if value is not None:
            self.pause_changed.emit(bool(value))

    def _on_time_position(self, _name: str, value: float | None) -> None:
        if value is not None:
            self.position_changed.emit(float(value))

    def _on_duration(self, _name: str, value: float | None) -> None:
        if value is not None:
            self.duration_changed.emit(float(value))

    def _handle_mpv_log(self, level: str, component: str, message: str) -> None:
        cleaned = message.strip()
        if "scaletempo2" in cleaned.lower():
            LOGGER.info("mpv %s: %s", component, cleaned)
        elif level in {"error", "fatal"}:
            LOGGER.error("mpv %s: %s", component, cleaned)
        elif level == "warn":
            LOGGER.warning("mpv %s: %s", component, cleaned)
