from shadowing_player.app import _smoke_test_requested


def test_smoke_test_flag_is_explicit() -> None:
    assert _smoke_test_requested(["ShadowingPlayer.exe", "--smoke-test"])
    assert not _smoke_test_requested(["ShadowingPlayer.exe"])
