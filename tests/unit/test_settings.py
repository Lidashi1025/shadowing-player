from pathlib import Path

from shadowing_player.playback.session_controller import PlaybackMode
from shadowing_player.storage.settings import AppSettings, load_settings, save_settings


def test_missing_settings_uses_first_version_defaults(tmp_path: Path) -> None:
    settings, warning = load_settings(tmp_path / "settings.json")

    assert settings.speed == 1.0
    assert settings.blank_multiplier == 1.5
    assert settings.mode is PlaybackMode.WATCH
    assert settings.shortcuts["play_pause"] == "Space"
    assert warning is None


def test_malformed_settings_falls_back_with_chinese_warning(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    path.write_text("{broken", encoding="utf-8")

    settings, warning = load_settings(path)

    assert settings == AppSettings()
    assert warning is not None and "设置文件格式错误" in warning


def test_settings_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    expected = AppSettings(speed=0.75, mode=PlaybackMode.SHADOWING, subtitle_visible=False)

    save_settings(path, expected)
    loaded, warning = load_settings(path)

    assert loaded == expected
    assert warning is None


def test_old_subtitle_visible_false_migrates_to_hidden_mode(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    path.write_text('{"subtitle_visible": false}', encoding="utf-8")

    settings, warning = load_settings(path)

    assert warning is None
    assert settings.subtitle_mode == "hidden"
