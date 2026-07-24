from pathlib import Path
from types import SimpleNamespace

import pytest

from shadowing_player.runtime.windows_shortcut import (
    ShortcutCreationError,
    create_desktop_shortcut,
)


def test_create_desktop_shortcut_passes_portable_target_and_icon(
    tmp_path: Path,
) -> None:
    executable = tmp_path / "ShadowingPlayer.exe"
    executable.touch()
    desktop_shortcut = tmp_path / "Desktop" / "儿童影子跟读播放器.lnk"
    calls: list[tuple[list[str], dict]] = []

    def fake_runner(command, **kwargs):
        calls.append((command, kwargs))
        return SimpleNamespace(
            returncode=0,
            stdout=f"{desktop_shortcut}\n",
            stderr="",
        )

    result = create_desktop_shortcut(executable, runner=fake_runner)

    assert result == desktop_shortcut
    command, kwargs = calls[0]
    assert command[:4] == [
        "powershell.exe",
        "-NoProfile",
        "-NonInteractive",
        "-ExecutionPolicy",
    ]
    assert kwargs["env"]["SHADOWING_SHORTCUT_TARGET"] == str(executable.resolve())
    assert kwargs["env"]["SHADOWING_SHORTCUT_WORKDIR"] == str(tmp_path.resolve())
    assert kwargs["env"]["SHADOWING_SHORTCUT_ICON"] == (
        f"{executable.resolve()},0"
    )
    assert kwargs["env"]["SHADOWING_SHORTCUT_NAME"] == "儿童影子跟读播放器.lnk"


def test_create_desktop_shortcut_reports_powershell_failure(tmp_path: Path) -> None:
    executable = tmp_path / "ShadowingPlayer.exe"
    executable.touch()

    def failing_runner(_command, **_kwargs):
        return SimpleNamespace(returncode=1, stdout="", stderr="COM 创建失败")

    with pytest.raises(ShortcutCreationError, match="COM 创建失败"):
        create_desktop_shortcut(executable, runner=failing_runner)


def test_create_desktop_shortcut_requires_existing_executable(
    tmp_path: Path,
) -> None:
    with pytest.raises(FileNotFoundError, match="找不到播放器程序"):
        create_desktop_shortcut(tmp_path / "missing.exe")
