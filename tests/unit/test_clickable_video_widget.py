from PySide6.QtCore import QPoint, Qt
from PySide6.QtWidgets import QApplication

from shadowing_player.ui.clickable_video_widget import ClickableVideoWidget


def _shown_widget(qtbot) -> ClickableVideoWidget:
    widget = ClickableVideoWidget()
    widget.resize(240, 135)
    qtbot.addWidget(widget)
    widget.show()
    return widget


def test_left_click_emits_clicked_once(qtbot) -> None:
    widget = _shown_widget(qtbot)

    with qtbot.waitSignal(widget.clicked, timeout=1_000):
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


def test_double_click_emits_only_double_clicked(qtbot) -> None:
    widget = _shown_widget(qtbot)
    single_calls: list[bool] = []
    double_calls: list[bool] = []
    widget.clicked.connect(lambda: single_calls.append(True))
    widget.double_clicked.connect(lambda: double_calls.append(True))

    qtbot.mouseDClick(
        widget,
        Qt.MouseButton.LeftButton,
        pos=QPoint(120, 68),
    )
    qtbot.wait(QApplication.doubleClickInterval() + 50)

    assert double_calls == [True]
    assert single_calls == []


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
