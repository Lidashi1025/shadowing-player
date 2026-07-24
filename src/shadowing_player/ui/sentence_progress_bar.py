from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QMouseEvent, QPainter
from PySide6.QtWidgets import QWidget

from shadowing_player.ui.theme import COLORS


class SentenceProgressBar(QWidget):
    sentence_clicked = Signal(int)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._count = 0
        self._current = -1
        self.setFixedHeight(12)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def set_sentence_count(self, count: int) -> None:
        self._count = max(0, count)
        self._current = 0 if count else -1
        self.update()

    def set_current_index(self, index: int) -> None:
        self._current = index
        self.update()

    def paintEvent(self, _event) -> None:  # noqa: N802 - Qt API
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor(COLORS["surface"]))
        if not self._count:
            return
        cell_width = self.width() / self._count
        for index in range(self._count):
            left = round(index * cell_width)
            right = round((index + 1) * cell_width)
            color = (
                QColor(COLORS["accent"])
                if index == self._current
                else QColor(COLORS["border"])
            )
            painter.fillRect(
                left + 1,
                1,
                max(1, right - left - 2),
                self.height() - 2,
                color,
            )

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802 - Qt API
        if self._count and event.button() == Qt.MouseButton.LeftButton:
            index = min(self._count - 1, int(event.position().x() / max(1, self.width()) * self._count))
            self.sentence_clicked.emit(index)
        super().mouseReleaseEvent(event)
