from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QListWidget,
    QVBoxLayout,
)

from shadowing_player.review.review_controller import ReviewItem


class ReviewDialog(QDialog):
    def __init__(self, items: list[ReviewItem], parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("复习清单")
        self.resize(620, 420)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"共收藏 {len(items)} 句", self))
        listing = QListWidget(self)
        for item in items:
            listing.addItem(
                f"{item.video_path.name} · {item.sentence.index + 1}\n"
                f"{item.sentence.text}"
            )
        layout.addWidget(listing)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel,
            self,
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("开始复习")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    @classmethod
    def confirm(cls, items: list[ReviewItem], parent=None) -> bool:
        return cls(items, parent).exec() == QDialog.DialogCode.Accepted
