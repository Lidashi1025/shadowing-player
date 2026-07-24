from __future__ import annotations

from pathlib import Path

import pytest

from shadowing_player.transcription.model_manager import ModelDownloadError, ModelManager


def test_model_manager_downloads_small_model_to_application_directory(tmp_path: Path) -> None:
    calls: list[tuple] = []

    def download(size: str, output_dir: str) -> str:
        calls.append((size, output_dir))
        model_dir = Path(output_dir)
        model_dir.mkdir(parents=True)
        (model_dir / "model.bin").write_bytes(b"model")
        (model_dir / "config.json").write_text("{}", encoding="utf-8")
        return str(model_dir)

    manager = ModelManager(tmp_path / "faster-whisper-small", downloader=download)

    assert manager.ensure_model() == tmp_path / "faster-whisper-small"
    assert calls == [("small", str(tmp_path / "faster-whisper-small"))]


def test_model_manager_reuses_local_model_without_downloading(tmp_path: Path) -> None:
    model_dir = tmp_path / "faster-whisper-small"
    model_dir.mkdir()
    (model_dir / "model.bin").write_bytes(b"model")
    (model_dir / "config.json").write_text("{}", encoding="utf-8")

    manager = ModelManager(
        model_dir,
        downloader=lambda *_args, **_kwargs: pytest.fail("download should not run"),
    )

    assert manager.ensure_model() == model_dir


def test_model_manager_wraps_download_failure_with_manual_instructions(tmp_path: Path) -> None:
    def fail(*_args, **_kwargs):
        raise OSError("offline")

    manager = ModelManager(tmp_path / "model", downloader=fail)

    with pytest.raises(ModelDownloadError) as captured:
        manager.ensure_model()

    assert str(tmp_path / "model") in str(captured.value)
    assert "download_model" in str(captured.value)
