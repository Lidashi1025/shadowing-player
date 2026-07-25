from __future__ import annotations

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication, QWidget


class ClickableVideoWidget(QWidget):
    clicked = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._press_position: QPoint | None = None

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802 - Qt API
        if event.button() is Qt.MouseButton.LeftButton:
            self._press_position = event.position().toPoint()
        else:
            self._press_position = None
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802 - Qt API
        release_position = event.position().toPoint()
        press_position = self._press_position
        self._press_position = None
        if (
            event.button() is Qt.MouseButton.LeftButton
            and press_position is not None
            and self.rect().contains(release_position)
            and (release_position - press_position).manhattanLength()
            <= QApplication.startDragDistance()
        ):
            self.clicked.emit()
        super().mouseReleaseEvent(event)
