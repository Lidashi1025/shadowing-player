from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from shadowing_player.runtime.setup_checks import SetupCheck
from shadowing_player.ui import strings


class SetupChecklistDialog(QDialog):
    """First-run / on-demand environment checklist."""

    def __init__(
        self,
        checks: list[SetupCheck],
        *,
        allow_dismiss: bool = True,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(strings.SETUP_CHECKLIST_TITLE)
        self.setModal(True)
        self.resize(560, 420)
        self._checks = checks

        root = QVBoxLayout(self)
        intro = QLabel(strings.SETUP_CHECKLIST_INTRO, self)
        intro.setWordWrap(True)
        intro.setObjectName("setupIntro")
        root.addWidget(intro)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        body = QWidget(scroll)
        body_layout = QVBoxLayout(body)
        body_layout.setSpacing(10)
        for item in checks:
            body_layout.addWidget(self._row_for(item, body))
        body_layout.addStretch(1)
        scroll.setWidget(body)
        root.addWidget(scroll, 1)

        self.dismiss_check = QCheckBox(strings.SETUP_CHECKLIST_DISMISS, self)
        self.dismiss_check.setVisible(allow_dismiss)
        root.addWidget(self.dismiss_check)

        buttons = QDialogButtonBox(self)
        self.close_button = buttons.addButton(
            strings.SETUP_CHECKLIST_CLOSE, QDialogButtonBox.ButtonRole.AcceptRole
        )
        buttons.accepted.connect(self.accept)
        root.addWidget(buttons)

    def dismiss_future_prompts(self) -> bool:
        return self.dismiss_check.isChecked()

    def _row_for(self, item: SetupCheck, parent: QWidget) -> QWidget:
        row = QWidget(parent)
        layout = QVBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        header = QHBoxLayout()
        status = QLabel("✓" if item.ok else "✗", row)
        status.setObjectName("setupOk" if item.ok else "setupBad")
        status.setFixedWidth(18)
        title = QLabel(item.title, row)
        title.setObjectName("setupTitle")
        badge = QLabel(
            strings.SETUP_REQUIRED if item.required else strings.SETUP_OPTIONAL,
            row,
        )
        badge.setObjectName("setupBadge")
        header.addWidget(status)
        header.addWidget(title, 1)
        header.addWidget(badge)
        layout.addLayout(header)

        detail = QLabel(item.detail, row)
        detail.setWordWrap(True)
        detail.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        detail.setObjectName("setupDetail")
        layout.addWidget(detail)

        if not item.ok and item.fix_hint:
            hint = QLabel(item.fix_hint, row)
            hint.setWordWrap(True)
            hint.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            hint.setObjectName("setupHint")
            layout.addWidget(hint)

        return row
