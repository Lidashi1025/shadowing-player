from __future__ import annotations

from pathlib import Path

from shadowing_player.runtime.package_self_test import verify_frozen_bundle


def test_verify_frozen_bundle_loads_cpu_int8_model_and_media_tools(
    tmp_path: Path,
) -> None:
    model = tmp_path / "model"
    binaries = tmp_path / "bin"
    model.mkdir()
    binaries.mkdir()
    (model / "model.bin").touch()
    (model / "config.json").touch()
    (binaries / "ffmpeg.exe").touch()
    (binaries / "ffprobe.exe").touch()
    model_calls: list[tuple] = []
    command_calls: list[list[str]] = []

    verify_frozen_bundle(
        model,
        binaries,
        model_factory=lambda path, **kwargs: model_calls.append((path, kwargs)),
        runner=lambda command: command_calls.append(command),
    )

    assert model_calls == [
        (str(model), {"device": "cpu", "compute_type": "int8"})
    ]
    assert command_calls == [
        [str(binaries / "ffmpeg.exe"), "-version"],
        [str(binaries / "ffprobe.exe"), "-version"],
    ]
