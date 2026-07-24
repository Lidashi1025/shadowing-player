import logging
from typing import Any, Callable

from shadowing_player.playback.mpv_backend import MpvBackend


class FakePlayer:
    def __init__(self, **options: Any) -> None:
        self.options = options
        self.pause = True
        self.speed = float(options["speed"])
        self.time_pos = 0.0
        self.duration = 120.0
        self.af = ["scaletempo2"]
        self.commands: list[tuple[Any, ...]] = []
        self.observers: dict[str, Callable[..., None]] = {}
        self.terminated = False

    def observe_property(self, name: str, callback: Callable[..., None]) -> None:
        self.observers[name] = callback

    def command(self, *parts: Any) -> None:
        self.commands.append(parts)

    def terminate(self) -> None:
        self.terminated = True


class FakeMpvModule:
    def __init__(self) -> None:
        self.player: FakePlayer | None = None

    def MPV(self, **options: Any) -> FakePlayer:
        self.player = FakePlayer(**options)
        return self.player


def test_backend_configures_embedded_pitch_preserving_player() -> None:
    module = FakeMpvModule()

    backend = MpvBackend(window_id=12345, mpv_module=module)

    assert module.player is not None
    expected_options = {
        "wid": "12345",
        "input_default_bindings": False,
        "input_vo_keyboard": False,
        "osc": False,
        "idle": "yes",
        "keep_open": "yes",
        "hr_seek": "yes",
        "audio_pitch_correction": "yes",
        "speed": 0.75,
        "sid": "no",
    }
    assert {key: module.player.options[key] for key in expected_options} == expected_options


def test_backend_logs_automatic_scaletempo2_insertion(caplog) -> None:
    module = FakeMpvModule()
    backend = MpvBackend(window_id=7, mpv_module=module)
    assert module.player is not None

    with caplog.at_level(logging.INFO):
        module.player.options["log_handler"]("v", "autoaspeed", "adding scaletempo2\n")

    assert module.player.options["loglevel"] == "v"
    assert "autoaspeed: adding scaletempo2" in caplog.text


def test_backend_loads_file_plays_and_toggles_pause() -> None:
    module = FakeMpvModule()
    backend = MpvBackend(window_id=7, mpv_module=module)
    assert module.player is not None

    backend.open_file(r"D:\videos\sample.mkv")
    backend.toggle_pause()

    assert module.player.commands == [("loadfile", r"D:\videos\sample.mkv", "replace")]
    assert module.player.pause is True


def test_backend_changes_speed_reports_filter_and_terminates() -> None:
    module = FakeMpvModule()
    backend = MpvBackend(window_id=7, mpv_module=module)
    assert module.player is not None

    backend.set_speed(1.0)
    filters = backend.audio_filters()
    backend.shutdown()

    assert module.player.speed == 1.0
    assert filters == ["scaletempo2"]
    assert module.player.terminated is True


def test_backend_supports_explicit_play_pause_and_exact_seek() -> None:
    module = FakeMpvModule()
    backend = MpvBackend(window_id=7, mpv_module=module)
    assert module.player is not None

    backend.play()
    backend.seek_ms(12_345)
    backend.pause()

    assert module.player.pause is True
    assert module.player.commands == [("seek", 12.345, "absolute+exact")]
    assert backend.position_ms == 0
    assert backend.duration_ms == 120_000
