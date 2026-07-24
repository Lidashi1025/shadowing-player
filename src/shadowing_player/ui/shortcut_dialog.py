from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QKeySequenceEdit,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from shadowing_player.shortcut_catalog import (
    default_shortcuts,
    find_shortcut_conflicts,
    normalize_shortcut,
    shortcut_definitions,
)


class ShortcutDialog(QDialog):
    def __init__(self, shortcuts: dict[str, str], parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("shortcutDialog")
        self.setWindowTitle("快捷键设置")
        self.setMinimumSize(560, 560)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 18, 20, 18)
        outer.setSpacing(12)
        title = QLabel("快捷键设置", self)
        title.setObjectName("dialogTitle")
        description = QLabel(
            "点击右侧输入框后按下新的组合键。所有可用功能都列在这里。",
            self,
        )
        description.setObjectName("dialogDescription")
        description.setWordWrap(True)
        outer.addWidget(title)
        outer.addWidget(description)

        scroll = QScrollArea(self)
        scroll.setObjectName("shortcutScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget(scroll)
        grid = QGridLayout(content)
        grid.setContentsMargins(0, 4, 8, 4)
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(8)
        self.editors: dict[str, QKeySequenceEdit] = {}
        current_category = ""
        row = 0
        defaults = default_shortcuts()
        for definition in shortcut_definitions():
            if definition.category != current_category:
                current_category = definition.category
                category = QLabel(current_category, content)
                category.setObjectName("shortcutCategory")
                grid.addWidget(category, row, 0, 1, 2)
                row += 1
            action = QWidget(content)
            action_layout = QVBoxLayout(action)
            action_layout.setContentsMargins(0, 0, 0, 0)
            action_layout.setSpacing(1)
            label = QLabel(definition.label, action)
            detail = QLabel(definition.description, action)
            detail.setObjectName("shortcutDescription")
            action_layout.addWidget(label)
            action_layout.addWidget(detail)
            editor = QKeySequenceEdit(content)
            editor.setObjectName(f"shortcut_{definition.name}")
            editor.setClearButtonEnabled(True)
            editor.setMaximumSequenceLength(1)
            editor.setKeySequence(
                QKeySequence(shortcuts.get(definition.name, defaults[definition.name]))
            )
            self.editors[definition.name] = editor
            grid.addWidget(action, row, 0)
            grid.addWidget(editor, row, 1)
            row += 1
        grid.setColumnStretch(0, 1)
        grid.setColumnMinimumWidth(1, 210)
        scroll.setWidget(content)
        outer.addWidget(scroll, 1)

        self.conflict_label = QLabel(self)
        self.conflict_label.setObjectName("shortcutConflict")
        self.conflict_label.setWordWrap(True)
        self.conflict_label.hide()
        outer.addWidget(self.conflict_label)

        footer = QHBoxLayout()
        self.restore_button = QPushButton("恢复默认", self)
        self.restore_button.setObjectName("secondaryButton")
        self.restore_button.clicked.connect(self._restore_defaults)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel,
            Qt.Orientation.Horizontal,
            self,
        )
        self.save_button = buttons.button(QDialogButtonBox.StandardButton.Save)
        self.save_button.setText("保存")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("取消")
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        footer.addWidget(self.restore_button)
        footer.addStretch(1)
        footer.addWidget(buttons)
        outer.addLayout(footer)
        for editor in self.editors.values():
            editor.keySequenceChanged.connect(self._validate_shortcuts)
        self._validate_shortcuts()

    def shortcuts(self) -> dict[str, str]:
        return {
            name: normalize_shortcut(
                editor.keySequence().toString(
                    QKeySequence.SequenceFormat.PortableText
                )
            )
            for name, editor in self.editors.items()
        }

    def _restore_defaults(self) -> None:
        for name, sequence in default_shortcuts().items():
            self.editors[name].setKeySequence(QKeySequence(sequence))

    def _validate_shortcuts(self, *_args) -> bool:
        conflicts = find_shortcut_conflicts(self.shortcuts())
        if conflicts:
            labels = {item.name: item.label for item in shortcut_definitions()}
            details = "；".join(
                f"{sequence}：{'、'.join(labels[name] for name in names)}"
                for sequence, names in conflicts.items()
            )
            self.conflict_label.setText(
                f"快捷键冲突，请修改后再保存：{details}"
            )
            self.conflict_label.show()
            self.save_button.setEnabled(False)
            return False
        self.conflict_label.hide()
        self.save_button.setEnabled(True)
        return True

    def _save(self) -> None:
        if not self._validate_shortcuts():
            return
        self.accept()
