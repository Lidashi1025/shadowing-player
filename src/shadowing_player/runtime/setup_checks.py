from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path

from shadowing_player.runtime.bundle_paths import (
    bundle_internal_dir,
    bundled_binary_dir,
    bundled_model_dir,
    is_frozen,
)
from shadowing_player.runtime.diagnostics import default_data_dir, probe_ffprobe


@dataclass(frozen=True, slots=True)
class SetupCheck:
    """One environment check shown in the first-run checklist."""

    id: str
    title: str
    required: bool
    ok: bool
    detail: str
    fix_hint: str


def libmpv_path(root: Path | None = None) -> Path:
    resolved_root = (root or bundle_internal_dir()).resolve()
    return resolved_root / "vendor" / "libmpv" / "libmpv-2.dll"


def resolve_model_dir(data_dir: Path | None = None) -> Path:
    bundled = bundled_model_dir()
    if bundled is not None:
        return bundled
    base = data_dir or default_data_dir()
    return base / "models" / "faster-whisper-small"


def check_libmpv(root: Path | None = None) -> SetupCheck:
    path = libmpv_path(root)
    if path.is_file():
        return SetupCheck(
            id="libmpv",
            title="libmpv 播放引擎",
            required=True,
            ok=True,
            detail=str(path),
            fix_hint="",
        )
    return SetupCheck(
        id="libmpv",
        title="libmpv 播放引擎",
        required=True,
        ok=False,
        detail=f"未找到：{path}",
        fix_hint=(
            "按 vendor/libmpv/README.md 下载 mpv-dev x64 包中的 libmpv-2.dll，"
            f"放到：{path.parent}"
        ),
    )


def check_ffprobe() -> SetupCheck:
    ok, message = probe_ffprobe()
    if ok:
        return SetupCheck(
            id="ffprobe",
            title="ffprobe（内嵌字幕）",
            required=False,
            ok=True,
            detail=message,
            fix_hint="",
        )
    return SetupCheck(
        id="ffprobe",
        title="ffprobe（内嵌字幕）",
        required=False,
        ok=False,
        detail=message,
        fix_hint=(
            "安装 ffmpeg 完整包，并确保 ffmpeg.exe / ffprobe.exe 在 PATH 中。"
            "仅使用外部 .srt/.ass 时可暂时忽略。"
        ),
    )


def check_whisper_model(data_dir: Path | None = None) -> SetupCheck:
    model_dir = resolve_model_dir(data_dir)
    model_bin = model_dir / "model.bin"
    config = model_dir / "config.json"
    if model_bin.is_file() and config.is_file():
        size_mb = model_bin.stat().st_size / (1024 * 1024)
        return SetupCheck(
            id="model",
            title="离线语音模型（faster-whisper small）",
            required=False,
            ok=True,
            detail=f"{model_dir}（约 {size_mb:.0f} MB）",
            fix_hint="",
        )
    return SetupCheck(
        id="model",
        title="离线语音模型（faster-whisper small）",
        required=False,
        ok=False,
        detail=f"尚未就绪：{model_dir}",
        fix_hint=(
            "首次无字幕转写时会自动下载。也可手动执行：\n"
            "python -c \"from faster_whisper.utils import download_model; "
            f"download_model('small', output_dir=r'{model_dir}')\""
        ),
    )


def check_data_dir_writable(data_dir: Path | None = None) -> SetupCheck:
    target = data_dir or default_data_dir()
    try:
        target.mkdir(parents=True, exist_ok=True)
        probe = target / ".write_probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return SetupCheck(
            id="data_dir",
            title="用户数据目录可写",
            required=True,
            ok=True,
            detail=str(target),
            fix_hint="",
        )
    except OSError as exc:
        return SetupCheck(
            id="data_dir",
            title="用户数据目录可写",
            required=True,
            ok=False,
            detail=str(target),
            fix_hint=f"无法写入数据目录：{exc}",
        )


def check_ffmpeg_binary_bundle() -> SetupCheck | None:
    """Only relevant for frozen folder packages."""
    if not is_frozen():
        return None
    binary_dir = bundled_binary_dir()
    if binary_dir is not None:
        return SetupCheck(
            id="bundled_ffmpeg",
            title="打包内附 ffmpeg",
            required=False,
            ok=True,
            detail=str(binary_dir),
            fix_hint="",
        )
    return SetupCheck(
        id="bundled_ffmpeg",
        title="打包内附 ffmpeg",
        required=False,
        ok=False,
        detail="文件夹版缺少 _internal/vendor/ffmpeg",
        fix_hint="请重新解压完整 ShadowingPlayer 文件夹，不要只复制 exe。",
    )


def run_setup_checks(
    *,
    project_root: Path | None = None,
    data_dir: Path | None = None,
) -> list[SetupCheck]:
    checks = [
        check_libmpv(project_root),
        check_data_dir_writable(data_dir),
        check_ffprobe(),
        check_whisper_model(data_dir),
    ]
    bundled = check_ffmpeg_binary_bundle()
    if bundled is not None:
        checks.insert(2, bundled)
    return checks


def summary_lines(checks: list[SetupCheck]) -> list[str]:
    lines: list[str] = []
    for item in checks:
        mark = "OK" if item.ok else ("缺失*" if item.required else "可选未就绪")
        lines.append(f"[{mark}] {item.title}: {item.detail}")
        if not item.ok and item.fix_hint:
            lines.append(f"    → {item.fix_hint}")
    return lines


def has_blocking_failures(checks: list[SetupCheck]) -> bool:
    return any(not item.ok and item.required for item in checks)


def has_optional_gaps(checks: list[SetupCheck]) -> bool:
    return any(not item.ok and not item.required for item in checks)


def which_ffmpeg() -> str | None:
    return shutil.which("ffmpeg") or os.environ.get("SHADOWING_FFMPEG_DIR")
