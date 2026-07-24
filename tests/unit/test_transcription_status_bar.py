from PySide6.QtCore import Qt

from shadowing_player.ui.transcription_status_bar import TranscriptionStatusBar


def test_transcription_status_bar_reports_progress_and_cancels(qtbot) -> None:
    now = [100.0]
    bar = TranscriptionStatusBar(clock=lambda: now[0])
    qtbot.addWidget(bar)
    cancelled: list[bool] = []
    bar.cancel_requested.connect(lambda: cancelled.append(True))

    bar.start()
    now[0] = 130.0
    bar.set_phase("transcribing")
    bar.set_progress(25)

    assert not bar.isHidden()
    assert bar.progress.minimum() == 0
    assert bar.progress.maximum() == 100
    assert bar.progress.value() == 25
    assert "25%" in bar.label.text()
    assert "约 1分30秒" in bar.label.text()

    qtbot.mouseClick(bar.cancel_button, Qt.MouseButton.LeftButton)
    assert cancelled == [True]

    bar.reset()
    assert bar.isHidden()


def test_transcription_status_bar_uses_busy_state_while_loading_model(qtbot) -> None:
    bar = TranscriptionStatusBar()
    qtbot.addWidget(bar)

    bar.start()
    bar.set_phase("downloading_model")

    assert bar.progress.minimum() == 0
    assert bar.progress.maximum() == 0
    assert "模型" in bar.label.text()
