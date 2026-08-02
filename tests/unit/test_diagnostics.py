from pathlib import Path
import subprocess

from shadowing_player.runtime.diagnostics import (
    configure_file_logging,
    probe_ffprobe,
)


def test_configure_file_logging_writes_handler(tmp_path: Path) -> None:
    log_path = configure_file_logging(tmp_path)
    assert log_path == tmp_path / "shadowing-player.log"
    assert log_path.parent.is_dir()
    # Second call should not duplicate handlers for the same path.
    again = configure_file_logging(tmp_path)
    assert again == log_path


def test_probe_ffprobe_missing(monkeypatch) -> None:
    monkeypatch.setattr(
        "shadowing_player.runtime.diagnostics.shutil.which",
        lambda _name: None,
    )
    ok, message = probe_ffprobe()
    assert ok is False
    assert "ffprobe" in message.lower()


def test_probe_ffprobe_ok(monkeypatch) -> None:
    monkeypatch.setattr(
        "shadowing_player.runtime.diagnostics.shutil.which",
        lambda _name: r"C:\Tools\ffprobe.exe",
    )

    def fake_runner(command: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            command, 0, stdout="ffprobe version test\n", stderr=""
        )

    ok, message = probe_ffprobe(runner=fake_runner)
    assert ok is True
    assert "ffprobe version test" in message
