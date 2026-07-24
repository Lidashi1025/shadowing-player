from __future__ import annotations

import sys
from pathlib import Path

from shadowing_player.runtime.bundle_paths import (
    bundle_internal_dir,
    bundled_binary_dir,
    bundled_model_dir,
    executable_dir,
    transcription_cache_dir,
)


def test_frozen_paths_use_executable_and_meipass(monkeypatch, tmp_path: Path) -> None:
    executable = tmp_path / "ShadowingPlayer.exe"
    internal = tmp_path / "_internal"
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(internal), raising=False)
    monkeypatch.setattr(sys, "executable", str(executable))

    assert executable_dir() == tmp_path
    assert bundle_internal_dir() == internal


def test_bundled_model_requires_complete_model(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(tmp_path / "ShadowingPlayer.exe"))
    model = tmp_path / "models" / "faster-whisper-small"
    model.mkdir(parents=True)
    (model / "config.json").write_text("{}", encoding="utf-8")

    assert bundled_model_dir() is None

    (model / "model.bin").write_bytes(b"model")
    assert bundled_model_dir() == model


def test_bundled_binary_dir_requires_ffmpeg_and_ffprobe(
    monkeypatch, tmp_path: Path
) -> None:
    internal = tmp_path / "_internal"
    binary_dir = internal / "vendor" / "ffmpeg"
    binary_dir.mkdir(parents=True)
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(internal), raising=False)
    (binary_dir / "ffmpeg.exe").touch()

    assert bundled_binary_dir() is None

    (binary_dir / "ffprobe.exe").touch()
    assert bundled_binary_dir() == binary_dir


def test_transcription_cache_is_portable_when_frozen(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(tmp_path / "ShadowingPlayer.exe"))

    assert transcription_cache_dir() == tmp_path / "cache" / "transcriptions"


def test_transcription_cache_uses_project_folder_during_development(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.delattr(sys, "frozen", raising=False)
    monkeypatch.setattr(
        "shadowing_player.runtime.bundle_paths.project_root",
        lambda: tmp_path,
    )

    assert transcription_cache_dir() == tmp_path / "cache" / "transcriptions"
