from __future__ import annotations

import logging
import os
import sqlite3
import time
from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path

from PySide6.QtCore import QMimeData, QSignalBlocker, QThread, QTimer, Qt, QUrl
from PySide6.QtGui import QCloseEvent, QDesktopServices, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMessageBox,
    QMenu,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from shadowing_player.playback.mpv_backend import MpvBackend
from shadowing_player.playback.session_controller import PlaybackMode, SessionController, SessionPhase
from shadowing_player.runtime.bundle_paths import bundled_model_dir, transcription_cache_dir
from shadowing_player.runtime.windows_shortcut import (
    ShortcutCreationError,
    create_desktop_shortcut,
)
from shadowing_player.shortcut_catalog import shortcut_definitions
from shadowing_player.subtitles.models import Sentence, SubtitleSource
from shadowing_player.subtitles.subtitle_service import SubtitleError, SubtitleService
from shadowing_player.storage.progress_store import ProgressStore, VideoProgress
from shadowing_player.storage.sentence_repository import SentenceRepository
from shadowing_player.storage.settings import AppSettings, load_settings, save_settings
from shadowing_player.transcription.model_manager import ModelManager
from shadowing_player.transcription.service import TranscriptionService
from shadowing_player.transcription.worker import CancellationToken, TranscriptionWorker
from shadowing_player.review.review_controller import ReviewController
from shadowing_player.ui import strings
from shadowing_player.ui.persistent_action_dock import PersistentActionDock
from shadowing_player.ui.sentence_table_model import SentenceTableModel
from shadowing_player.ui.sentence_item_delegate import SentenceItemDelegate
from shadowing_player.ui.sentence_progress_bar import SentenceProgressBar
from shadowing_player.ui.shortcut_dialog import ShortcutDialog
from shadowing_player.ui.split_sentence_dialog import SplitSentenceDialog
from shadowing_player.ui.review_dialog import ReviewDialog
from shadowing_player.ui.theme import apply_dark_theme
from shadowing_player.ui.transcription_status_bar import TranscriptionStatusBar


LOGGER = logging.getLogger(__name__)


@dataclass(eq=False, slots=True)
class _TranscriptionJob:
    video_path: Path
    thread: QThread
    worker: TranscriptionWorker
    token: CancellationToken
    progress: VideoProgress | None
    chinese_source: SubtitleSource | None


def _format_time(milliseconds: int) -> str:
    total_seconds = max(0, milliseconds // 1000)
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"


def _default_cache_dir() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    return base / "ShadowingPlayer" / "cache" / "subtitles"


def _default_data_dir() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    return base / "ShadowingPlayer"


class MainWindow(QMainWindow):
    def __init__(
        self,
        backend_factory: Callable[[int], MpvBackend] = MpvBackend,
        subtitle_service: SubtitleService | None = None,
        progress_store: ProgressStore | None = None,
        sentence_repository: SentenceRepository | None = None,
        transcription_service: TranscriptionService | None = None,
        settings_path: Path | None = None,
    ) -> None:
        super().__init__()
        self.setWindowTitle(strings.WINDOW_TITLE)
        self.resize(1180, 720)
        self.setMinimumSize(980, 640)
        self.setAcceptDrops(True)
        apply_dark_theme(self)
        self._subtitle_service = subtitle_service or SubtitleService(_default_cache_dir())
        self._subtitle_sources: list[SubtitleSource] = []
        data_dir = settings_path.parent if settings_path is not None else _default_data_dir()
        self._settings_path = settings_path or data_dir / "settings.json"
        self._settings, settings_warning = load_settings(self._settings_path)
        self._progress_store = progress_store or ProgressStore(data_dir / "data.sqlite")
        self._sentence_repository = sentence_repository or SentenceRepository(
            data_dir / "data.sqlite"
        )
        model_dir = bundled_model_dir() or (
            data_dir / "models" / "faster-whisper-small"
        )
        self._transcription_service = transcription_service or TranscriptionService(
            transcription_cache_dir(),
            ModelManager(model_dir),
            fallback_cache_dirs=(data_dir / "cache",),
        )
        self._current_video: Path | None = None
        self._last_position_ms = 0
        self._last_left_press = 0.0
        self._transcription_job: _TranscriptionJob | None = None
        self._transcription_jobs: list[_TranscriptionJob] = []
        self._queued_transcription: tuple[
            Path, VideoProgress | None, SubtitleSource | None
        ] | None = None
        self._close_pending = False
        self._teardown_complete = False
        self._review_in_progress = False
        self._review_return_video: Path | None = None
        self._review_return_mode: PlaybackMode | None = None

        root = QWidget(self)
        root.setObjectName("appRoot")
        outer = QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        top_bar = QFrame(root)
        top_bar.setObjectName("topBar")
        top = QHBoxLayout(top_bar)
        top.setContentsMargins(16, 10, 16, 10)
        top.setSpacing(10)
        self.open_button = QPushButton(strings.OPEN_VIDEO, top_bar)
        self.open_button.setObjectName("openButton")
        self.open_button.setToolTip("打开 MKV 或 MP4 视频")
        self.recent_button = QPushButton(strings.RECENT_WATCHING, top_bar)
        self.recent_button.setObjectName("recentButton")
        self.recent_menu = QMenu(self.recent_button)
        self.recent_button.setMenu(self.recent_menu)
        self.favorites_button = QPushButton(strings.FAVORITES, top_bar)
        self.favorites_button.setObjectName("favoritesButton")
        self.favorites_menu = QMenu(self.favorites_button)
        self.favorites_button.setMenu(self.favorites_menu)
        self.file_label = QLabel(strings.READY, top_bar)
        self.file_label.setObjectName("fileLabel")
        self.file_label.setMinimumWidth(160)
        self.file_label.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred
        )
        self.subtitle_combo = QComboBox(top_bar)
        self.subtitle_combo.setMinimumWidth(170)
        self.subtitle_combo.setMaximumWidth(240)
        subtitle_source_label = QLabel(strings.SUBTITLE_SOURCE, top_bar)
        subtitle_source_label.setObjectName("metaLabel")
        self.subtitle_mode_combo = QComboBox(top_bar)
        self.subtitle_mode_combo.setMinimumWidth(92)
        self.subtitle_mode_combo.setMaximumWidth(108)
        self.subtitle_mode_combo.addItem(strings.SUBTITLE_ENGLISH, "english")
        self.subtitle_mode_combo.addItem(strings.SUBTITLE_BILINGUAL, "bilingual")
        self.subtitle_mode_combo.addItem(strings.SUBTITLE_HIDDEN, "hidden")
        self.tools_button = QPushButton(strings.TOOLS, top_bar)
        self.tools_button.setObjectName("toolsButton")
        self.tools_menu = QMenu(self.tools_button)
        self.create_shortcut_action = self.tools_menu.addAction(
            strings.CREATE_DESKTOP_SHORTCUT
        )
        self.open_data_action = self.tools_menu.addAction(strings.OPEN_DATA_FOLDER)
        self.shortcut_help_action = self.tools_menu.addAction(strings.SHORTCUT_HELP)
        self.tools_button.setMenu(self.tools_menu)
        top.addWidget(self.open_button)
        top.addWidget(self.recent_button)
        top.addWidget(self.favorites_button)
        top.addWidget(self.file_label, 1)
        top.addWidget(subtitle_source_label)
        top.addWidget(self.subtitle_combo)
        top.addWidget(self.subtitle_mode_combo)
        top.addWidget(self.tools_button)
        outer.addWidget(top_bar)

        splitter = QSplitter(Qt.Orientation.Horizontal, root)
        splitter.setObjectName("mainSplitter")
        splitter.setHandleWidth(1)
        splitter.setChildrenCollapsible(False)
        left = QFrame(splitter)
        left.setObjectName("playerPanel")
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)
        self.video_widget = QWidget(left)
        self.video_widget.setObjectName("videoWidget")
        self.video_widget.setAttribute(Qt.WidgetAttribute.WA_DontCreateNativeAncestors)
        self.video_widget.setAttribute(Qt.WidgetAttribute.WA_NativeWindow)
        self.video_widget.setMinimumSize(480, 270)
        self.video_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        left_layout.addWidget(self.video_widget, 1)

        subtitle_stage = QFrame(left)
        subtitle_stage.setObjectName("subtitleStage")
        subtitle_layout = QVBoxLayout(subtitle_stage)
        subtitle_layout.setContentsMargins(18, 10, 18, 12)
        subtitle_layout.setSpacing(3)
        self.subtitle_label = QLabel("", subtitle_stage)
        self.subtitle_label.setObjectName("subtitleLabel")
        self.subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.subtitle_label.setWordWrap(True)
        self.subtitle_label.setMinimumHeight(54)
        subtitle_layout.addWidget(self.subtitle_label)
        self.prompt_label = QLabel("", subtitle_stage)
        self.prompt_label.setObjectName("promptLabel")
        self.prompt_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.prompt_label.setMinimumHeight(24)
        subtitle_layout.addWidget(self.prompt_label)
        self.sentence_progress = SentenceProgressBar(subtitle_stage)
        subtitle_layout.addWidget(self.sentence_progress)
        playback_meta = QHBoxLayout()
        playback_meta.setContentsMargins(1, 1, 1, 0)
        self.position_label = QLabel("00:00", subtitle_stage)
        self.sentence_counter_label = QLabel("暂无句子", subtitle_stage)
        self.duration_label = QLabel("00:00", subtitle_stage)
        for label in (
            self.position_label,
            self.sentence_counter_label,
            self.duration_label,
        ):
            label.setObjectName("playbackMetaLabel")
        self.position_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.sentence_counter_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.duration_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        playback_meta.addWidget(self.position_label, 1)
        playback_meta.addWidget(self.sentence_counter_label, 2)
        playback_meta.addWidget(self.duration_label, 1)
        subtitle_layout.addLayout(playback_meta)
        left_layout.addWidget(subtitle_stage)

        self.sentence_panel = QFrame(splitter)
        self.sentence_panel.setObjectName("sentencePanel")
        sentence_layout = QVBoxLayout(self.sentence_panel)
        sentence_layout.setContentsMargins(0, 0, 0, 0)
        sentence_layout.setSpacing(0)

        sentence_header = QFrame(self.sentence_panel)
        sentence_header.setObjectName("sentenceHeader")
        sentence_header_layout = QHBoxLayout(sentence_header)
        sentence_header_layout.setContentsMargins(14, 9, 10, 9)
        sentence_header_layout.setSpacing(7)
        sentence_title = QLabel("句子清单", sentence_header)
        sentence_title.setObjectName("sentenceTitle")
        sentence_hint = QLabel("点句跳播 · 点星收藏", sentence_header)
        sentence_hint.setObjectName("sentenceHint")
        self.merge_button = QPushButton(strings.MERGE_SENTENCES, sentence_header)
        self.split_button = QPushButton(strings.SPLIT_SENTENCE, sentence_header)
        for button in (self.merge_button, self.split_button):
            button.setObjectName("editorButton")
        sentence_header_layout.addWidget(sentence_title)
        sentence_header_layout.addWidget(sentence_hint, 1)
        sentence_header_layout.addWidget(self.merge_button)
        sentence_header_layout.addWidget(self.split_button)
        sentence_layout.addWidget(sentence_header)

        self.sentence_model = SentenceTableModel()
        self.sentence_list = QTableView(self.sentence_panel)
        self.sentence_list.setModel(self.sentence_model)
        self.sentence_list.setItemDelegate(SentenceItemDelegate(self.sentence_list))
        self.sentence_list.setAlternatingRowColors(True)
        self.sentence_list.setShowGrid(False)
        self.sentence_list.setWordWrap(True)
        self.sentence_list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.sentence_list.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.sentence_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.sentence_list.verticalHeader().setVisible(False)
        self.sentence_list.horizontalHeader().setVisible(False)
        self.sentence_list.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        self.sentence_list.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Fixed
        )
        self.sentence_list.setColumnWidth(1, 44)
        sentence_layout.addWidget(self.sentence_list, 1)

        sentence_footer = QFrame(self.sentence_panel)
        sentence_footer.setObjectName("sentenceFooter")
        sentence_footer_layout = QHBoxLayout(sentence_footer)
        sentence_footer_layout.setContentsMargins(12, 9, 12, 9)
        self.review_button = QPushButton(strings.REVIEW_LIST, sentence_footer)
        self.review_button.setObjectName("reviewButton")
        self.review_button.setToolTip("连续练习所有视频中已收藏的句子")
        sentence_footer_layout.addWidget(self.review_button)
        sentence_footer_layout.addStretch(1)
        sentence_layout.addWidget(sentence_footer)

        splitter.addWidget(left)
        splitter.addWidget(self.sentence_panel)
        splitter.setStretchFactor(0, 64)
        splitter.setStretchFactor(1, 36)
        splitter.setSizes([755, 425])
        outer.addWidget(splitter, 1)

        self.action_dock = PersistentActionDock(root)
        self.previous_button = self.action_dock.previous_button
        self.repeat_button = self.action_dock.repeat_button
        self.play_button = self.action_dock.play_button
        self.next_button = self.action_dock.next_button
        self.mode_action_button = self.action_dock.mode_action_button
        self.single_loop_button = self.action_dock.single_loop_button
        self.subtitle_action_button = self.action_dock.subtitle_action_button
        self.star_button = self.action_dock.star_button
        self.fullscreen_button = self.action_dock.fullscreen_button
        self.shortcut_button = self.action_dock.shortcut_button
        self.speed_down_button = self.action_dock.speed_down_button
        self.speed_up_button = self.action_dock.speed_up_button
        self.mode_combo = self.action_dock.mode_combo
        self.plays_combo = self.action_dock.plays_combo
        self.speed_combo = self.action_dock.speed_combo
        self.blank_combo = self.action_dock.blank_combo
        self.auto_advance_check = self.action_dock.auto_advance_check
        self.play_button.setEnabled(False)
        self.permanent_action_controls = {
            "open_video": self.open_button,
            "recent": self.recent_button,
            "play_pause": self.play_button,
            "repeat": self.repeat_button,
            "previous": self.previous_button,
            "next": self.next_button,
            "speed_up": self.speed_up_button,
            "speed_down": self.speed_down_button,
            "single_loop": self.single_loop_button,
            "subtitle": self.subtitle_action_button,
            "mode": self.mode_action_button,
            "star": self.star_button,
            "review": self.review_button,
            "fullscreen": self.fullscreen_button,
            "shortcut_help": self.shortcut_button,
        }
        outer.addWidget(self.action_dock)

        self.transcription_status = TranscriptionStatusBar(root)
        outer.addWidget(self.transcription_status)

        status_bar = QFrame(root)
        status_bar.setObjectName("statusBar")
        status_layout = QHBoxLayout(status_bar)
        status_layout.setContentsMargins(16, 5, 16, 6)
        self.status_label = QLabel(strings.READY, status_bar)
        self.status_label.setObjectName("statusLabel")
        self.status_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        status_layout.addWidget(self.status_label, 1)
        outer.addWidget(status_bar)
        self.setCentralWidget(root)

        self.backend = backend_factory(int(self.video_widget.winId()))
        self.controller = SessionController(self.backend)
        self.review_controller = ReviewController(self.backend, self.controller)
        self._apply_settings_to_widgets(self._settings)
        self.backend.set_speed(self._settings.speed)
        self._connect_signals()
        self._install_shortcuts()
        self._update_practice_config()
        self.controller.set_mode(self._settings.mode)
        self._refresh_action_dock()
        if settings_warning:
            self.status_label.setText(settings_warning)
        QTimer.singleShot(0, self._restore_last_session)

    @property
    def current_mode(self) -> PlaybackMode:
        return PlaybackMode(self.mode_combo.currentData())

    def _connect_signals(self) -> None:
        self.open_button.clicked.connect(self._choose_video)
        self.recent_menu.aboutToShow.connect(self._refresh_recent_menu)
        self.favorites_menu.aboutToShow.connect(self._refresh_favorites_menu)
        self.play_button.clicked.connect(self._toggle_play)
        self.previous_button.clicked.connect(lambda: self.controller.previous_sentence(True))
        self.repeat_button.clicked.connect(self.controller.repeat_current)
        self.next_button.clicked.connect(lambda: self.controller.next_sentence(True))
        self.action_dock.action_requested.connect(self._handle_dock_action)
        self.speed_combo.currentIndexChanged.connect(self._change_speed)
        self.mode_combo.currentIndexChanged.connect(self._change_mode)
        self.plays_combo.currentIndexChanged.connect(self._update_practice_config)
        self.blank_combo.currentIndexChanged.connect(self._update_practice_config)
        self.auto_advance_check.toggled.connect(self._update_practice_config)
        self.subtitle_mode_combo.currentIndexChanged.connect(self._subtitle_mode_changed)
        self.subtitle_combo.currentIndexChanged.connect(self._subtitle_source_changed)
        self.sentence_list.clicked.connect(self._sentence_clicked)
        self.sentence_model.starred_changed.connect(self._starred_changed)
        self.merge_button.clicked.connect(self._merge_selected)
        self.split_button.clicked.connect(self._split_current)
        self.review_button.clicked.connect(self._open_review)
        self.create_shortcut_action.triggered.connect(self._create_desktop_shortcut)
        self.open_data_action.triggered.connect(self._open_data_folder)
        self.shortcut_help_action.triggered.connect(self._show_shortcut_help)
        self.sentence_progress.sentence_clicked.connect(lambda index: self.controller.select_sentence(index, True))
        self.backend.pause_changed.connect(self._set_pause_label)
        self.backend.file_loaded.connect(self._file_loaded)
        self.backend.position_changed.connect(self._position_changed)
        self.backend.duration_changed.connect(self._duration_changed)
        self.backend.error.connect(self._show_error)
        self.controller.current_changed.connect(self._current_sentence_changed)
        self.controller.mode_changed.connect(self._controller_mode_changed)
        self.controller.phase_changed.connect(self._session_phase_changed)
        self.controller.prompt_changed.connect(self.prompt_label.setText)
        self.controller.completed.connect(lambda: self.prompt_label.setText(strings.PRACTICE_COMPLETED))
        self.review_controller.warning.connect(self.status_label.setText)
        self.review_controller.current_changed.connect(self._review_item_changed)
        self.review_controller.completed.connect(self._review_completed)
        self.transcription_status.cancel_requested.connect(
            self._request_transcription_cancel
        )

    def _install_shortcuts(self) -> None:
        for shortcut in getattr(self, "_shortcuts", []):
            shortcut.setEnabled(False)
            shortcut.deleteLater()
        self._shortcuts: list[QShortcut] = []
        actions = {
            "open_video": self._choose_video,
            "recent": self._show_recent_menu,
            "play_pause": self._toggle_if_available,
            "repeat": self._left_pressed,
            "previous": lambda: self.controller.previous_sentence(True),
            "next": lambda: self.controller.next_sentence(True),
            "speed_up": lambda: self._step_speed(-1),
            "speed_down": lambda: self._step_speed(1),
            "single_loop": self._toggle_single_loop,
            "subtitle": self._cycle_subtitle_mode,
            "mode": self._cycle_mode,
            "star": self._toggle_current_star,
            "review": self._open_review,
            "fullscreen": self._toggle_fullscreen,
            "shortcut_help": self._show_shortcut_help,
        }
        for name, slot in actions.items():
            sequence = QKeySequence(self._settings.shortcuts.get(name, ""))
            if sequence.isEmpty():
                continue
            shortcut = QShortcut(sequence, self)
            shortcut.activated.connect(slot)
            self._shortcuts.append(shortcut)
        self.action_dock.set_shortcut_hints(self._settings.shortcuts)
        definitions = {item.name: item for item in shortcut_definitions()}
        for name in ("open_video", "recent", "review"):
            sequence = self._settings.shortcuts.get(name, "")
            description = definitions[name].description
            binding = sequence or "未设置"
            self.permanent_action_controls[name].setToolTip(
                f"{description}（{binding}）"
            )

    def _handle_dock_action(self, name: str) -> None:
        actions = {
            "speed_up": lambda: self._step_speed(-1),
            "speed_down": lambda: self._step_speed(1),
            "single_loop": self._toggle_single_loop,
            "subtitle": self._cycle_subtitle_mode,
            "mode": self._cycle_mode,
            "star": self._toggle_current_star,
            "fullscreen": self._toggle_fullscreen,
            "shortcut_help": self._show_shortcut_help,
        }
        action = actions.get(name)
        if action is not None:
            action()

    def _refresh_action_dock(self) -> None:
        self.action_dock.set_mode(self.controller.mode)
        self.action_dock.set_subtitle_mode(
            str(self.subtitle_mode_combo.currentData())
        )
        sentence = self.controller.current_sentence
        self.action_dock.set_starred(
            bool(sentence and sentence.starred),
            enabled=sentence is not None,
        )
        self.action_dock.set_fullscreen(self.isFullScreen())
        has_sentence = sentence is not None
        for button in (
            self.previous_button,
            self.repeat_button,
            self.next_button,
        ):
            button.setEnabled(has_sentence)

    def _restore_last_session(self) -> None:
        if self._current_video is not None or self._close_pending:
            return
        try:
            candidates = self._progress_store.list_resume_candidates(limit=100)
            for item in candidates:
                path = item.path
                if (
                    not path.is_file()
                    or path.suffix.lower() not in {".mkv", ".mp4"}
                ):
                    continue
                # A changed file has no valid saved progress. Skipping it keeps
                # startup silent because open_video() plays brand-new files.
                if self._progress_store.load(path) is None:
                    continue
                self.open_video(path)
                return
        except Exception as exc:
            LOGGER.exception("恢复上次播放失败")
            self.status_label.setText(
                strings.STARTUP_RESTORE_ERROR.format(message=exc)
            )

    def _choose_video(self) -> None:
        path, _selected_filter = QFileDialog.getOpenFileName(
            self, strings.FILE_DIALOG_TITLE, "", strings.FILE_DIALOG_FILTER
        )
        if path:
            self.open_video(Path(path))

    def _refresh_recent_menu(self) -> None:
        self.recent_menu.clear()
        available = [
            item
            for item in self._progress_store.list_recent(limit=8)
            if item.path.is_file()
            and item.path.suffix.lower() in {".mkv", ".mp4"}
        ]
        if not available:
            action = self.recent_menu.addAction(strings.NO_RECENT_WATCHING)
            action.setEnabled(False)
            return
        for item in available:
            action = self.recent_menu.addAction(item.path.name)
            action.setToolTip(str(item.path))
            action.triggered.connect(
                lambda _checked=False, path=item.path: self.open_video(path)
            )

    def _show_recent_menu(self) -> None:
        self._refresh_recent_menu()
        self.recent_menu.popup(
            self.recent_button.mapToGlobal(self.recent_button.rect().bottomLeft())
        )

    def _refresh_favorites_menu(self) -> None:
        self.favorites_menu.clear()
        current = self._current_video
        try:
            if (
                current is None
                or not current.is_file()
                or current.suffix.lower() not in {".mkv", ".mp4"}
            ):
                toggle_action = self.favorites_menu.addAction(
                    strings.NO_VIDEO_TO_FAVORITE
                )
                toggle_action.setEnabled(False)
            else:
                is_favorite = self._progress_store.is_favorite(current)
                toggle_action = self.favorites_menu.addAction(
                    strings.REMOVE_VIDEO_FAVORITE
                    if is_favorite
                    else strings.ADD_VIDEO_FAVORITE
                )
                toggle_action.triggered.connect(
                    self._toggle_current_video_favorite
                )

            self.favorites_menu.addSeparator()
            available = [
                item
                for item in self._progress_store.list_favorites(limit=100)
                if item.path.is_file()
                and item.path.suffix.lower() in {".mkv", ".mp4"}
            ]
        except sqlite3.Error as exc:
            self.favorites_menu.clear()
            error_action = self.favorites_menu.addAction(
                strings.VIDEO_FAVORITE_ERROR.format(message=exc)
            )
            error_action.setEnabled(False)
            self.status_label.setText(error_action.text())
            return
        if not available:
            empty_action = self.favorites_menu.addAction(
                strings.NO_VIDEO_FAVORITES
            )
            empty_action.setEnabled(False)
            return
        for item in available:
            action = self.favorites_menu.addAction(item.path.name)
            action.setToolTip(str(item.path))
            action.triggered.connect(
                lambda _checked=False, path=item.path: self.open_video(path)
            )

    def _toggle_current_video_favorite(self) -> None:
        video = self._current_video
        if (
            video is None
            or not video.is_file()
            or video.suffix.lower() not in {".mkv", ".mp4"}
        ):
            return
        try:
            self._save_current_progress()
            favorite = not self._progress_store.is_favorite(video)
            self._progress_store.set_favorite(video, favorite)
        except (OSError, sqlite3.Error) as exc:
            self.status_label.setText(
                strings.VIDEO_FAVORITE_ERROR.format(message=exc)
            )
            return
        self.status_label.setText(
            (
                strings.VIDEO_FAVORITED
                if favorite
                else strings.VIDEO_UNFAVORITED
            ).format(name=video.name)
        )
        self._refresh_favorites_menu()

    def _create_desktop_shortcut(self) -> None:
        try:
            shortcut_path = create_desktop_shortcut()
        except (FileNotFoundError, OSError, ShortcutCreationError) as exc:
            message = strings.SHORTCUT_CREATE_FAILED.format(message=exc)
            self.status_label.setText(message)
            QMessageBox.warning(self, strings.TOOLS, message)
            return
        self.status_label.setText(
            strings.SHORTCUT_CREATED.format(path=shortcut_path)
        )

    def _open_data_folder(self) -> None:
        data_dir = self._settings_path.parent
        data_dir.mkdir(parents=True, exist_ok=True)
        if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(data_dir.resolve()))):
            self.status_label.setText(strings.DATA_FOLDER_OPEN_FAILED)

    def _show_shortcut_help(self) -> None:
        dialog = ShortcutDialog(self._settings.shortcuts, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self._settings.shortcuts = dialog.shortcuts()
        self._install_shortcuts()
        save_settings(self._settings_path, self._current_settings())
        self.status_label.setText(strings.SHORTCUTS_SAVED)

    @staticmethod
    def _dropped_video_path(mime_data: QMimeData) -> Path | None:
        urls = mime_data.urls()
        if len(urls) != 1 or not urls[0].isLocalFile():
            return None
        path = Path(urls[0].toLocalFile()).resolve()
        if not path.is_file() or path.suffix.lower() not in {".mkv", ".mp4"}:
            return None
        return path

    def dragEnterEvent(self, event) -> None:  # noqa: N802 - Qt API name
        if self._dropped_video_path(event.mimeData()) is not None:
            event.acceptProposedAction()
            return
        event.ignore()

    def dropEvent(self, event) -> None:  # noqa: N802 - Qt API name
        path = self._dropped_video_path(event.mimeData())
        if path is None:
            event.ignore()
            return
        event.acceptProposedAction()
        self.open_video(path)

    def open_video(self, video_path: Path) -> None:
        if self._close_pending:
            return
        self._abandon_transcription()
        self._save_current_progress()
        self._current_video = video_path.resolve()
        self._last_position_ms = 0
        progress = self._progress_store.load(self._current_video)
        self._progress_store.mark_opened(self._current_video)
        self.play_button.setEnabled(True)
        self.backend.open_file(str(video_path))
        self.file_label.setText(video_path.name)
        try:
            sources = self._subtitle_service.discover(video_path)
        except SubtitleError as exc:
            self._subtitle_sources = []
            self.sentence_model.set_sentences([])
            self.sentence_progress.set_sentence_count(0)
            self.status_label.setText(str(exc))
            self.controller.load_sentences([], self.backend.duration_ms)
            self._finish_open(progress)
            return
        self._subtitle_sources = sources
        if not sources:
            try:
                if hasattr(self._transcription_service, "existing_cache_path_for"):
                    cached = self._transcription_service.existing_cache_path_for(
                        self._current_video
                    )
                else:
                    candidate = self._transcription_service.cache_path_for(
                        self._current_video
                    )
                    cached = candidate if candidate.is_file() else None
            except OSError as exc:
                self.status_label.setText(str(exc))
                self._finish_open(progress)
                return
            if cached is not None and cached.is_file():
                source = SubtitleSource.external(cached)
                self._subtitle_sources = [source]
                self._populate_subtitle_combo([source], source)
                self._load_subtitle_source(source)
                self._finish_open(progress)
                return
            self.controller.load_sentences([], self.backend.duration_ms)
            answer = QMessageBox.question(
                self,
                strings.TRANSCRIBE_QUESTION_TITLE,
                strings.TRANSCRIBE_QUESTION,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes,
            )
            if answer == QMessageBox.StandardButton.Yes:
                self._finish_open(progress)
                self._start_transcription(self._current_video, None)
            else:
                self.status_label.setText(strings.NO_SUBTITLE)
                self._finish_open(progress)
            return

        self.subtitle_combo.blockSignals(True)
        self.subtitle_combo.clear()
        for source in sources:
            self.subtitle_combo.addItem(source.label, source)
        restored_source = next(
            (
                source
                for source in sources
                if progress is not None and source.identifier == progress.subtitle_source_id
            ),
            None,
        )
        default_source = restored_source
        chinese_source: SubtitleSource | None = None
        if hasattr(self._subtitle_service, "choose_language_sources"):
            english_source, chinese_source = self._subtitle_service.choose_language_sources(
                sources
            )
            if english_source is None and chinese_source is not None:
                try:
                    if hasattr(
                        self._transcription_service, "existing_cache_path_for"
                    ):
                        cached = (
                            self._transcription_service.existing_cache_path_for(
                                self._current_video
                            )
                        )
                    else:
                        candidate = self._transcription_service.cache_path_for(
                            self._current_video
                        )
                        cached = candidate if candidate.is_file() else None
                except OSError as exc:
                    self.subtitle_combo.blockSignals(False)
                    self.status_label.setText(str(exc))
                    self._finish_open(progress)
                    return
                if cached is not None and cached.is_file():
                    generated_source = SubtitleSource.external(cached)
                    combined_sources = [generated_source, *sources]
                    self._subtitle_sources = combined_sources
                    self._populate_subtitle_combo(
                        combined_sources, generated_source
                    )
                    self._load_subtitle_source(
                        generated_source, chinese_source
                    )
                    self._finish_open(progress)
                    return
                self.subtitle_combo.setCurrentIndex(sources.index(chinese_source))
                self.subtitle_combo.blockSignals(False)
                self.controller.load_sentences([], self.backend.duration_ms)
                self._finish_open(progress)
                self._start_transcription(
                    self._current_video, None, chinese_source
                )
                return
            if default_source is chinese_source:
                default_source = None
            default_source = default_source or english_source
        default_source = default_source or self._subtitle_service.choose_default(sources)
        if default_source is None:
            self.subtitle_combo.blockSignals(False)
            self.controller.load_sentences([], self.backend.duration_ms)
            self.status_label.setText(strings.NO_SUBTITLE)
            self._finish_open(progress)
            return
        default_index = sources.index(default_source)
        self.subtitle_combo.setCurrentIndex(default_index)
        self.subtitle_combo.blockSignals(False)
        self._load_subtitle_source(default_source, chinese_source)
        self._finish_open(progress)

    def _populate_subtitle_combo(
        self, sources: list[SubtitleSource], selected: SubtitleSource
    ) -> None:
        self.subtitle_combo.blockSignals(True)
        self.subtitle_combo.clear()
        for source in sources:
            self.subtitle_combo.addItem(source.label, source)
        self.subtitle_combo.setCurrentIndex(sources.index(selected))
        self.subtitle_combo.blockSignals(False)

    def _load_subtitle_source(
        self,
        source: SubtitleSource,
        chinese_source: SubtitleSource | None = None,
    ) -> None:
        try:
            if (
                chinese_source is not None
                and hasattr(self._subtitle_service, "load_bilingual_sentences")
            ):
                sentences = self._subtitle_service.load_bilingual_sentences(
                    source, chinese_source, self.backend.duration_ms or None
                )
            else:
                sentences = self._subtitle_service.load_sentences(
                    source, self.backend.duration_ms or None
                )
        except SubtitleError as exc:
            self.status_label.setText(str(exc))
            return
        if self._current_video is not None:
            source_key = self._source_content_key(source)
            if chinese_source is not None:
                source_key += f"|zh:{self._source_content_key(chinese_source)}"
            sentences = self._sentence_repository.replace_source_sentences(
                self._current_video, source_key, sentences
            )
        self._apply_sentences(sentences)
        self.status_label.setText(f"已载入 {len(sentences)} 句")

    @staticmethod
    def _source_content_key(source: SubtitleSource) -> str:
        try:
            stat = source.path.stat()
            return (
                f"{source.identifier}|{stat.st_size}|{stat.st_mtime_ns}|"
                f"{source.stream_index}"
            )
        except OSError:
            return source.identifier

    def _apply_sentences(self, sentences: list[Sentence]) -> None:
        self.sentence_model.set_sentences(sentences)
        self.sentence_model.set_subtitle_mode(str(self.subtitle_mode_combo.currentData()))
        self.sentence_list.resizeRowsToContents()
        self.sentence_progress.set_sentence_count(len(sentences))
        self.sentence_counter_label.setText(
            f"第 1 / {len(sentences)} 句" if sentences else "暂无句子"
        )
        self.controller.load_sentences(sentences, self.backend.duration_ms or None)
        self._refresh_action_dock()

    def _subtitle_source_changed(self, index: int) -> None:
        if not 0 <= index < len(self._subtitle_sources):
            return
        selected = self._subtitle_sources[index]
        if hasattr(self._subtitle_service, "choose_language_sources"):
            english_source, chinese_source = self._subtitle_service.choose_language_sources(
                self._subtitle_sources
            )
            if selected is chinese_source:
                if english_source is None:
                    self.status_label.setText(strings.ENGLISH_SUBTITLE_PENDING)
                    return
                self._load_subtitle_source(english_source, chinese_source)
                return
            self._load_subtitle_source(selected, chinese_source)
            return
        self._load_subtitle_source(selected)

    def _sentence_clicked(self, index) -> None:
        if index.column() == 1:
            self.sentence_model.toggle_star(index.row())
            return
        self.controller.select_sentence(index.row(), True)

    def _starred_changed(self, sentence: Sentence, starred: bool) -> None:
        self._sentence_repository.set_starred(sentence.id, starred)
        if 0 <= sentence.index < len(self.controller.sentences):
            self.controller.sentences[sentence.index] = sentence
        self.status_label.setText("已收藏" if starred else "已取消收藏")
        self._refresh_action_dock()

    def _toggle_current_star(self) -> None:
        sentence = self.controller.current_sentence
        if sentence is None:
            return
        if not self._review_in_progress:
            self.sentence_model.toggle_star(self.controller.current_index)
            return
        updated = replace(sentence, starred=not sentence.starred)
        self._sentence_repository.set_starred(updated.id, updated.starred)
        self.controller.sentences[self.controller.current_index] = updated
        review_index = self.review_controller.index
        if 0 <= review_index < len(self.review_controller.items):
            item = self.review_controller.items[review_index]
            self.review_controller.items[review_index] = replace(
                item, sentence=updated
            )
        self.status_label.setText(
            "已收藏" if updated.starred else "已取消收藏"
        )
        self._refresh_action_dock()

    def _merge_selected(self) -> None:
        rows = sorted(
            {index.row() for index in self.sentence_list.selectionModel().selectedRows()}
        )
        if len(rows) != 2 or rows[1] != rows[0] + 1:
            self.status_label.setText("请选择两个相邻句子")
            return
        first = self.sentence_model.sentences[rows[0]]
        second = self.sentence_model.sentences[rows[1]]
        try:
            sentences = self._sentence_repository.merge_adjacent(first.id, second.id)
        except ValueError as exc:
            self.status_label.setText(str(exc))
            return
        self._apply_sentences(sentences)
        self.controller.select_sentence(rows[0], autoplay=False)
        self.status_label.setText("已合并句子")

    def _split_current(self) -> None:
        sentence = self.controller.current_sentence
        if sentence is None:
            self.status_label.setText("当前没有可拆分的句子")
            return
        split_ms = self.backend.position_ms
        if not sentence.start_ms < split_ms < sentence.end_ms:
            self.status_label.setText("请先把播放位置移到句子中间")
            return
        ratio = (split_ms - sentence.start_ms) / max(1, sentence.duration_ms)
        values = SplitSentenceDialog.get_values(self, sentence, ratio)
        if values is None:
            return
        try:
            sentences = self._sentence_repository.split_sentence(
                sentence.id,
                split_ms,
                *values,
            )
        except ValueError as exc:
            self.status_label.setText(str(exc))
            return
        self._apply_sentences(sentences)
        self.controller.select_sentence(sentence.index, autoplay=False)
        self.status_label.setText("已拆分句子")

    def _open_review(self) -> None:
        items = self._sentence_repository.list_starred()
        if not items:
            self.status_label.setText(strings.NO_STARRED)
            return
        if not ReviewDialog.confirm(items, self):
            return
        self._save_current_progress()
        self._review_return_video = self._current_video
        self._review_return_mode = self.current_mode
        self._review_in_progress = True
        self.status_label.setText(f"开始复习 {len(items)} 句")
        self.review_controller.start(items)

    def _review_item_changed(self, index: int, item) -> None:
        self.file_label.setText(item.video_path.name)
        self.status_label.setText(f"复习第 {index + 1} / {len(self.review_controller.items)} 句")

    def _review_completed(self) -> None:
        self.status_label.setText(strings.PRACTICE_COMPLETED)
        return_video = self._review_return_video
        return_mode = self._review_return_mode
        self._review_in_progress = False
        self._review_return_video = None
        self._review_return_mode = None
        if return_video is not None and return_video.is_file():
            self._current_video = None
            self.open_video(return_video)
        elif return_mode is not None:
            self.controller.set_mode(return_mode)

    def _start_transcription(
        self,
        video_path: Path,
        progress: VideoProgress | None,
        chinese_source: SubtitleSource | None = None,
    ) -> None:
        resolved_video = video_path.resolve()
        if (
            self._teardown_complete
            or self._close_pending
            or self._current_video != resolved_video
        ):
            return
        if self._transcription_jobs:
            for running_job in self._transcription_jobs:
                running_job.token.cancel()
            self._queued_transcription = (
                resolved_video,
                progress,
                chinese_source,
            )
            self.transcription_status.start()
            self.transcription_status.label.setText(
                "正在等待上一个转写安全结束…"
            )
            self.status_label.setText("已排队后台转写")
            return
        token = CancellationToken()
        thread = QThread(self)
        worker = TranscriptionWorker(
            video_path,
            self._transcription_service,
            token,
        )
        job = _TranscriptionJob(
            video_path=resolved_video,
            thread=thread,
            worker=worker,
            token=token,
            progress=progress,
            chinese_source=chinese_source,
        )
        self._transcription_job = job
        self._transcription_jobs.append(job)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.phase_changed.connect(self._transcription_phase)
        worker.progress_changed.connect(self._transcription_progress)
        worker.completed.connect(self._transcription_completed)
        worker.cancelled.connect(self._transcription_cancelled)
        worker.failed.connect(self._transcription_failed)
        worker.completed.connect(thread.quit)
        worker.cancelled.connect(thread.quit)
        worker.failed.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(self._transcription_thread_finished)
        self.transcription_status.start()
        self.status_label.setText(strings.TRANSCRIBING)
        thread.start()

    def _job_for_sender(self) -> _TranscriptionJob | None:
        sender = self.sender()
        return next(
            (
                job
                for job in self._transcription_jobs
                if job.worker is sender or job.thread is sender
            ),
            None,
        )

    def _transcription_phase(self, phase: str) -> None:
        if self._job_for_sender() is not self._transcription_job:
            return
        self.transcription_status.set_phase(phase)

    def _transcription_progress(self, value: int) -> None:
        if self._job_for_sender() is not self._transcription_job:
            return
        self.transcription_status.set_progress(value)

    def _request_transcription_cancel(self) -> None:
        if self._transcription_job is not None:
            self._transcription_job.token.cancel()
            self.transcription_status.set_cancelling()
            self.status_label.setText(strings.CANCELLING)
        elif self._queued_transcription is not None:
            self._queued_transcription = None
            self.transcription_status.reset()
            self.status_label.setText(strings.TRANSCRIPTION_CANCELLED)

    def _transcription_completed(self, cache_path: str) -> None:
        job = self._job_for_sender()
        if job is None:
            return
        if (
            job is not self._transcription_job
            or self._close_pending
            or self._current_video != job.video_path
        ):
            return
        position_ms = self.backend.position_ms
        playing = not self.backend.is_paused
        source = SubtitleSource.external(Path(cache_path))
        combined_sources = [
            source,
            *[
                item
                for item in self._subtitle_sources
                if item.identifier != source.identifier
            ],
        ]
        self._subtitle_sources = combined_sources
        self._populate_subtitle_combo(combined_sources, source)
        self._load_subtitle_source(source, job.chinese_source)
        self.controller.sync_background_load(position_ms, playing=playing)
        self._finish_transcription_job(job)
        if job.progress is not None:
            self._finish_open(job.progress)

    def _transcription_cancelled(self) -> None:
        job = self._job_for_sender()
        if job is None or job is not self._transcription_job:
            return
        if not self._close_pending:
            self.status_label.setText(strings.TRANSCRIPTION_CANCELLED)
        self._finish_transcription_job(job)
        if job.progress is not None and not self._close_pending:
            self._finish_open(job.progress)

    def _transcription_failed(self, message: str) -> None:
        job = self._job_for_sender()
        if job is None or job is not self._transcription_job:
            return
        if not self._close_pending:
            self.status_label.setText(strings.ERROR.format(message=message))
            QMessageBox.warning(self, strings.TRANSCRIBE_QUESTION_TITLE, message)
        self._finish_transcription_job(job)
        if job.progress is not None and not self._close_pending:
            self._finish_open(job.progress)

    def _finish_transcription_job(self, job: _TranscriptionJob) -> None:
        job.thread.quit()
        if job is self._transcription_job:
            self._transcription_job = None
            self.transcription_status.reset()

    def _transcription_thread_finished(self) -> None:
        job = self._job_for_sender()
        if job is not None:
            self._transcription_jobs.remove(job)
            if job is self._transcription_job:
                self._transcription_job = None
                self.transcription_status.reset()
        if self._close_pending and not self._transcription_jobs:
            QTimer.singleShot(0, self.close)
            return
        if not self._transcription_jobs and self._queued_transcription is not None:
            video_path, progress, chinese_source = self._queued_transcription
            self._queued_transcription = None
            if self._current_video == video_path:
                QTimer.singleShot(
                    0,
                    lambda: self._start_transcription(
                        video_path, progress, chinese_source
                    ),
                )

    def _cancel_transcription(self) -> None:
        if self._transcription_job is not None:
            self._transcription_job.token.cancel()

    def _abandon_transcription(self) -> None:
        self._queued_transcription = None
        if self._transcription_job is None:
            return
        self._transcription_job.token.cancel()
        self._transcription_job = None
        self.transcription_status.reset()

    def _toggle_if_available(self) -> None:
        if self.play_button.isEnabled():
            self._toggle_play()

    def _toggle_play(self) -> None:
        self.controller.toggle_pause()

    def _change_speed(self, _index: int) -> None:
        speed = float(self.speed_combo.currentData())
        self.backend.set_speed(speed)
        self.status_label.setText(strings.SPEED_STATUS.format(speed=speed))

    def _change_mode(self, _index: int) -> None:
        self.controller.set_mode(self.current_mode)
        if self.play_button.isEnabled():
            self.controller.play_current()

    def _controller_mode_changed(self, mode: PlaybackMode) -> None:
        blocker = QSignalBlocker(self.mode_combo)
        self._set_combo_data(self.mode_combo, mode)
        del blocker
        self._refresh_action_dock()

    def _update_practice_config(self, *_args) -> None:
        self.controller.config.plays_per_sentence = int(self.plays_combo.currentData())
        self.controller.config.blank_multiplier = float(self.blank_combo.currentData())
        self.controller.config.auto_advance = self.auto_advance_check.isChecked()

    def _current_sentence_changed(self, index: int, sentence) -> None:
        self._show_sentence_text(sentence)
        self.sentence_progress.set_current_index(index)
        self.sentence_model.set_current_row(index)
        self.sentence_counter_label.setText(
            f"第 {index + 1} / {len(self.controller.sentences)} 句"
        )
        model_index = self.sentence_model.index(index, 0)
        self.sentence_list.scrollTo(model_index)
        self._refresh_action_dock()

    def _duration_changed(self, seconds: float) -> None:
        self.controller.video_duration_ms = round(seconds * 1000)
        self.duration_label.setText(_format_time(self.controller.video_duration_ms))

    def _position_changed(self, seconds: float) -> None:
        self._last_position_ms = round(seconds * 1000)
        self.position_label.setText(_format_time(self._last_position_ms))
        self.controller.on_position_ms(self._last_position_ms)

    def _set_pause_label(self, paused: bool) -> None:
        if self.controller.phase is SessionPhase.BLANK:
            self.action_dock.set_blank_paused(self.controller.blank_paused)
            return
        self.action_dock.set_playing(not paused)

    def _session_phase_changed(self, value: str) -> None:
        phase = SessionPhase(value)
        if phase is SessionPhase.BLANK:
            self.action_dock.set_blank_paused(self.controller.blank_paused)
            return
        self.action_dock.set_playing(phase is SessionPhase.PLAYING)

    def _file_loaded(self, path: str) -> None:
        self.file_label.setText(Path(path).name)
        LOGGER.info("当前速度：%.2fx；音调校正已启用", self.speed_combo.currentData())

    def _show_error(self, message: str) -> None:
        self.status_label.setText(strings.ERROR.format(message=message))

    def _finish_open(self, progress: VideoProgress | None) -> None:
        if progress is None:
            self.controller.set_mode(self.current_mode)
            self.controller.play_current()
            return
        self._set_combo_data(self.speed_combo, progress.speed)
        self._set_combo_data(self.mode_combo, progress.mode)
        self._set_combo_data(self.subtitle_mode_combo, progress.subtitle_mode)
        self.backend.set_speed(progress.speed)
        self.controller.set_mode(progress.mode)
        if self.controller.sentences:
            index = 0
            for candidate, sentence in enumerate(self.controller.sentences):
                if progress.position_ms < sentence.start_ms:
                    break
                index = candidate
            self.controller.select_sentence(index, autoplay=False)
        self.backend.seek_ms(progress.position_ms)
        self.backend.pause()
        self._last_position_ms = progress.position_ms
        self.position_label.setText(_format_time(self._last_position_ms))
        self.status_label.setText(f"已恢复到 {progress.position_ms / 1000:.1f} 秒，等待播放")

    def _apply_settings_to_widgets(self, settings: AppSettings) -> None:
        self._set_combo_data(self.speed_combo, settings.speed)
        self._set_combo_data(self.mode_combo, settings.mode)
        self._set_combo_data(self.plays_combo, settings.plays_per_sentence)
        self._set_combo_data(self.blank_combo, settings.blank_multiplier)
        self.auto_advance_check.setChecked(settings.auto_advance)
        subtitle_mode = settings.subtitle_mode
        if not settings.subtitle_visible:
            subtitle_mode = "hidden"
        self._set_combo_data(self.subtitle_mode_combo, subtitle_mode)
        self.sentence_model.set_subtitle_mode(subtitle_mode)
        self.subtitle_label.setVisible(subtitle_mode != "hidden")

    @staticmethod
    def _set_combo_data(combo: QComboBox, value) -> None:
        index = combo.findData(value)
        if index >= 0:
            combo.setCurrentIndex(index)

    def _save_current_progress(self) -> None:
        if (
            self._review_in_progress
            or self._current_video is None
            or not self._current_video.is_file()
        ):
            return
        source = self.subtitle_combo.currentData()
        source_id = source.identifier if isinstance(source, SubtitleSource) else ""
        self._progress_store.save(
            self._current_video,
            position_ms=self.backend.position_ms,
            speed=float(self.speed_combo.currentData()),
            mode=self.current_mode,
            subtitle_source_id=source_id,
            subtitle_mode=str(self.subtitle_mode_combo.currentData()),
        )

    def _current_settings(self) -> AppSettings:
        return AppSettings(
            speed=float(self.speed_combo.currentData()),
            mode=self._review_return_mode or self.current_mode,
            blank_multiplier=float(self.blank_combo.currentData()),
            plays_per_sentence=int(self.plays_combo.currentData()),
            auto_advance=self.auto_advance_check.isChecked(),
            subtitle_visible=self.subtitle_mode_combo.currentData() != "hidden",
            subtitle_mode=str(self.subtitle_mode_combo.currentData()),
            shortcuts=dict(self._settings.shortcuts),
        )

    def _subtitle_mode_changed(self, _index: int) -> None:
        mode = str(self.subtitle_mode_combo.currentData())
        self.sentence_model.set_subtitle_mode(mode)
        self.sentence_list.resizeRowsToContents()
        self.subtitle_label.setVisible(mode != "hidden")
        if self.controller.current_sentence is not None:
            self._show_sentence_text(self.controller.current_sentence)
        self._refresh_action_dock()

    def _show_sentence_text(self, sentence: Sentence) -> None:
        mode = str(self.subtitle_mode_combo.currentData())
        if mode == "hidden":
            self.subtitle_label.clear()
            return
        if mode == "bilingual" and sentence.text_zh:
            self.subtitle_label.setText(f"{sentence.text}\n{sentence.text_zh}")
        else:
            self.subtitle_label.setText(sentence.text)

    def _cycle_subtitle_mode(self) -> None:
        self.subtitle_mode_combo.setCurrentIndex(
            (self.subtitle_mode_combo.currentIndex() + 1)
            % self.subtitle_mode_combo.count()
        )

    def _left_pressed(self) -> None:
        now = time.monotonic()
        if now - self._last_left_press <= 0.4:
            self.controller.previous_sentence(True)
        else:
            self.controller.repeat_current()
        self._last_left_press = now

    def _step_speed(self, offset: int) -> None:
        index = min(max(0, self.speed_combo.currentIndex() + offset), self.speed_combo.count() - 1)
        self.speed_combo.setCurrentIndex(index)

    def _toggle_single_loop(self) -> None:
        target = PlaybackMode.WATCH if self.current_mode is PlaybackMode.SINGLE_LOOP else PlaybackMode.SINGLE_LOOP
        self._set_combo_data(self.mode_combo, target)

    def _cycle_mode(self) -> None:
        self.mode_combo.setCurrentIndex((self.mode_combo.currentIndex() + 1) % self.mode_combo.count())

    def _toggle_fullscreen(self) -> None:
        self.showNormal() if self.isFullScreen() else self.showFullScreen()
        self._refresh_action_dock()

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802 - Qt API name
        if self._teardown_complete:
            super().closeEvent(event)
            return
        if self._transcription_jobs:
            self._close_pending = True
            self._queued_transcription = None
            for job in self._transcription_jobs:
                job.token.cancel()
            for shortcut in self._shortcuts:
                shortcut.setEnabled(False)
            self.centralWidget().setEnabled(False)
            self.transcription_status.show()
            self.transcription_status.set_cancelling()
            self.status_label.setText("正在等待后台转写安全结束…")
            event.ignore()
            return
        self._teardown_complete = True
        self._save_current_progress()
        save_settings(self._settings_path, self._current_settings())
        self.controller.timer.cancel()
        self.backend.shutdown()
        self._progress_store.close()
        self._sentence_repository.close()
        super().closeEvent(event)
