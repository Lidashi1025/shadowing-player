from __future__ import annotations

import time
from collections.abc import Callable

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
)


def _format_remaining(seconds: float) -> str:
    rounded = max(0, int(round(seconds)))
    minutes, seconds = divmod(rounded, 60)
    if minutes:
        return f"{minutes}分{seconds:02d}秒"
    return f"{seconds}秒"


class TranscriptionStatusBar(QFrame):
    cancel_requested = Signal()

    def __init__(
        self,
        parent=None,
        *,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("transcriptionStatus")
        self._clock = clock
        self._started_at = 0.0
        self._phase = "transcribing"

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 7, 16, 7)
        layout.setSpacing(12)
        self.label = QLabel("正在准备英文字幕…", self)
        self.label.setObjectName("transcriptionLabel")
        self.progress = QProgressBar(self)
        self.progress.setObjectName("transcriptionProgress")
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setMinimumWidth(220)
        self.progress.setMaximumWidth(420)
        self.cancel_button = QPushButton("取消", self)
        self.cancel_button.setObjectName("transcriptionCancel")
        self.cancel_button.setFixedWidth(64)
        self.cancel_button.clicked.connect(self.cancel_requested)
        layout.addWidget(self.label, 1)
        layout.addWidget(self.progress)
        layout.addWidget(self.cancel_button)
        self.hide()

    def start(self) -> None:
        self._started_at = self._clock()
        self._phase = "transcribing"
        self.label.setText("正在准备英文字幕…")
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.cancel_button.setEnabled(True)
        self.show()

    def set_phase(self, phase: str) -> None:
        self._phase = phase
        if phase == "downloading_model":
            self.label.setText("正在准备语音模型…")
            self.progress.setRange(0, 0)
        elif phase == "transcribing":
            self.label.setText("正在后台转写英文字幕…")
            self.progress.setRange(0, 100)

    def set_progress(self, value: int) -> None:
        value = max(0, min(100, int(value)))
        if self.progress.maximum() == 0:
            self.progress.setRange(0, 100)
        self.progress.setValue(value)
        if value <= 0:
            self.label.setText("正在后台转写英文字幕… 0%")
            return
        elapsed = max(0.0, self._clock() - self._started_at)
        remaining = elapsed * (100 - value) / value
        self.label.setText(
            f"正在后台转写英文字幕… {value}% · 约 {_format_remaining(remaining)}"
        )

    def set_cancelling(self) -> None:
        self.label.setText("正在取消转写…")
        self.cancel_button.setEnabled(False)

    def reset(self) -> None:
        self.hide()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.cancel_button.setEnabled(True)
