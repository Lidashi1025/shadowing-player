from __future__ import annotations

from PySide6.QtCore import QRect
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QStyle, QStyledItemDelegate, QStyleOptionViewItem

from shadowing_player.ui.sentence_table_model import SentenceTableModel
from shadowing_player.ui.theme import COLORS


class SentenceItemDelegate(QStyledItemDelegate):
    """Draw one playback marker while suppressing per-cell focus frames."""

    def paint(self, painter: QPainter, option, index) -> None:
        clean = QStyleOptionViewItem(option)
        clean.state &= ~QStyle.StateFlag.State_HasFocus
        super().paint(painter, clean, index)
        if (
            index.column() == 0
            and bool(index.data(SentenceTableModel.CurrentRole))
        ):
            painter.save()
            painter.fillRect(
                QRect(option.rect.left(), option.rect.top(), 3, option.rect.height()),
                QColor(COLORS["accent"]),
            )
            painter.restore()
