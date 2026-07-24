from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from shadowing_player.playback.session_controller import PlaybackMode


class PersistentActionDock(QFrame):
    """Compact, always-visible controls for every keyboard action."""

    action_requested = Signal(str)

    _MODE_LABELS = {
        PlaybackMode.WATCH: "观看",
        PlaybackMode.SENTENCE_PRACTICE: "跟读",
        PlaybackMode.SINGLE_LOOP: "精听",
        PlaybackMode.SHADOWING: "影子",
    }
    _SUBTITLE_LABELS = {
        "english": "英文",
        "bilingual": "双语",
        "hidden": "隐藏",
    }
    _TOOLTIP_TEXT = {
        "previous": "上一句",
        "repeat": "重播本句",
        "play_pause": "播放或暂停",
        "next": "下一句",
        "mode": "切换练习模式",
        "single_loop": "切换单句循环",
        "subtitle": "切换英文、双语或隐藏字幕",
        "star": "收藏或取消收藏当前句",
        "fullscreen": "切换全屏",
        "shortcut_help": "查看并设置快捷键",
        "speed_down": "降低 0.05 倍速",
        "speed_up": "提高 0.05 倍速",
    }

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("persistentActionDock")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(7)

        primary_frame = QFrame(self)
        primary_frame.setObjectName("primaryActionRow")
        self.primary_row = QHBoxLayout(primary_frame)
        self.primary_row.setContentsMargins(0, 0, 0, 0)
        self.primary_row.setSpacing(6)
        layout.addWidget(primary_frame)

        self.previous_button = self._action_button("◀ 上一句", "previous", 74)
        self.repeat_button = self._action_button("↻ 重播", "repeat", 64)
        self.play_button = self._action_button("播放", "play_pause", 78)
        self.play_button.setObjectName("primaryPlayButton")
        self.next_button = self._action_button("下一句 ▶", "next", 74)
        self.mode_action_button = self._action_button("模式 · 观看", "mode", 96)
        self.single_loop_button = self._state_button("单句循环", "single_loop", 88)
        self.subtitle_action_button = self._state_button("字幕 · 英文", "subtitle", 96)
        self.star_button = self._state_button("☆ 收藏本句", "star", 92)
        self.star_button.setObjectName("favoriteAction")
        self.fullscreen_button = self._state_button("全屏", "fullscreen", 70)
        self.shortcut_button = self._action_button("快捷键", "shortcut_help", 78)
        for button in (
            self.previous_button,
            self.repeat_button,
            self.play_button,
            self.next_button,
            self.mode_action_button,
            self.single_loop_button,
            self.subtitle_action_button,
            self.star_button,
            self.fullscreen_button,
            self.shortcut_button,
        ):
            self.primary_row.addWidget(button)

        settings_frame = QFrame(self)
        settings_frame.setObjectName("settingsActionRow")
        self.settings_row = QHBoxLayout(settings_frame)
        self.settings_row.setContentsMargins(0, 0, 0, 0)
        self.settings_row.setSpacing(6)
        layout.addWidget(settings_frame)

        self.mode_combo = QComboBox(settings_frame)
        for mode, label in self._MODE_LABELS.items():
            self.mode_combo.addItem(f"模式 · {label}", mode)
        self.mode_combo.setFixedWidth(138)

        self.plays_combo = QComboBox(settings_frame)
        for count in range(1, 4):
            self.plays_combo.addItem(f"每句×{count}", count)
        self.plays_combo.setFixedWidth(100)

        self.speed_down_button = self._action_button("−", "speed_down", 42)
        self.speed_down_button.setObjectName("stepButton")
        self.speed_combo = QComboBox(settings_frame)
        for step in range(20, 9, -1):
            speed = step / 20
            self.speed_combo.addItem(f"速度 {speed:.2f}×", speed)
        self.speed_combo.setFixedWidth(150)
        self.speed_up_button = self._action_button("+", "speed_up", 42)
        self.speed_up_button.setObjectName("stepButton")

        self.blank_combo = QComboBox(settings_frame)
        for value in (1.2, 1.5, 1.8, 2.0, 2.5):
            self.blank_combo.addItem(f"留白 {value:.1f}×", value)
        self.blank_combo.setCurrentIndex(1)
        self.blank_combo.setFixedWidth(138)

        self.loop_combo = QComboBox(settings_frame)
        for count in range(1, 11):
            self.loop_combo.addItem(f"循环 {count} 次", count)
        self.loop_combo.addItem("循环无限", None)
        self.loop_combo.setCurrentIndex(2)
        self.loop_combo.setFixedWidth(138)

        self.auto_advance_check = QCheckBox("自动下一句", settings_frame)
        self.auto_advance_check.setChecked(True)
        self.auto_advance_check.setFixedWidth(
            self.auto_advance_check.sizeHint().width() + 12
        )

        for widget in (
            self.mode_combo,
            self.plays_combo,
            self.speed_down_button,
            self.speed_combo,
            self.speed_up_button,
            self.blank_combo,
            self.loop_combo,
            self.auto_advance_check,
        ):
            self.settings_row.addWidget(widget)
        self.settings_row.addStretch(1)

        self._action_controls = {
            "previous": self.previous_button,
            "repeat": self.repeat_button,
            "play_pause": self.play_button,
            "next": self.next_button,
            "mode": self.mode_action_button,
            "single_loop": self.single_loop_button,
            "subtitle": self.subtitle_action_button,
            "star": self.star_button,
            "fullscreen": self.fullscreen_button,
            "shortcut_help": self.shortcut_button,
            "speed_down": self.speed_down_button,
            "speed_up": self.speed_up_button,
        }
        self.set_shortcut_hints({})

    def _action_button(
        self, text: str, action_name: str, width: int
    ) -> QPushButton:
        button = QPushButton(text, self)
        button.setMinimumWidth(width)
        button.setProperty("dockAction", True)
        button.clicked.connect(
            lambda _checked=False, name=action_name: self.action_requested.emit(name)
        )
        return button

    def _state_button(
        self, text: str, action_name: str, width: int
    ) -> QPushButton:
        button = self._action_button(text, action_name, width)
        button.setCheckable(True)
        button.setProperty("actionState", True)
        return button

    @staticmethod
    def _set_active(button: QPushButton, active: bool) -> None:
        button.setChecked(active)
        button.setProperty("active", active)
        button.style().unpolish(button)
        button.style().polish(button)
        button.update()

    def set_playing(self, playing: bool) -> None:
        self.play_button.setText("暂停" if playing else "播放")

    def set_blank_paused(self, paused: bool) -> None:
        self.play_button.setText("继续留白" if paused else "暂停留白")

    def set_mode(self, mode: PlaybackMode) -> None:
        self.mode_action_button.setText(f"模式 · {self._MODE_LABELS[mode]}")
        self._set_active(
            self.single_loop_button, mode is PlaybackMode.SINGLE_LOOP
        )

    def set_subtitle_mode(self, mode: str) -> None:
        label = self._SUBTITLE_LABELS.get(mode, "英文")
        self.subtitle_action_button.setText(f"字幕 · {label}")
        self._set_active(self.subtitle_action_button, mode != "hidden")

    def set_starred(self, starred: bool, *, enabled: bool) -> None:
        self.star_button.setEnabled(enabled)
        self.star_button.setText("★ 已收藏" if starred else "☆ 收藏本句")
        self._set_active(self.star_button, starred)

    def set_fullscreen(self, fullscreen: bool) -> None:
        self.fullscreen_button.setText("退出全屏" if fullscreen else "全屏")
        self._set_active(self.fullscreen_button, fullscreen)

    def set_shortcut_hints(self, shortcuts: dict[str, str]) -> None:
        for name, control in self._action_controls.items():
            description = self._TOOLTIP_TEXT[name]
            sequence = shortcuts.get(name, "")
            binding = sequence or "未设置"
            control.setToolTip(f"{description}（{binding}）")
