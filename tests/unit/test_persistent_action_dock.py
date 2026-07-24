from PySide6.QtCore import Qt

from shadowing_player.playback.session_controller import PlaybackMode
from shadowing_player.ui.persistent_action_dock import PersistentActionDock


def test_action_dock_exposes_two_rows_and_all_action_buttons(qtbot) -> None:
    dock = PersistentActionDock()
    qtbot.addWidget(dock)

    assert dock.objectName() == "persistentActionDock"
    assert dock.primary_row.count() == 10
    assert dock.settings_row.count() == 9
    assert dock.single_loop_button.isCheckable()
    assert dock.subtitle_action_button.isCheckable()
    assert dock.star_button.isCheckable()
    assert dock.fullscreen_button.isCheckable()


def test_action_dock_state_copy_is_explicit(qtbot) -> None:
    dock = PersistentActionDock()
    qtbot.addWidget(dock)

    dock.set_playing(True)
    dock.set_mode(PlaybackMode.SENTENCE_PRACTICE)
    dock.set_subtitle_mode("bilingual")
    dock.set_starred(True, enabled=True)
    dock.set_fullscreen(True)

    assert dock.play_button.text() == "暂停"
    assert dock.mode_action_button.text() == "模式 · 跟读"
    assert dock.subtitle_action_button.text() == "字幕 · 双语"
    assert dock.star_button.text() == "★ 已收藏"
    assert dock.fullscreen_button.text() == "退出全屏"
    assert dock.star_button.isChecked()


def test_action_buttons_emit_catalog_action_names(qtbot) -> None:
    dock = PersistentActionDock()
    qtbot.addWidget(dock)
    requested: list[str] = []
    dock.action_requested.connect(requested.append)

    qtbot.mouseClick(dock.speed_down_button, Qt.MouseButton.LeftButton)
    qtbot.mouseClick(dock.mode_action_button, Qt.MouseButton.LeftButton)
    qtbot.mouseClick(dock.shortcut_button, Qt.MouseButton.LeftButton)

    assert requested == ["speed_down", "mode", "shortcut_help"]


def test_shortcut_hints_include_current_bindings(qtbot) -> None:
    dock = PersistentActionDock()
    qtbot.addWidget(dock)

    dock.set_shortcut_hints(
        {
            "play_pause": "Space",
            "repeat": "",
            "star": "Ctrl+S",
            "shortcut_help": "F1",
        }
    )

    assert "Space" in dock.play_button.toolTip()
    assert "未设置" in dock.repeat_button.toolTip()
    assert "Ctrl+S" in dock.star_button.toolTip()
    assert "F1" in dock.shortcut_button.toolTip()
