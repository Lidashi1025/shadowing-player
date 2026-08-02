from __future__ import annotations

import os
from collections.abc import MutableMapping
from pathlib import Path

from shadowing_player.runtime.bundle_paths import (
    bundle_internal_dir,
    bundled_binary_dir,
    project_root,
)


def configure_libmpv_path(
    root: Path | None = None,
    environment: MutableMapping[str, str] | None = None,
) -> Path:
    """在导入 python-mpv 之前，将项目内 DLL 目录放到进程 PATH 首位。"""
    resolved_root = (root or bundle_internal_dir()).resolve()
    dll_path = resolved_root / "vendor" / "libmpv" / "libmpv-2.dll"
    if not dll_path.is_file():
        raise RuntimeError(
            "找不到 libmpv-2.dll，播放器无法启动。\n\n"
            "请按 vendor/libmpv/README.md 下载 mpv-dev x64 包中的 libmpv-2.dll，"
            f"并放到：\n{dll_path}\n\n"
            "Missing libmpv-2.dll. See vendor/libmpv/README.md and place the "
            f"x64 DLL at:\n{dll_path}"
        )

    target_environment = environment if environment is not None else os.environ
    dll_directory = str(dll_path.parent.resolve())
    entries = [dll_directory]
    binary_dir = bundled_binary_dir()
    if binary_dir is not None:
        entries.append(str(binary_dir.resolve()))
    current_path = target_environment.get("PATH", "")
    if current_path:
        entries.append(current_path)
    target_environment["PATH"] = os.pathsep.join(entries)
    return dll_path.resolve()
