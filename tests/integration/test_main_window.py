from pathlib import Path

from dataclasses import replace
import time

from PySide6.QtCore import QMimeData, QObject, QPoint, QPointF, QUrl, Signal, Qt
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QMessageBox,
    QPushButton,
    QStyle,
    QStyleOptionComboBox,
)

from shadowing_player.ui.main_window import MainWindow, _format_time
from shadowing_player.ui import strings
from shadowing_player.ui.sentence_progress_bar import SentenceProgressBar
from shadowing_player.subtitles.models import Sentence, SubtitleSource
from shadowing_player.playback.session_controller import PlaybackMode, SessionPhase
from shadowing_player.review.review_controller import ReviewItem
from shadowing_player.shortcut_catalog import default_shortcuts
from shadowing_player.storage.progress_store import RecentVideo, VideoProgress
from shadowing_player.transcription.service import TranscriptionCancelled


class FakeBackend(QObject):
    pause_changed = Signal(bool)
    file_loaded = Signal(str)
    position_changed = Signal(float)
    duration_changed = Signal(float)
    error = Signal(str)

    def __init__(self, window_id: int) -> None:
        super().__init__()
        self.window_id = window_id
        self.opened: list[str] = []
        self.toggle_count = 0
        self.speeds: list[float] = []
        self.seeks: list[int] = []
        self.play_count = 0
        self.pause_count = 0
        self.closed = False
        self.duration_ms = 60_000
        self.position_ms = 0
        self.is_paused = False

    def open_file(self, path: str) -> None:
        self.opened.append(path)
        self.is_paused = False

    def toggle_pause(self) -> None:
        self.toggle_count += 1

    def play(self) -> None:
        self.play_count += 1
        self.is_paused = False

    def pause(self) -> None:
        self.pause_count += 1
        self.is_paused = True

    def seek_ms(self, position_ms: int) -> None:
        self.seeks.append(position_ms)

    def set_speed(self, speed: float) -> None:
        self.speeds.append(speed)

    def audio_filters(self) -> list[str]:
        return ["scaletempo2"]

    def shutdown(self) -> None:
        self.closed = True


class FakeSubtitleService:
    def __init__(self, source: SubtitleSource, sentences: list[Sentence]) -> None:
        self.source = source
        self.sentences = sentences
        self.discovered: list[Path] = []

    def discover(self, path: Path) -> list[SubtitleSource]:
        self.discovered.append(path)
        return [self.source]

    def choose_default(self, sources: list[SubtitleSource]) -> SubtitleSource:
        return sources[0]

    def load_sentences(self, source: SubtitleSource, video_duration_ms=None) -> list[Sentence]:
        return self.sentences


class FakeProgressStore:
    def __init__(self, restored: VideoProgress | None = None) -> None:
        self.restored = restored
        self.saved: list[tuple] = []
        self.opened: list[Path] = []
        self.recent: list[RecentVideo] = []
        self.closed = False

    def load(self, path: Path) -> VideoProgress | None:
        return self.restored

    def save(self, *args, **kwargs) -> None:
        self.saved.append((args, kwargs))

    def mark_opened(self, path: Path) -> None:
        self.opened.append(path)

    def list_recent(self, limit: int = 8) -> list[RecentVideo]:
        return self.recent[:limit]

    def close(self) -> None:
        self.closed = True


class FakeSentenceRepository:
    def __init__(self) -> None:
        self.sentences: list[Sentence] = []
        self.starred: list[tuple[int | None, bool]] = []
        self.closed = False

    def replace_source_sentences(self, _path, _source_key, sentences):
        self.sentences = [
            replace(item, id=index + 1, video_id=1)
            for index, item in enumerate(sentences)
        ]
        return self.sentences

    def set_starred(self, sentence_id, starred):
        self.starred.append((sentence_id, starred))

    def load_sentences(self, _path):
        return self.sentences

    def list_starred(self):
        return []

    def close(self):
        self.closed = True


def test_window_uses_simplified_chinese_and_default_speed(qtbot, tmp_path: Path) -> None:
    window = MainWindow(
        backend_factory=FakeBackend,
        progress_store=FakeProgressStore(),
        settings_path=tmp_path / "settings.json",
    )
    qtbot.addWidget(window)

    assert window.open_button.text() == strings.OPEN_VIDEO
    assert window.play_button.text() == strings.PLAY
    assert window.speed_combo.currentData() == 1.0
    assert window.status_label.text() == strings.READY
    assert ".mp4" in strings.FILE_DIALOG_FILTER


def test_window_uses_portable_transcription_cache_with_legacy_fallback(
    qtbot, tmp_path: Path, monkeypatch
) -> None:
    portable_cache = tmp_path / "portable" / "cache" / "transcriptions"
    monkeypatch.setattr(
        "shadowing_player.ui.main_window.transcription_cache_dir",
        lambda: portable_cache,
    )
    window = MainWindow(
        backend_factory=FakeBackend,
        progress_store=FakeProgressStore(),
        settings_path=tmp_path / "user-data" / "settings.json",
    )
    qtbot.addWidget(window)

    assert window._transcription_service.cache_dir == portable_cache
    assert window._transcription_service.fallback_cache_dirs == (
        tmp_path / "user-data" / "cache",
    )


def test_compact_dark_layout_keeps_all_existing_controls(
    qtbot, tmp_path: Path
) -> None:
    window = MainWindow(
        backend_factory=FakeBackend,
        progress_store=FakeProgressStore(),
        settings_path=tmp_path / "settings.json",
    )
    qtbot.addWidget(window)

    assert window.objectName() == "mainWindow"
    assert window.play_button.objectName() == "primaryPlayButton"
    assert window.sentence_panel.objectName() == "sentencePanel"
    assert "#101419" in window.styleSheet()
    for widget in (
        window.previous_button,
        window.repeat_button,
        window.play_button,
        window.next_button,
        window.merge_button,
        window.split_button,
        window.review_button,
        window.subtitle_combo,
        window.subtitle_mode_combo,
        window.mode_combo,
        window.plays_combo,
        window.speed_combo,
        window.blank_combo,
        window.loop_combo,
        window.auto_advance_check,
    ):
        assert window.centralWidget().isAncestorOf(widget)


def test_every_shortcut_has_a_permanent_visible_control(
    qtbot, tmp_path: Path
) -> None:
    window = MainWindow(
        backend_factory=FakeBackend,
        progress_store=FakeProgressStore(),
        settings_path=tmp_path / "settings.json",
    )
    qtbot.addWidget(window)

    assert set(window.permanent_action_controls) == set(default_shortcuts())
    assert all(
        window.centralWidget().isAncestorOf(control)
        for control in window.permanent_action_controls.values()
    )
    assert all(
        shortcut in window.permanent_action_controls[name].toolTip()
        for name, shortcut in default_shortcuts().items()
    )


def test_persistent_action_buttons_call_existing_behaviors(
    qtbot, tmp_path: Path
) -> None:
    repository = FakeSentenceRepository()
    window = MainWindow(
        backend_factory=FakeBackend,
        progress_store=FakeProgressStore(),
        sentence_repository=repository,
        settings_path=tmp_path / "settings.json",
    )
    qtbot.addWidget(window)
    window._apply_sentences([Sentence(0, 1_000, 2_000, "Hello", id=7)])
    window.controller.select_sentence(0, autoplay=False)

    qtbot.mouseClick(window.star_button, Qt.MouseButton.LeftButton)
    qtbot.mouseClick(window.speed_down_button, Qt.MouseButton.LeftButton)

    assert window.sentence_model.sentences[0].starred is True
    assert repository.starred == [(7, True)]
    assert window.speed_combo.currentData() == 0.95


def test_persistent_action_states_follow_external_changes(
    qtbot, tmp_path: Path
) -> None:
    window = MainWindow(
        backend_factory=FakeBackend,
        progress_store=FakeProgressStore(),
        settings_path=tmp_path / "settings.json",
    )
    qtbot.addWidget(window)
    window._apply_sentences([Sentence(0, 1_000, 2_000, "Hello")])
    window.controller.select_sentence(0, autoplay=False)

    window.mode_combo.setCurrentIndex(
        window.mode_combo.findData(PlaybackMode.SINGLE_LOOP)
    )
    window.subtitle_mode_combo.setCurrentIndex(
        window.subtitle_mode_combo.findData("hidden")
    )
    window.backend.pause_changed.emit(False)

    assert window.single_loop_button.isChecked()
    assert window.mode_action_button.text() == "模式 · 精听"
    assert window.subtitle_action_button.text() == "字幕 · 隐藏"
    assert not window.subtitle_action_button.isChecked()
    assert window.play_button.text() == "暂停"


def test_play_button_explains_running_and_paused_blank_time(
    qtbot, tmp_path: Path
) -> None:
    window = MainWindow(
        backend_factory=FakeBackend,
        progress_store=FakeProgressStore(),
        settings_path=tmp_path / "settings.json",
    )
    qtbot.addWidget(window)
    window._apply_sentences([Sentence(0, 1_000, 2_000, "Hello")])
    window.controller._set_phase(SessionPhase.BLANK)

    assert window.play_button.text() == "暂停留白"

    window.controller.toggle_pause()

    assert window.play_button.text() == "继续留白"


def test_review_mode_and_favorite_buttons_follow_the_review_sentence(
    qtbot, tmp_path: Path
) -> None:
    movie = tmp_path / "review.mp4"
    movie.write_bytes(b"video")
    repository = FakeSentenceRepository()
    window = MainWindow(
        backend_factory=FakeBackend,
        progress_store=FakeProgressStore(),
        sentence_repository=repository,
        settings_path=tmp_path / "settings.json",
    )
    qtbot.addWidget(window)
    window._apply_sentences(
        [Sentence(0, 1_000, 2_000, "Original", id=10)]
    )
    window.mode_combo.setCurrentIndex(
        window.mode_combo.findData(PlaybackMode.SINGLE_LOOP)
    )
    review_sentence = Sentence(
        8, 3_000, 4_000, "Review", starred=True, id=20
    )
    window._review_in_progress = True
    window.review_controller._current_video = movie.resolve()

    window.review_controller.start([ReviewItem(movie, review_sentence)])

    assert window.controller.mode is PlaybackMode.SENTENCE_PRACTICE
    assert window.mode_combo.currentData() == PlaybackMode.SENTENCE_PRACTICE
    assert window.mode_action_button.text() == "模式 · 跟读"
    assert not window.single_loop_button.isChecked()
    assert window.star_button.isChecked()

    qtbot.mouseClick(window.star_button, Qt.MouseButton.LeftButton)

    assert repository.starred[-1] == (20, False)
    assert window.controller.current_sentence.starred is False
    assert window.sentence_model.sentences[0].id == 10
    assert window.sentence_model.sentences[0].starred is False


def test_sentence_transport_buttons_are_disabled_without_sentences(
    qtbot, tmp_path: Path
) -> None:
    window = MainWindow(
        backend_factory=FakeBackend,
        progress_store=FakeProgressStore(),
        settings_path=tmp_path / "settings.json",
    )
    qtbot.addWidget(window)

    assert not window.previous_button.isEnabled()
    assert not window.repeat_button.isEnabled()
    assert not window.next_button.isEnabled()

    window._apply_sentences([Sentence(0, 1_000, 2_000, "Hello")])

    assert window.previous_button.isEnabled()
    assert window.repeat_button.isEnabled()
    assert window.next_button.isEnabled()


def test_auto_advance_label_has_enough_width_and_is_not_clipped(
    qtbot, tmp_path: Path
) -> None:
    window = MainWindow(
        backend_factory=FakeBackend,
        progress_store=FakeProgressStore(),
        settings_path=tmp_path / "settings.json",
    )
    qtbot.addWidget(window)

    assert window.auto_advance_check.width() >= (
        window.auto_advance_check.sizeHint().width() + 8
    )


def test_sentence_progress_bar_uses_compact_height(qtbot) -> None:
    progress = SentenceProgressBar()
    qtbot.addWidget(progress)

    assert progress.height() == 12


def test_window_accepts_one_local_video_drop(qtbot, tmp_path: Path) -> None:
    movie = tmp_path / "episode.mp4"
    movie.touch()
    window = MainWindow(
        backend_factory=FakeBackend,
        progress_store=FakeProgressStore(),
        settings_path=tmp_path / "settings.json",
    )
    qtbot.addWidget(window)
    opened: list[Path] = []
    window.open_video = opened.append
    mime_data = QMimeData()
    mime_data.setUrls([QUrl.fromLocalFile(str(movie))])

    drag_event = QDragEnterEvent(
        QPoint(10, 10),
        Qt.DropAction.CopyAction,
        mime_data,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    window.dragEnterEvent(drag_event)
    drop_event = QDropEvent(
        QPointF(10, 10),
        Qt.DropAction.CopyAction,
        mime_data,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    window.dropEvent(drop_event)

    assert window.acceptDrops()
    assert drag_event.isAccepted()
    assert drop_event.isAccepted()
    assert opened == [movie.resolve()]


def test_window_ignores_non_video_drop(qtbot, tmp_path: Path) -> None:
    document = tmp_path / "notes.txt"
    document.touch()
    window = MainWindow(
        backend_factory=FakeBackend,
        progress_store=FakeProgressStore(),
        settings_path=tmp_path / "settings.json",
    )
    qtbot.addWidget(window)
    opened: list[Path] = []
    window.open_video = opened.append
    mime_data = QMimeData()
    mime_data.setUrls([QUrl.fromLocalFile(str(document))])
    drag_event = QDragEnterEvent(
        QPoint(10, 10),
        Qt.DropAction.CopyAction,
        mime_data,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )

    window.dragEnterEvent(drag_event)

    assert not drag_event.isAccepted()
    assert opened == []


def test_time_formatter_handles_minutes_and_hours() -> None:
    assert _format_time(0) == "00:00"
    assert _format_time(65_000) == "01:05"
    assert _format_time(3_665_000) == "1:01:05"


def test_window_updates_time_and_sentence_counter_labels(
    qtbot, tmp_path: Path
) -> None:
    window = MainWindow(
        backend_factory=FakeBackend,
        progress_store=FakeProgressStore(),
        settings_path=tmp_path / "settings.json",
    )
    qtbot.addWidget(window)
    sentence = Sentence(0, 4_000, 8_000, "Hello")

    window._duration_changed(65.0)
    window._position_changed(5.0)
    window._apply_sentences([sentence])
    window.controller.select_sentence(0, autoplay=False)

    assert window.position_label.text() == "00:05"
    assert window.duration_label.text() == "01:05"
    assert window.sentence_counter_label.text() == "第 1 / 1 句"


def test_tools_menu_actions_use_current_paths_and_shortcuts(
    qtbot, tmp_path: Path, monkeypatch
) -> None:
    window = MainWindow(
        backend_factory=FakeBackend,
        progress_store=FakeProgressStore(),
        settings_path=tmp_path / "settings.json",
    )
    qtbot.addWidget(window)
    shortcut_path = tmp_path / "Desktop" / "儿童影子跟读播放器.lnk"
    opened_urls: list[QUrl] = []
    monkeypatch.setattr(
        "shadowing_player.ui.main_window.create_desktop_shortcut",
        lambda: shortcut_path,
    )
    monkeypatch.setattr(
        "shadowing_player.ui.main_window.QDesktopServices.openUrl",
        lambda url: opened_urls.append(url) or True,
    )
    monkeypatch.setattr(
        "shadowing_player.ui.main_window.ShortcutDialog.exec",
        lambda _dialog: QDialog.DialogCode.Rejected,
    )

    assert [action.text() for action in window.tools_menu.actions()] == [
        strings.CREATE_DESKTOP_SHORTCUT,
        strings.OPEN_DATA_FOLDER,
        strings.SHORTCUT_HELP,
    ]
    window.create_shortcut_action.trigger()
    window.open_data_action.trigger()
    window.shortcut_help_action.trigger()

    assert str(shortcut_path) in window.status_label.text()
    assert Path(opened_urls[0].toLocalFile()) == tmp_path.resolve()


def test_recent_menu_lists_existing_videos_and_opens_selection(
    qtbot, tmp_path: Path
) -> None:
    first = tmp_path / "first.mp4"
    second = tmp_path / "second.mkv"
    missing = tmp_path / "missing.mp4"
    first.touch()
    second.touch()
    store = FakeProgressStore()
    store.recent = [
        RecentVideo(first, 1_000, "2026-07-23 10:00:03"),
        RecentVideo(missing, 2_000, "2026-07-23 10:00:02"),
        RecentVideo(second, 3_000, "2026-07-23 10:00:01"),
    ]
    window = MainWindow(
        backend_factory=FakeBackend,
        progress_store=store,
        settings_path=tmp_path / "settings.json",
    )
    qtbot.addWidget(window)
    opened: list[Path] = []
    window.open_video = opened.append

    window.recent_menu.aboutToShow.emit()
    actions = [
        action for action in window.recent_menu.actions() if action.isEnabled()
    ]

    assert [action.text() for action in actions] == [first.name, second.name]
    assert actions[0].toolTip() == str(first)
    actions[1].trigger()
    assert opened == [second]


def test_persistent_action_rows_fit_the_980_pixel_minimum_width(
    qtbot, tmp_path: Path
) -> None:
    window = MainWindow(
        backend_factory=FakeBackend,
        progress_store=FakeProgressStore(),
        settings_path=tmp_path / "settings.json",
    )
    qtbot.addWidget(window)
    window.resize(980, 680)
    window.show()
    qtbot.wait(10)

    rows = [
        [
            window.previous_button,
            window.repeat_button,
            window.play_button,
            window.next_button,
            window.mode_action_button,
            window.single_loop_button,
            window.subtitle_action_button,
            window.star_button,
            window.fullscreen_button,
            window.shortcut_button,
        ],
        [
            window.mode_combo,
            window.plays_combo,
            window.speed_down_button,
            window.speed_combo,
            window.speed_up_button,
            window.blank_combo,
            window.loop_combo,
            window.auto_advance_check,
        ],
    ]
    for controls in rows:
        rectangles = [
            (widget.mapTo(window, widget.rect().topLeft()).x(), widget.width())
            for widget in controls
        ]
        assert all(
            left + width <= next_left
            for (left, width), (next_left, _next_width) in zip(
                rectangles, rectangles[1:]
            )
        )
        assert rectangles[-1][0] + rectangles[-1][1] <= window.width()
    assert window.width() == 980


def test_compact_combo_boxes_show_their_complete_current_text(
    qtbot, tmp_path: Path
) -> None:
    window = MainWindow(
        backend_factory=FakeBackend,
        progress_store=FakeProgressStore(),
        settings_path=tmp_path / "settings.json",
    )
    qtbot.addWidget(window)
    window.show()

    for combo in (
        window.mode_combo,
        window.plays_combo,
        window.speed_combo,
        window.blank_combo,
        window.loop_combo,
    ):
        for index in range(combo.count()):
            combo.setCurrentIndex(index)
            option = QStyleOptionComboBox()
            combo.initStyleOption(option)
            edit_rect = combo.style().subControlRect(
                QStyle.ComplexControl.CC_ComboBox,
                option,
                QStyle.SubControl.SC_ComboBoxEditField,
                combo,
            )
            assert (
                combo.fontMetrics().horizontalAdvance(combo.currentText())
                <= edit_rect.width()
            )


def test_bilingual_sentence_rows_expand_to_show_both_lines(
    qtbot, tmp_path: Path
) -> None:
    window = MainWindow(
        backend_factory=FakeBackend,
        progress_store=FakeProgressStore(),
        settings_path=tmp_path / "settings.json",
    )
    qtbot.addWidget(window)
    window.subtitle_mode_combo.setCurrentIndex(
        window.subtitle_mode_combo.findData("bilingual")
    )

    window._apply_sentences([Sentence(0, 1_000, 2_000, "Hello", "你好")])

    assert window.sentence_list.rowHeight(0) >= 44


def test_window_opens_selected_mkv_and_controls_backend(qtbot, monkeypatch, tmp_path: Path) -> None:
    movie = tmp_path / "sample.mkv"
    movie.touch()
    monkeypatch.setattr(
        QFileDialog,
        "getOpenFileName",
        lambda *args, **kwargs: (str(movie), "MKV 视频 (*.mkv)"),
    )
    window = MainWindow(
        backend_factory=FakeBackend,
        progress_store=FakeProgressStore(),
        settings_path=tmp_path / "settings.json",
    )
    qtbot.addWidget(window)
    backend = window.backend

    window.open_button.click()
    window.play_button.click()
    window.speed_combo.setCurrentIndex(1)

    assert backend.opened == [str(movie)]
    assert backend.pause_count >= 1
    assert backend.speeds[-1] == 0.95


def test_window_opens_mp4_and_populates_sentence_list(qtbot, monkeypatch, tmp_path: Path) -> None:
    movie = tmp_path / "episode.mp4"
    movie.touch()
    subtitle = tmp_path / "episode.srt"
    subtitle.touch()
    source = SubtitleSource.external(subtitle)
    service = FakeSubtitleService(
        source,
        [Sentence(0, 1_000, 2_000, "Hello"), Sentence(1, 3_000, 4_000, "Again")],
    )
    store = FakeProgressStore()
    monkeypatch.setattr(
        QFileDialog,
        "getOpenFileName",
        lambda *args, **kwargs: (str(movie), strings.FILE_DIALOG_FILTER),
    )
    window = MainWindow(
        backend_factory=FakeBackend,
        subtitle_service=service,
        progress_store=store,
        settings_path=tmp_path / "settings.json",
    )
    qtbot.addWidget(window)

    window.open_button.click()

    assert window.backend.opened == [str(movie)]
    assert service.discovered == [movie]
    assert window.sentence_model.rowCount() == 2
    assert window.subtitle_combo.count() == 1
    assert window.subtitle_label.text() == "Hello"
    assert store.opened == [movie.resolve()]


def test_clicking_sentence_text_seeks_to_that_sentence(
    qtbot, tmp_path: Path
) -> None:
    movie = tmp_path / "episode.mp4"
    movie.touch()
    subtitle = tmp_path / "episode.srt"
    subtitle.touch()
    service = FakeSubtitleService(
        SubtitleSource.external(subtitle),
        [
            Sentence(0, 1_000, 2_000, "Hello"),
            Sentence(1, 3_000, 4_000, "Again"),
        ],
    )
    window = MainWindow(
        backend_factory=FakeBackend,
        subtitle_service=service,
        progress_store=FakeProgressStore(),
        sentence_repository=FakeSentenceRepository(),
        settings_path=tmp_path / "settings.json",
    )
    qtbot.addWidget(window)
    window.show()
    window.open_video(movie)
    index = window.sentence_model.index(1, 0)

    qtbot.mouseClick(
        window.sentence_list.viewport(),
        Qt.MouseButton.LeftButton,
        pos=window.sentence_list.visualRect(index).center(),
    )

    assert window.backend.seeks[-1] == 2_750
    assert window.controller.current_index == 1


def test_single_left_press_replays_current_sentence(
    qtbot, tmp_path: Path
) -> None:
    window = MainWindow(
        backend_factory=FakeBackend,
        progress_store=FakeProgressStore(),
        settings_path=tmp_path / "settings.json",
    )
    qtbot.addWidget(window)
    window._apply_sentences(
        [
            Sentence(0, 1_000, 2_000, "First"),
            Sentence(1, 3_000, 4_000, "Second"),
        ]
    )
    window.controller.select_sentence(1, autoplay=False)
    window.backend.seeks.clear()
    window._last_left_press = 0.0

    window._left_pressed()

    assert window.backend.seeks == [2_750]
    assert window.backend.play_count == 1


def test_star_column_is_right_aligned_and_click_only_toggles_favorite(
    qtbot, tmp_path: Path
) -> None:
    repository = FakeSentenceRepository()
    window = MainWindow(
        backend_factory=FakeBackend,
        progress_store=FakeProgressStore(),
        sentence_repository=repository,
        settings_path=tmp_path / "settings.json",
    )
    qtbot.addWidget(window)
    window.show()
    window._apply_sentences([Sentence(0, 1_000, 2_000, "Hello", id=7)])
    star_index = window.sentence_model.index(0, 1)

    qtbot.mouseClick(
        window.sentence_list.viewport(),
        Qt.MouseButton.LeftButton,
        pos=window.sentence_list.visualRect(star_index).center(),
    )

    assert window.sentence_model.data(
        star_index, Qt.ItemDataRole.DisplayRole
    ) == "★"
    assert repository.starred == [(7, True)]
    assert window.backend.seeks == []
    assert window.sentence_list.columnWidth(1) <= 48
    assert window.sentence_list.itemDelegate().__class__.__name__ == (
        "SentenceItemDelegate"
    )


def test_playback_row_does_not_replace_merge_selection(
    qtbot, tmp_path: Path
) -> None:
    window = MainWindow(
        backend_factory=FakeBackend,
        progress_store=FakeProgressStore(),
        settings_path=tmp_path / "settings.json",
    )
    qtbot.addWidget(window)
    sentences = [
        Sentence(0, 1_000, 2_000, "First"),
        Sentence(1, 3_000, 4_000, "Second"),
    ]
    window._apply_sentences(sentences)
    selection = window.sentence_list.selectionModel()
    selection.select(
        window.sentence_model.index(0, 0),
        selection.SelectionFlag.Select | selection.SelectionFlag.Rows,
    )
    selection.select(
        window.sentence_model.index(1, 0),
        selection.SelectionFlag.Select | selection.SelectionFlag.Rows,
    )

    window._current_sentence_changed(1, sentences[1])

    assert window.sentence_model.data(
        window.sentence_model.index(1, 0),
        window.sentence_model.CurrentRole,
    ) is True
    assert {index.row() for index in selection.selectedRows()} == {0, 1}


def test_window_restores_progress_paused_and_saves_on_close(qtbot, monkeypatch, tmp_path: Path) -> None:
    movie = tmp_path / "episode.mp4"
    movie.write_bytes(b"video")
    subtitle = tmp_path / "episode.srt"
    subtitle.touch()
    source = SubtitleSource.external(subtitle)
    service = FakeSubtitleService(
        source,
        [Sentence(0, 1_000, 2_000, "Hello"), Sentence(1, 3_000, 4_000, "Again")],
    )
    store = FakeProgressStore(
        VideoProgress(3_200, 0.75, PlaybackMode.SHADOWING, source.identifier)
    )
    monkeypatch.setattr(
        QFileDialog,
        "getOpenFileName",
        lambda *args, **kwargs: (str(movie), strings.FILE_DIALOG_FILTER),
    )
    window = MainWindow(
        backend_factory=FakeBackend,
        subtitle_service=service,
        progress_store=store,
        settings_path=tmp_path / "settings.json",
    )
    qtbot.addWidget(window)

    window.open_button.click()

    assert window.speed_combo.currentData() == 0.75
    assert window.current_mode is PlaybackMode.SHADOWING
    assert window.backend.seeks[-1] == 3_200
    assert window.backend.pause_count >= 1

    window.backend.position_ms = 4_200
    window.close()

    assert store.saved
    assert store.saved[-1][1]["position_ms"] == 4_200
    assert store.closed is True


def test_window_installs_all_visible_second_version_shortcuts(qtbot, tmp_path: Path) -> None:
    window = MainWindow(
        backend_factory=FakeBackend,
        progress_store=FakeProgressStore(),
        settings_path=tmp_path / "settings.json",
    )
    qtbot.addWidget(window)

    sequences = {shortcut.key().toString() for shortcut in window._shortcuts}

    assert {
        "Ctrl+O",
        "Ctrl+H",
        "Space",
        "Left",
        "Ctrl+Left",
        "Right",
        "Up",
        "Down",
        "L",
        "M",
        "Tab",
        "S",
        "R",
        "F",
        "F1",
    } <= sequences


def test_switching_to_sentence_practice_starts_current_sentence(qtbot, monkeypatch, tmp_path: Path) -> None:
    movie = tmp_path / "episode.mp4"
    movie.touch()
    subtitle = tmp_path / "episode.srt"
    subtitle.touch()
    service = FakeSubtitleService(
        SubtitleSource.external(subtitle),
        [Sentence(0, 1_000, 2_000, "Hello")],
    )
    monkeypatch.setattr(
        QFileDialog,
        "getOpenFileName",
        lambda *args, **kwargs: (str(movie), strings.FILE_DIALOG_FILTER),
    )
    window = MainWindow(
        backend_factory=FakeBackend,
        subtitle_service=service,
        progress_store=FakeProgressStore(),
        settings_path=tmp_path / "settings.json",
    )
    qtbot.addWidget(window)
    window.open_button.click()

    window.mode_combo.setCurrentIndex(1)

    assert window.current_mode is PlaybackMode.SENTENCE_PRACTICE
    assert window.backend.seeks[-1] == 750


def test_window_displays_bilingual_subtitles_and_persists_star(
    qtbot, monkeypatch, tmp_path: Path
) -> None:
    movie = tmp_path / "episode.mp4"
    movie.touch()
    subtitle = tmp_path / "episode.srt"
    subtitle.touch()
    service = FakeSubtitleService(
        SubtitleSource.external(subtitle),
        [Sentence(0, 1_000, 2_000, "Hello", text_zh="你好")],
    )
    repository = FakeSentenceRepository()
    monkeypatch.setattr(
        QFileDialog,
        "getOpenFileName",
        lambda *args, **kwargs: (str(movie), strings.FILE_DIALOG_FILTER),
    )
    window = MainWindow(
        backend_factory=FakeBackend,
        subtitle_service=service,
        progress_store=FakeProgressStore(),
        sentence_repository=repository,
        settings_path=tmp_path / "settings.json",
    )
    qtbot.addWidget(window)

    window.open_button.click()

    assert window.subtitle_mode_combo.currentData() == "bilingual"
    assert window.subtitle_label.text() == "Hello\n你好"
    window.sentence_model.toggle_star(0)
    assert repository.starred == [(1, True)]

    window.subtitle_mode_combo.setCurrentIndex(
        window.subtitle_mode_combo.findData("english")
    )
    assert window.subtitle_label.text() == "Hello"


class NoSubtitleService:
    def discover(self, _path):
        return []

    def choose_default(self, _sources):
        return None

    def load_sentences(self, source, video_duration_ms=None):
        from shadowing_player.subtitles.subtitle_service import SubtitleService

        return SubtitleService(source.path.parent / "embedded").load_sentences(
            source, video_duration_ms
        )


class FastTranscriptionService:
    def __init__(self, cache: Path) -> None:
        self.cache = cache
        self.calls: list[Path] = []

    def cache_path_for(self, _video):
        return self.cache

    def transcribe(self, video, on_progress, on_phase, is_cancelled):
        self.calls.append(video)
        on_phase("transcribing")
        on_progress(50)
        self.cache.parent.mkdir(parents=True, exist_ok=True)
        self.cache.write_text(
            "1\n00:00:00,000 --> 00:00:02,000\nGenerated sentence\n",
            encoding="utf-8",
        )
        on_progress(100)
        return self.cache


class ChineseOnlySubtitleService:
    def __init__(self, source: SubtitleSource) -> None:
        self.source = source
        self.bilingual_calls: list[tuple[SubtitleSource, SubtitleSource | None]] = []
        self.primary_only_calls: list[SubtitleSource] = []

    def discover(self, _path):
        return [self.source]

    def choose_default(self, _sources):
        return self.source

    def choose_language_sources(self, _sources):
        return None, self.source

    def load_sentences(self, source, video_duration_ms=None):
        self.primary_only_calls.append(source)
        return [Sentence(0, 0, 2_000, "只有中文")]

    def load_bilingual_sentences(
        self, english_source, chinese_source, video_duration_ms=None
    ):
        self.bilingual_calls.append((english_source, chinese_source))
        return [Sentence(0, 0, 2_000, "Generated English", "现有中文")]


def test_chinese_only_subtitle_automatically_transcribes_english_and_aligns(
    qtbot, monkeypatch, tmp_path: Path
) -> None:
    movie = tmp_path / "episode.mp4"
    movie.write_bytes(b"video")
    chinese = tmp_path / "episode.srt"
    chinese.write_text(
        "1\n00:00:00,000 --> 00:00:02,000\n现有中文\n",
        encoding="utf-8",
    )
    source = SubtitleSource.external(chinese)
    service = ChineseOnlySubtitleService(source)
    transcription = FastTranscriptionService(tmp_path / "cache" / "hash.srt")
    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("Chinese-only input should start English transcription automatically")
        ),
    )
    window = MainWindow(
        backend_factory=FakeBackend,
        subtitle_service=service,
        progress_store=FakeProgressStore(),
        sentence_repository=FakeSentenceRepository(),
        transcription_service=transcription,
        settings_path=tmp_path / "settings.json",
    )
    qtbot.addWidget(window)

    window.open_video(movie)
    qtbot.waitUntil(lambda: bool(service.bilingual_calls), timeout=3_000)

    english_source, chinese_source = service.bilingual_calls[-1]
    assert english_source.path == transcription.cache
    assert chinese_source == source
    assert service.primary_only_calls == []
    assert window.subtitle_label.text() == "Generated English\n现有中文"


def test_chinese_only_subtitle_reuses_cached_english_without_transcribing(
    qtbot, monkeypatch, tmp_path: Path
) -> None:
    movie = tmp_path / "episode.mp4"
    movie.write_bytes(b"video")
    chinese = tmp_path / "episode.zh.srt"
    chinese.write_text(
        "1\n00:00:00,000 --> 00:00:02,000\n现有中文\n",
        encoding="utf-8",
    )
    source = SubtitleSource.external(chinese)
    service = ChineseOnlySubtitleService(source)
    cache = tmp_path / "cache" / "hash.srt"
    cache.parent.mkdir()
    cache.write_text(
        "1\n00:00:00,000 --> 00:00:02,000\nCached English\n",
        encoding="utf-8",
    )
    transcription = FastTranscriptionService(cache)
    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("cached English should avoid prompting")
        ),
    )
    window = MainWindow(
        backend_factory=FakeBackend,
        subtitle_service=service,
        progress_store=FakeProgressStore(),
        sentence_repository=FakeSentenceRepository(),
        transcription_service=transcription,
        settings_path=tmp_path / "settings.json",
    )
    qtbot.addWidget(window)

    window.open_video(movie)

    assert transcription.calls == []
    assert service.bilingual_calls[-1][0].path == cache
    assert service.bilingual_calls[-1][1] == source
    assert window.subtitle_label.text() == "Generated English\n现有中文"


def test_no_subtitle_video_transcribes_in_background_and_populates_list(
    qtbot, monkeypatch, tmp_path: Path
) -> None:
    movie = tmp_path / "silent.mp4"
    movie.write_bytes(b"video")
    transcription = FastTranscriptionService(tmp_path / "cache" / "hash.srt")
    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda *args, **kwargs: QMessageBox.StandardButton.Yes,
    )
    window = MainWindow(
        backend_factory=FakeBackend,
        subtitle_service=NoSubtitleService(),
        progress_store=FakeProgressStore(),
        sentence_repository=FakeSentenceRepository(),
        transcription_service=transcription,
        settings_path=tmp_path / "settings.json",
    )
    qtbot.addWidget(window)

    window.open_video(movie)
    assert window.open_button.isEnabled()
    qtbot.waitUntil(lambda: window.sentence_model.rowCount() == 1, timeout=3_000)

    assert transcription.calls == [movie.resolve()]
    assert window.sentence_model.data(
        window.sentence_model.index(0, 0), Qt.ItemDataRole.DisplayRole
    ).endswith("Generated sentence")


class CancellableTranscriptionService:
    def __init__(self, cache: Path) -> None:
        self.cache = cache
        self.started = False

    def cache_path_for(self, _video):
        return self.cache

    def transcribe(self, _video, on_progress, on_phase, is_cancelled):
        self.started = True
        on_phase("transcribing")
        while not is_cancelled():
            on_progress(10)
            time.sleep(0.01)
        raise TranscriptionCancelled()


class LateCompletionTranscriptionService:
    def __init__(self, cache: Path) -> None:
        import threading

        self.cache = cache
        self.started = threading.Event()
        self.release = threading.Event()

    def cache_path_for(self, _video):
        return self.cache

    def transcribe(self, _video, on_progress, on_phase, is_cancelled):
        on_phase("transcribing")
        self.started.set()
        self.release.wait(3)
        self.cache.parent.mkdir(parents=True, exist_ok=True)
        self.cache.write_text(
            "1\n00:00:00,000 --> 00:00:01,000\nStale sentence\n",
            encoding="utf-8",
        )
        return self.cache


class SerializedTranscriptionService:
    def __init__(self, cache_dir: Path) -> None:
        import threading

        self.cache_dir = cache_dir
        self.calls: list[Path] = []
        self.first_started = threading.Event()
        self.release_first = threading.Event()

    def cache_path_for(self, video):
        return self.cache_dir / f"{video.stem}.srt"

    def transcribe(self, video, on_progress, on_phase, is_cancelled):
        self.calls.append(video)
        if len(self.calls) == 1:
            self.first_started.set()
            self.release_first.wait(3)
        output = self.cache_path_for(video)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            "1\n00:00:00,000 --> 00:00:01,000\nGenerated\n",
            encoding="utf-8",
        )
        return output


class FirstVideoHasNoSubtitleService(FakeSubtitleService):
    def __init__(
        self,
        first_video: Path,
        source: SubtitleSource,
        sentences: list[Sentence],
    ) -> None:
        super().__init__(source, sentences)
        self.first_video = first_video.resolve()

    def discover(self, path: Path) -> list[SubtitleSource]:
        if path.resolve() == self.first_video:
            return []
        return [self.source]


def test_transcription_status_is_embedded_non_blocking_and_can_cancel(
    qtbot, monkeypatch, tmp_path: Path
) -> None:
    movie = tmp_path / "silent.mp4"
    movie.write_bytes(b"video")
    service = CancellableTranscriptionService(tmp_path / "cache" / "hash.srt")
    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda *args, **kwargs: QMessageBox.StandardButton.Yes,
    )
    window = MainWindow(
        backend_factory=FakeBackend,
        subtitle_service=NoSubtitleService(),
        progress_store=FakeProgressStore(),
        sentence_repository=FakeSentenceRepository(),
        transcription_service=service,
        settings_path=tmp_path / "settings.json",
    )
    qtbot.addWidget(window)

    window.open_video(movie)
    qtbot.waitUntil(lambda: service.started, timeout=1_000)
    assert window.backend.pause_count == 0
    assert not window.transcription_status.isHidden()
    assert window.centralWidget().isAncestorOf(window.transcription_status)
    window.speed_combo.setCurrentIndex(1)
    assert window.speed_combo.currentData() == 0.95
    qtbot.mouseClick(
        window.transcription_status.cancel_button, Qt.MouseButton.LeftButton
    )
    qtbot.waitUntil(
        lambda: window.status_label.text() == strings.TRANSCRIPTION_CANCELLED,
        timeout=3_000,
    )
    assert window.transcription_status.isHidden()


def test_late_transcription_from_previous_video_cannot_replace_new_sentences(
    qtbot, monkeypatch, tmp_path: Path
) -> None:
    first = tmp_path / "first.mp4"
    second = tmp_path / "second.mp4"
    first.write_bytes(b"first")
    second.write_bytes(b"second")
    subtitle = tmp_path / "second.srt"
    subtitle.write_text("", encoding="utf-8")
    subtitle_service = FirstVideoHasNoSubtitleService(
        first,
        SubtitleSource.external(subtitle),
        [Sentence(0, 2_000, 3_000, "Current video sentence")],
    )
    transcription = LateCompletionTranscriptionService(
        tmp_path / "cache" / "first.srt"
    )
    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda *args, **kwargs: QMessageBox.StandardButton.Yes,
    )
    window = MainWindow(
        backend_factory=FakeBackend,
        subtitle_service=subtitle_service,
        progress_store=FakeProgressStore(),
        sentence_repository=FakeSentenceRepository(),
        transcription_service=transcription,
        settings_path=tmp_path / "settings.json",
    )
    qtbot.addWidget(window)

    window.open_video(first)
    assert transcription.started.wait(1)
    window.open_video(second)
    transcription.release.set()
    qtbot.waitUntil(lambda: not window._transcription_jobs, timeout=3_000)

    assert window._current_video == second.resolve()
    assert window.sentence_model.sentences[0].text == "Current video sentence"


def test_replacement_transcriptions_are_serialized(
    qtbot, monkeypatch, tmp_path: Path
) -> None:
    first = tmp_path / "first.mp4"
    second = tmp_path / "second.mp4"
    first.write_bytes(b"first")
    second.write_bytes(b"second")
    service = SerializedTranscriptionService(tmp_path / "cache")
    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda *args, **kwargs: QMessageBox.StandardButton.Yes,
    )
    window = MainWindow(
        backend_factory=FakeBackend,
        subtitle_service=NoSubtitleService(),
        progress_store=FakeProgressStore(),
        sentence_repository=FakeSentenceRepository(),
        transcription_service=service,
        settings_path=tmp_path / "settings.json",
    )
    qtbot.addWidget(window)

    window.open_video(first)
    assert service.first_started.wait(1)
    window.open_video(second)

    assert service.calls == [first.resolve()]
    service.release_first.set()
    qtbot.waitUntil(lambda: len(service.calls) == 2, timeout=3_000)
    assert service.calls == [first.resolve(), second.resolve()]


def test_stale_queued_transcription_cannot_start_after_video_changes(
    qtbot, tmp_path: Path
) -> None:
    old_video = tmp_path / "old.mp4"
    new_video = tmp_path / "new.mp4"
    old_video.write_bytes(b"old")
    new_video.write_bytes(b"new")
    service = SerializedTranscriptionService(tmp_path / "cache")
    window = MainWindow(
        backend_factory=FakeBackend,
        subtitle_service=NoSubtitleService(),
        progress_store=FakeProgressStore(),
        sentence_repository=FakeSentenceRepository(),
        transcription_service=service,
        settings_path=tmp_path / "settings.json",
    )
    qtbot.addWidget(window)
    window._current_video = new_video.resolve()

    window._start_transcription(old_video, None)
    qtbot.wait(20)

    assert window._transcription_jobs == []
    assert service.calls == []


def test_close_waits_for_background_worker_before_destroying_services(
    qtbot, monkeypatch, tmp_path: Path
) -> None:
    movie = tmp_path / "silent.mp4"
    movie.write_bytes(b"video")
    transcription = LateCompletionTranscriptionService(
        tmp_path / "cache" / "late.srt"
    )
    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda *args, **kwargs: QMessageBox.StandardButton.Yes,
    )
    window = MainWindow(
        backend_factory=FakeBackend,
        subtitle_service=NoSubtitleService(),
        progress_store=FakeProgressStore(),
        sentence_repository=FakeSentenceRepository(),
        transcription_service=transcription,
        settings_path=tmp_path / "settings.json",
    )
    qtbot.addWidget(window)
    window.show()
    window.open_video(movie)
    assert transcription.started.wait(1)

    window.close()

    assert window.isVisible()
    assert window.backend.closed is False
    assert all(not shortcut.isEnabled() for shortcut in window._shortcuts)
    transcription.release.set()
    qtbot.waitUntil(lambda: window.backend.closed, timeout=3_000)


def test_existing_transcription_cache_loads_without_prompt(
    qtbot, monkeypatch, tmp_path: Path
) -> None:
    movie = tmp_path / "silent.mp4"
    movie.write_bytes(b"video")
    cache = tmp_path / "cache" / "hash.srt"
    cache.parent.mkdir()
    cache.write_text(
        "1\n00:00:00,000 --> 00:00:01,000\nLoaded instantly\n",
        encoding="utf-8",
    )
    service = FastTranscriptionService(cache)
    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("cache should avoid prompt")
        ),
    )
    window = MainWindow(
        backend_factory=FakeBackend,
        subtitle_service=NoSubtitleService(),
        progress_store=FakeProgressStore(),
        sentence_repository=FakeSentenceRepository(),
        transcription_service=service,
        settings_path=tmp_path / "settings.json",
    )
    qtbot.addWidget(window)

    window.open_video(movie)

    assert window.sentence_model.rowCount() == 1
    assert service.calls == []
