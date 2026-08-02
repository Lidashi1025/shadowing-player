from __future__ import annotations

import logging
import os
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path


LOGGER = logging.getLogger(__name__)

CommandRunner = Callable[[list[str]], subprocess.CompletedProcess[str]]


def default_data_dir() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    return base / "ShadowingPlayer"


def configure_file_logging(data_dir: Path | None = None) -> Path:
    """Attach a rotating log under the app data directory (2 MB × 3 backups)."""
    from logging.handlers import RotatingFileHandler

    target_dir = data_dir or default_data_dir()
    target_dir.mkdir(parents=True, exist_ok=True)
    log_path = target_dir / "shadowing-player.log"
    root = logging.getLogger()
    resolved = str(log_path.resolve())
    for handler in root.handlers:
        if getattr(handler, "baseFilename", None) == resolved:
            return log_path
    handler = RotatingFileHandler(
        log_path,
        maxBytes=2_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    handler.setLevel(logging.INFO)
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    )
    root.addHandler(handler)
    LOGGER.info("日志文件：%s", log_path)
    return log_path


def probe_ffprobe(runner: CommandRunner | None = None) -> tuple[bool, str]:
    """Return (ok, human message) for PATH/bundled ffprobe availability."""
    executable = shutil.which("ffprobe")
    if executable is None:
        return (
            False,
            "未找到 ffprobe。读取内嵌字幕需要把 ffmpeg/ffprobe 加入 PATH。",
        )
    run = runner or _run_version
    try:
        completed = run(["ffprobe", "-version"])
    except (OSError, subprocess.SubprocessError) as exc:
        return False, f"ffprobe 无法运行：{exc}"
    first_line = (completed.stdout or completed.stderr or "").splitlines()
    detail = first_line[0] if first_line else executable
    return True, f"ffprobe 可用：{detail}"


def _run_version(command: list[str]) -> subprocess.CompletedProcess[str]:
    creation_flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    return subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=creation_flags,
    )
