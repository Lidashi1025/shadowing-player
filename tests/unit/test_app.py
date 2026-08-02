from shadowing_player.app import _smoke_test_requested, _version_requested
from shadowing_player import __version__


def test_smoke_test_flag_is_explicit() -> None:
    assert _smoke_test_requested(["ShadowingPlayer.exe", "--smoke-test"])
    assert not _smoke_test_requested(["ShadowingPlayer.exe"])


def test_version_flag_is_recognized() -> None:
    assert _version_requested(["shadowing-player", "--version"])
    assert _version_requested(["shadowing-player", "-V"])
    assert not _version_requested(["shadowing-player"])


def test_package_version_is_semver_like() -> None:
    parts = __version__.split(".")
    assert len(parts) >= 2
    assert all(part.isdigit() for part in parts[:2])
