from pathlib import Path

from shadowing_player.runtime.setup_checks import (
    check_libmpv,
    check_whisper_model,
    has_blocking_failures,
    has_optional_gaps,
    run_setup_checks,
    summary_lines,
)


def test_check_libmpv_ok(tmp_path: Path) -> None:
    dll = tmp_path / "vendor" / "libmpv" / "libmpv-2.dll"
    dll.parent.mkdir(parents=True)
    dll.touch()
    result = check_libmpv(tmp_path)
    assert result.ok is True
    assert result.required is True


def test_check_libmpv_missing(tmp_path: Path) -> None:
    result = check_libmpv(tmp_path)
    assert result.ok is False
    assert "libmpv-2.dll" in result.detail


def test_check_whisper_model_detects_files(tmp_path: Path) -> None:
    model_dir = tmp_path / "models" / "faster-whisper-small"
    model_dir.mkdir(parents=True)
    (model_dir / "model.bin").write_bytes(b"x" * 100)
    (model_dir / "config.json").write_text("{}", encoding="utf-8")
    result = check_whisper_model(tmp_path)
    assert result.ok is True
    assert "MB" in result.detail


def test_run_setup_checks_reports_blocking_when_libmpv_missing(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(
        "shadowing_player.runtime.setup_checks.bundle_internal_dir",
        lambda: tmp_path,
    )
    monkeypatch.setattr(
        "shadowing_player.runtime.setup_checks.probe_ffprobe",
        lambda: (True, "ffprobe ok"),
    )
    checks = run_setup_checks(project_root=tmp_path, data_dir=tmp_path)
    assert has_blocking_failures(checks) is True
    assert any("libmpv" in line for line in summary_lines(checks))


def test_optional_gaps_when_model_missing(tmp_path: Path, monkeypatch) -> None:
    dll = tmp_path / "vendor" / "libmpv" / "libmpv-2.dll"
    dll.parent.mkdir(parents=True)
    dll.touch()
    monkeypatch.setattr(
        "shadowing_player.runtime.setup_checks.probe_ffprobe",
        lambda: (True, "ffprobe ok"),
    )
    checks = run_setup_checks(project_root=tmp_path, data_dir=tmp_path)
    assert has_blocking_failures(checks) is False
    assert has_optional_gaps(checks) is True
