from __future__ import annotations

import sys
from pathlib import Path


def project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def executable_dir() -> Path:
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return project_root()


def transcription_cache_dir() -> Path:
    return executable_dir() / "cache" / "transcriptions"


def bundle_internal_dir() -> Path:
    if is_frozen():
        return Path(getattr(sys, "_MEIPASS", executable_dir())).resolve()
    return project_root()


def bundled_model_dir() -> Path | None:
    if not is_frozen():
        return None
    candidate = executable_dir() / "models" / "faster-whisper-small"
    if (candidate / "model.bin").is_file() and (candidate / "config.json").is_file():
        return candidate
    return None


def bundled_binary_dir() -> Path | None:
    if not is_frozen():
        return None
    candidate = bundle_internal_dir() / "vendor" / "ffmpeg"
    if (candidate / "ffmpeg.exe").is_file() and (candidate / "ffprobe.exe").is_file():
        return candidate
    return None
