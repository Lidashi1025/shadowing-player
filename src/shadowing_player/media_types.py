from __future__ import annotations

from pathlib import Path

VIDEO_EXTENSIONS = frozenset({".mkv", ".mp4", ".webm", ".mov", ".avi", ".m4v"})

FILE_DIALOG_FILTER = (
    "视频文件 (*.mkv *.mp4 *.webm *.mov *.avi *.m4v);;所有文件 (*.*)"
)


def is_supported_video(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in VIDEO_EXTENSIONS
