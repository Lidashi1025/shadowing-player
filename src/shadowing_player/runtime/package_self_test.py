from __future__ import annotations

import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any


def _model_factory(path: str, **kwargs: Any):
    from faster_whisper import WhisperModel

    return WhisperModel(path, **kwargs)


def _runner(command: list[str]) -> None:
    subprocess.run(
        command,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def verify_frozen_bundle(
    model_dir: Path | None,
    binary_dir: Path | None,
    model_factory: Callable[..., Any] = _model_factory,
    runner: Callable[[list[str]], Any] = _runner,
) -> None:
    if model_dir is None:
        raise RuntimeError("Packaged faster-whisper model is missing or incomplete")
    if binary_dir is None:
        raise RuntimeError("Packaged ffmpeg/ffprobe directory is missing or incomplete")
    model_factory(str(model_dir), device="cpu", compute_type="int8")
    runner([str(binary_dir / "ffmpeg.exe"), "-version"])
    runner([str(binary_dir / "ffprobe.exe"), "-version"])
