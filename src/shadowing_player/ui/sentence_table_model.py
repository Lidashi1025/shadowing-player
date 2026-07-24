from __future__ import annotations

from dataclasses import replace

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt, Signal
from PySide6.QtGui import QBrush, QColor

from shadowing_player.subtitles.models import Sentence
from shadowing_player.ui.theme import COLORS


class SentenceTableModel(QAbstractTableModel):
    SentenceRole = Qt.ItemDataRole.UserRole + 1
    CurrentRole = Qt.ItemDataRole.UserRole + 2
    starred_changed = Signal(object, bool)

    def __init__(self) -> None:
        super().__init__()
        self.sentences: list[Sentence] = []
        self._subtitle_mode = "bilingual"
        self._current_row = -1

    def set_sentences(self, sentences: list[Sentence]) -> None:
        self.beginResetModel()
        self.sentences = list(sentences)
        self._current_row = -1
        self.endResetModel()

    def set_current_row(self, row: int) -> None:
        target = row if 0 <= row < len(self.sentences) else -1
        if target == self._current_row:
            return
        previous = self._current_row
        self._current_row = target
        for changed in {previous, target}:
            if 0 <= changed < len(self.sentences):
                self.dataChanged.emit(
                    self.index(changed, 0),
                    self.index(changed, 1),
                    [self.CurrentRole, Qt.ItemDataRole.BackgroundRole],
                )

    def toggle_star(self, row: int) -> None:
        if not 0 <= row < len(self.sentences):
            return
        sentence = self.sentences[row]
        self._set_star(row, not sentence.starred)

    def set_subtitle_mode(self, mode: str) -> None:
        self._subtitle_mode = mode
        if self.sentences:
            self.dataChanged.emit(
                self.index(0, 0),
                self.index(len(self.sentences) - 1, 0),
                [Qt.ItemDataRole.DisplayRole],
            )

    def rowCount(self, parent=QModelIndex()) -> int:  # noqa: N802
        return 0 if parent.isValid() else len(self.sentences)

    def columnCount(self, parent=QModelIndex()) -> int:  # noqa: N802
        return 0 if parent.isValid() else 2

    def data(self, index: QModelIndex, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not 0 <= index.row() < len(self.sentences):
            return None
        sentence = self.sentences[index.row()]
        if role == self.SentenceRole:
            return sentence
        if role == self.CurrentRole:
            return index.row() == self._current_row
        if role == Qt.ItemDataRole.BackgroundRole and index.row() == self._current_row:
            return QBrush(QColor(COLORS["accent_surface"]))
        if index.column() == 1:
            if role == Qt.ItemDataRole.TextAlignmentRole:
                return Qt.AlignmentFlag.AlignCenter
            if role == Qt.ItemDataRole.DisplayRole:
                return "★" if sentence.starred else "☆"
            if role == Qt.ItemDataRole.ForegroundRole:
                color = COLORS["favorite"] if sentence.starred else COLORS["text_subtle"]
                return QBrush(QColor(color))
            return None
        if role == Qt.ItemDataRole.DisplayRole:
            text = f"{sentence.index + 1}.  {sentence.text}"
            if self._subtitle_mode == "bilingual" and sentence.text_zh:
                text += f"\n{sentence.text_zh}"
            return text
        return None

    def setData(self, index: QModelIndex, value, role=Qt.ItemDataRole.EditRole) -> bool:  # noqa: N802
        if (
            not index.isValid()
            or index.column() != 1
            or role != Qt.ItemDataRole.CheckStateRole
        ):
            return False
        starred = value == Qt.CheckState.Checked
        self._set_star(index.row(), starred)
        return True

    def _set_star(self, row: int, starred: bool) -> None:
        sentence = self.sentences[row]
        updated = replace(sentence, starred=starred)
        self.sentences[row] = updated
        index = self.index(row, 1)
        self.dataChanged.emit(
            index,
            index,
            [Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.ForegroundRole],
        )
        self.starred_changed.emit(updated, starred)

    def flags(self, index: QModelIndex):
        flags = super().flags(index)
        return flags | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled

    def headerData(self, section: int, orientation, role=Qt.ItemDataRole.DisplayRole):  # noqa: N802
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return "句子" if section == 0 else "★"
        return super().headerData(section, orientation, role)
