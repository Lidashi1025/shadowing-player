from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtGui import QKeySequence


@dataclass(frozen=True, slots=True)
class ShortcutDefinition:
    name: str
    label: str
    description: str
    category: str
    default: str


_DEFINITIONS = (
    ShortcutDefinition("open_video", "打开视频", "选择 MKV 或 MP4 文件", "文件", "Ctrl+O"),
    ShortcutDefinition("recent", "最近观看", "打开最近观看菜单", "文件", "Ctrl+H"),
    ShortcutDefinition("play_pause", "播放 / 暂停", "也可暂停或继续留白倒数", "播放", "Space"),
    ShortcutDefinition("repeat", "重播本句", "从当前句开头重新播放", "播放", "Left"),
    ShortcutDefinition("previous", "上一句", "跳到上一句并播放", "播放", "Ctrl+Left"),
    ShortcutDefinition("next", "下一句", "跳到下一句并播放", "播放", "Right"),
    ShortcutDefinition("speed_up", "加速", "每次提高 0.05 倍速", "播放", "Up"),
    ShortcutDefinition("speed_down", "减速", "每次降低 0.05 倍速", "播放", "Down"),
    ShortcutDefinition("single_loop", "单句循环", "切换单句精听模式", "练习", "L"),
    ShortcutDefinition("subtitle", "切换字幕显示", "英文、双语与隐藏依次切换", "练习", "M"),
    ShortcutDefinition("mode", "切换练习模式", "依次切换四种播放模式", "练习", "Tab"),
    ShortcutDefinition("star", "收藏 / 取消收藏", "切换当前句的收藏状态", "练习", "S"),
    ShortcutDefinition("review", "打开复习清单", "播放所有影片的收藏句", "练习", "R"),
    ShortcutDefinition("record", "录音 / 停止", "录制当前句跟读，再按结束", "练习", "Ctrl+R"),
    ShortcutDefinition("play_recording", "听录音", "播放当前句的录音", "练习", "Ctrl+Shift+R"),
    ShortcutDefinition("play_original", "听原句", "播放视频中的当前句", "练习", "Ctrl+Shift+O"),
    ShortcutDefinition("fullscreen", "全屏", "切换全屏与普通窗口", "窗口", "F"),
    ShortcutDefinition("shortcut_help", "快捷键设置", "打开本设置面板", "窗口", "F1"),
)


def shortcut_definitions() -> tuple[ShortcutDefinition, ...]:
    return _DEFINITIONS


def default_shortcuts() -> dict[str, str]:
    return {item.name: item.default for item in _DEFINITIONS}


def normalize_shortcut(sequence: str) -> str:
    return QKeySequence(sequence).toString(QKeySequence.SequenceFormat.PortableText)


def find_shortcut_conflicts(
    shortcuts: dict[str, str],
) -> dict[str, tuple[str, ...]]:
    by_sequence: dict[str, list[str]] = {}
    for name, raw_sequence in shortcuts.items():
        sequence = normalize_shortcut(raw_sequence)
        if not sequence:
            continue
        by_sequence.setdefault(sequence, []).append(name)
    return {
        sequence: tuple(names)
        for sequence, names in by_sequence.items()
        if len(names) > 1
    }
