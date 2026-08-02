from __future__ import annotations

import os
from pathlib import Path

from PyInstaller.utils.hooks import collect_all


project_root = Path(SPECPATH).resolve().parent
ffmpeg_dir = Path(os.environ["SHADOWING_FFMPEG_DIR"]).resolve()

datas = [
    (str(project_root / "assets" / "app-icon.ico"), "assets"),
]
binaries = [
    (
        str(project_root / "vendor" / "libmpv" / "libmpv-2.dll"),
        "vendor/libmpv",
    ),
    (str(ffmpeg_dir / "ffmpeg.exe"), "vendor/ffmpeg"),
    (str(ffmpeg_dir / "ffprobe.exe"), "vendor/ffmpeg"),
]
hiddenimports = ["mpv"]

for package in (
    "faster_whisper",
    "ctranslate2",
    "tokenizers",
    "av",
    "huggingface_hub",
    "pysubs2",
):
    package_datas, package_binaries, package_hiddenimports = collect_all(package)
    datas += package_datas
    binaries += package_binaries
    hiddenimports += package_hiddenimports

analysis = Analysis(
    [str(project_root / "src" / "shadowing_player" / "__main__.py")],
    pathex=[str(project_root / "src")],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "pytest",
        "pytestqt",
        "pytest_qt",
        "PIL",
        "pillow",
        "setuptools",
        "pkg_resources",
        "yaml",
        "tkinter",
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(analysis.pure)

exe = EXE(
    pyz,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="ShadowingPlayer",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(project_root / "assets" / "app-icon.ico"),
    version=None,
)

collection = COLLECT(
    exe,
    analysis.binaries,
    analysis.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="ShadowingPlayer",
)
