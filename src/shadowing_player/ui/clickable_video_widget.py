from __future__ import annotations

from PySide6.QtCore import QPoint, Qt, QTimer, Signal
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication, QWidget


class ClickableVideoWidget(QWidget):
    clicked = Signal()
    double_clicked = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._press_position: QPoint | None = None
        self._suppress_release = False
        self._single_click_timer = QTimer(self)
        self._single_click_timer.setSingleShot(True)
        self._single_click_timer.timeout.connect(self.clicked.emit)

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
        if self._suppress_release:
            self._suppress_release = False
        elif (
            event.button() is Qt.MouseButton.LeftButton
            and press_position is not None
            and self.rect().contains(release_position)
            and (release_position - press_position).manhattanLength()
            <= QApplication.startDragDistance()
        ):
            self._single_click_timer.start(QApplication.doubleClickInterval())
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:  # noqa: N802 - Qt API
        if event.button() is Qt.MouseButton.LeftButton:
            self._single_click_timer.stop()
            self._press_position = None
            self._suppress_release = True
            self.double_clicked.emit()
        super().mouseDoubleClickEvent(event)
