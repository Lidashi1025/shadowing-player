from __future__ import annotations

from PySide6.QtCore import QAbstractListModel, QModelIndex, Qt

from shadowing_player.subtitles.models import Sentence


class SentenceListModel(QAbstractListModel):
    SentenceRole = Qt.ItemDataRole.UserRole + 1

    def __init__(self) -> None:
        super().__init__()
        self._sentences: list[Sentence] = []

    def set_sentences(self, sentences: list[Sentence]) -> None:
        self.beginResetModel()
        self._sentences = list(sentences)
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()) -> int:  # noqa: N802 - Qt API
        return 0 if parent.isValid() else len(self._sentences)

    def data(self, index: QModelIndex, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not 0 <= index.row() < len(self._sentences):
            return None
        sentence = self._sentences[index.row()]
        if role == Qt.ItemDataRole.DisplayRole:
            return f"{sentence.index + 1}.  {sentence.text}"
        if role == self.SentenceRole:
            return sentence
        return None
