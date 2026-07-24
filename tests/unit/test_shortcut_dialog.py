from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence

from shadowing_player.shortcut_catalog import default_shortcuts
from shadowing_player.ui.shortcut_dialog import ShortcutDialog


def test_shortcut_dialog_edits_and_restores_all_actions(qtbot) -> None:
    dialog = ShortcutDialog(default_shortcuts())
    qtbot.addWidget(dialog)

    dialog.editors["play_pause"].setKeySequence(QKeySequence("P"))
    assert dialog.shortcuts()["play_pause"] == "P"

    qtbot.mouseClick(dialog.restore_button, Qt.MouseButton.LeftButton)

    assert dialog.shortcuts() == default_shortcuts()
    assert len(dialog.editors) == len(default_shortcuts())


def test_shortcut_dialog_shows_duplicate_inline_and_disables_save(qtbot) -> None:
    dialog = ShortcutDialog(default_shortcuts())
    qtbot.addWidget(dialog)
    dialog.editors["repeat"].setKeySequence(QKeySequence("Space"))

    assert not dialog.conflict_label.isHidden()
    assert "Space" in dialog.conflict_label.text()
    assert dialog.save_button.isEnabled() is False

    dialog.editors["repeat"].setKeySequence(QKeySequence("Left"))
    assert dialog.conflict_label.isHidden()
    assert dialog.save_button.isEnabled() is True
