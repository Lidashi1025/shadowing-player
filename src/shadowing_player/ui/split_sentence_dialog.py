from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QPlainTextEdit,
)

from shadowing_player.subtitles.models import Sentence


def propose_text_split(text: str, ratio: float, chinese: bool = False) -> tuple[str, str]:
    cleaned = text.strip()
    if not cleaned:
        return "", ""
    if chinese:
        point = min(max(1, round(len(cleaned) * ratio)), len(cleaned) - 1)
        return cleaned[:point].strip(), cleaned[point:].strip()
    words = cleaned.split()
    if len(words) < 2:
        return cleaned, ""
    point = min(max(1, round(len(words) * ratio)), len(words) - 1)
    return " ".join(words[:point]), " ".join(words[point:])


class SplitSentenceDialog(QDialog):
    def __init__(self, sentence: Sentence, ratio: float, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("拆分句子")
        left_en, right_en = propose_text_split(sentence.text, ratio)
        left_zh, right_zh = propose_text_split(sentence.text_zh, ratio, chinese=True)
        layout = QFormLayout(self)
        self.left_en = QPlainTextEdit(left_en, self)
        self.right_en = QPlainTextEdit(right_en, self)
        self.left_zh = QPlainTextEdit(left_zh, self)
        self.right_zh = QPlainTextEdit(right_zh, self)
        layout.addRow("前半句英文", self.left_en)
        layout.addRow("后半句英文", self.right_en)
        layout.addRow("前半句中文", self.left_zh)
        layout.addRow("后半句中文", self.right_zh)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel,
            self,
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    @classmethod
    def get_values(
        cls, parent, sentence: Sentence, ratio: float
    ) -> tuple[str, str, str, str] | None:
        dialog = cls(sentence, ratio, parent)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return None
        return (
            dialog.left_en.toPlainText().strip(),
            dialog.right_en.toPlainText().strip(),
            dialog.left_zh.toPlainText().strip(),
            dialog.right_zh.toPlainText().strip(),
        )
