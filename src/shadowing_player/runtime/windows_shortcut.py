from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path


SHORTCUT_FILENAME = "儿童影子跟读播放器.lnk"

_CREATE_SHORTCUT_SCRIPT = r"""
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$desktop = [Environment]::GetFolderPath("Desktop")
$shortcutPath = Join-Path $desktop $env:SHADOWING_SHORTCUT_NAME
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $env:SHADOWING_SHORTCUT_TARGET
$shortcut.WorkingDirectory = $env:SHADOWING_SHORTCUT_WORKDIR
$shortcut.IconLocation = $env:SHADOWING_SHORTCUT_ICON
$shortcut.Description = "儿童影子跟读播放器"
$shortcut.Save()
Write-Output $shortcutPath
""".strip()


class ShortcutCreationError(RuntimeError):
    pass


def _default_executable() -> Path:
    if not getattr(sys, "frozen", False):
        raise ShortcutCreationError("请在打包版播放器中创建桌面快捷方式")
    return Path(sys.executable).resolve()


def create_desktop_shortcut(
    executable: Path | None = None,
    *,
    runner: Callable = subprocess.run,
) -> Path:
    target = (executable or _default_executable()).resolve()
    if not target.is_file():
        raise FileNotFoundError(f"找不到播放器程序：{target}")

    environment = os.environ.copy()
    environment.update(
        {
            "SHADOWING_SHORTCUT_NAME": SHORTCUT_FILENAME,
            "SHADOWING_SHORTCUT_TARGET": str(target),
            "SHADOWING_SHORTCUT_WORKDIR": str(target.parent),
            "SHADOWING_SHORTCUT_ICON": f"{target},0",
        }
    )
    result = runner(
        [
            "powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            _CREATE_SHORTCUT_SCRIPT,
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=environment,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "未知错误"
        raise ShortcutCreationError(f"创建桌面快捷方式失败：{detail}")
    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    if not lines:
        raise ShortcutCreationError("创建桌面快捷方式失败：PowerShell 未返回路径")
    return Path(lines[-1])
