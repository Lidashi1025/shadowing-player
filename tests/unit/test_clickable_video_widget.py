from PySide6.QtCore import QPoint, Qt

from shadowing_player.ui.clickable_video_widget import ClickableVideoWidget


def _shown_widget(qtbot) -> ClickableVideoWidget:
    widget = ClickableVideoWidget()
    widget.resize(240, 135)
    qtbot.addWidget(widget)
    widget.show()
    return widget


def test_left_click_emits_clicked_once(qtbot) -> None:
    widget = _shown_widget(qtbot)

    with qtbot.waitSignal(widget.clicked, timeout=500):
        qtbot.mouseClick(
            widget,
            Qt.MouseButton.LeftButton,
            pos=QPoint(120, 68),
        )


def test_right_click_does_not_emit_clicked(qtbot) -> None:
    widget = _shown_widget(qtbot)
    calls: list[bool] = []
    widget.clicked.connect(lambda: calls.append(True))

    qtbot.mouseClick(
        widget,
        Qt.MouseButton.RightButton,
        pos=QPoint(120, 68),
    )

    assert calls == []


def test_left_button_drag_does_not_emit_clicked(qtbot) -> None:
    widget = _shown_widget(qtbot)
    calls: list[bool] = []
    widget.clicked.connect(lambda: calls.append(True))

    qtbot.mousePress(
        widget,
        Qt.MouseButton.LeftButton,
        pos=QPoint(20, 68),
    )
    qtbot.mouseMove(widget, QPoint(120, 68))
    qtbot.mouseRelease(
        widget,
        Qt.MouseButton.LeftButton,
        pos=QPoint(120, 68),
    )

    assert calls == []
