from pathlib import Path

import pytest

from shadowing_player.runtime.libmpv_loader import configure_libmpv_path


def test_configure_libmpv_path_prepends_vendor_directory(tmp_path: Path) -> None:
    dll = tmp_path / "vendor" / "libmpv" / "libmpv-2.dll"
    dll.parent.mkdir(parents=True)
    dll.touch()
    environment = {"PATH": r"C:\\Windows\\System32"}

    resolved = configure_libmpv_path(tmp_path, environment)

    assert resolved == dll.resolve()
    assert environment["PATH"].split(";", 1)[0] == str(dll.parent.resolve())


def test_configure_libmpv_path_reports_missing_dll_in_chinese(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="(?s)找不到 libmpv-2.dll.*Missing libmpv-2.dll"):
        configure_libmpv_path(tmp_path, {"PATH": ""})


def test_configure_libmpv_path_also_prepends_bundled_ffmpeg(
    monkeypatch, tmp_path: Path
) -> None:
    dll = tmp_path / "vendor" / "libmpv" / "libmpv-2.dll"
    ffmpeg = tmp_path / "vendor" / "ffmpeg"
    dll.parent.mkdir(parents=True)
    ffmpeg.mkdir(parents=True)
    dll.touch()
    (ffmpeg / "ffmpeg.exe").touch()
    (ffmpeg / "ffprobe.exe").touch()
    monkeypatch.setattr(
        "shadowing_player.runtime.libmpv_loader.bundled_binary_dir",
        lambda: ffmpeg,
    )
    environment = {"PATH": r"C:\Windows\System32"}

    configure_libmpv_path(tmp_path, environment)

    path_parts = environment["PATH"].split(";")
    assert path_parts[:2] == [str(dll.parent.resolve()), str(ffmpeg.resolve())]
