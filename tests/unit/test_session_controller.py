from collections.abc import Callable

from shadowing_player.playback.session_controller import (
    PlaybackMode,
    PracticeConfig,
    SessionController,
    SessionPhase,
)
from shadowing_player.subtitles.models import Sentence


SENTENCES = [
    Sentence(0, 1_000, 2_000, "First"),
    Sentence(1, 3_000, 5_000, "Second"),
]


class FakePlayer:
    def __init__(self) -> None:
        self.seeks: list[int] = []
        self.play_count = 0
        self.pause_count = 0

    def seek_ms(self, position_ms: int) -> None:
        self.seeks.append(position_ms)

    def play(self) -> None:
        self.play_count += 1

    def pause(self) -> None:
        self.pause_count += 1


class FakeCountdown:
    def __init__(self) -> None:
        self.duration_ms = 0
        self.on_tick: Callable[[int], None] | None = None
        self.on_finished: Callable[[], None] | None = None
        self.cancel_count = 0
        self.is_paused = False

    def start(
        self,
        duration_ms: int,
        on_tick: Callable[[int], None],
        on_finished: Callable[[], None],
    ) -> None:
        self.duration_ms = duration_ms
        self.on_tick = on_tick
        self.on_finished = on_finished
        on_tick(duration_ms)

    def cancel(self) -> None:
        self.cancel_count += 1

    def pause(self) -> None:
        self.is_paused = True

    def resume(self) -> None:
        self.is_paused = False

    def fire(self) -> None:
        assert self.on_finished is not None
        self.on_finished()


def make_controller(config: PracticeConfig | None = None):
    player = FakePlayer()
    timer = FakeCountdown()
    controller = SessionController(player, timer=timer, config=config)
    controller.load_sentences(SENTENCES, video_duration_ms=6_000)
    return controller, player, timer


def test_watch_mode_tracks_sentence_from_playback_position() -> None:
    controller, _player, _timer = make_controller()
    controller.set_mode(PlaybackMode.WATCH)

    controller.on_position_ms(3_500)

    assert controller.current_index == 1


def test_watch_mode_selection_seeks_to_sentence_then_plays() -> None:
    controller, player, _timer = make_controller()
    controller.set_mode(PlaybackMode.WATCH)

    controller.select_sentence(1, autoplay=True)

    assert player.seeks == [2_750]
    assert player.play_count == 1


def test_shadowing_mode_selection_seeks_to_sentence_then_plays() -> None:
    controller, player, _timer = make_controller()
    controller.set_mode(PlaybackMode.SHADOWING)

    controller.select_sentence(1, autoplay=True)

    assert player.seeks == [2_750]
    assert player.play_count == 1


def test_watch_mode_repeat_seeks_to_current_sentence_then_plays() -> None:
    controller, player, _timer = make_controller()
    controller.set_mode(PlaybackMode.WATCH)
    controller.select_sentence(1, autoplay=False)
    player.seeks.clear()

    controller.repeat_current()

    assert player.seeks == [2_750]
    assert player.play_count == 1


def test_shadowing_mode_repeat_seeks_to_current_sentence_then_plays() -> None:
    controller, player, _timer = make_controller()
    controller.set_mode(PlaybackMode.SHADOWING)
    controller.select_sentence(1, autoplay=False)
    player.seeks.clear()

    controller.repeat_current()

    assert player.seeks == [2_750]
    assert player.play_count == 1


def test_sentence_practice_repeats_then_waits_and_advances() -> None:
    config = PracticeConfig(plays_per_sentence=2, blank_multiplier=1.5, auto_advance=True)
    controller, player, timer = make_controller(config)
    controller.set_mode(PlaybackMode.SENTENCE_PRACTICE)

    controller.play_current()
    controller.on_position_ms(2_250)
    controller.on_position_ms(2_250)

    assert player.seeks[:2] == [750, 750]
    assert timer.duration_ms == 1_500
    assert controller.phase is SessionPhase.BLANK

    timer.fire()

    assert controller.current_index == 1
    assert player.seeks[-1] == 2_750


def test_manual_sentence_practice_stays_after_blank() -> None:
    config = PracticeConfig(auto_advance=False)
    controller, player, timer = make_controller(config)
    controller.set_mode(PlaybackMode.SENTENCE_PRACTICE)
    controller.play_current()
    controller.on_position_ms(2_250)

    timer.fire()

    assert controller.current_index == 0
    assert controller.phase is SessionPhase.PAUSED
    assert player.pause_count >= 1


def test_single_loop_keeps_restarting_without_iteration_limit() -> None:
    controller, player, _timer = make_controller()
    controller.set_mode(PlaybackMode.SINGLE_LOOP)
    controller.play_current()

    for _ in range(5):
        controller.on_position_ms(2_250)

    assert player.seeks == [750] * 6
    assert controller.phase is SessionPhase.PLAYING
    assert player.pause_count == 0


def test_changing_mode_invalidates_old_blank_callback() -> None:
    controller, player, timer = make_controller()
    controller.set_mode(PlaybackMode.SENTENCE_PRACTICE)
    controller.play_current()
    controller.on_position_ms(2_250)
    stale_callback = timer.on_finished
    assert stale_callback is not None

    controller.set_mode(PlaybackMode.WATCH)
    stale_callback()

    assert controller.current_index == 0
    assert player.seeks == [750]


def test_last_sentence_completes_practice_after_blank() -> None:
    controller, player, timer = make_controller()
    controller.set_mode(PlaybackMode.SENTENCE_PRACTICE)
    controller.select_sentence(1, autoplay=True)
    controller.on_position_ms(5_250)

    timer.fire()

    assert controller.phase is SessionPhase.COMPLETED
    assert player.pause_count >= 2


def test_blank_countdown_can_be_paused_and_resumed() -> None:
    controller, _player, timer = make_controller()
    controller.set_mode(PlaybackMode.SENTENCE_PRACTICE)
    controller.play_current()
    controller.on_position_ms(2_250)

    controller.toggle_pause()
    assert timer.is_paused is True

    controller.toggle_pause()
    assert timer.is_paused is False


def test_space_pauses_and_resumes_single_loop_after_multiple_restarts() -> None:
    controller, player, _timer = make_controller()
    controller.set_mode(PlaybackMode.SINGLE_LOOP)
    controller.play_current()

    for _ in range(4):
        controller.on_position_ms(2_250)

    controller.toggle_pause()
    assert controller.phase is SessionPhase.PAUSED

    controller.toggle_pause()
    controller.on_position_ms(2_250)

    assert controller.phase is SessionPhase.PLAYING
    assert len(player.seeks) == 6


def test_shadowing_mode_plays_continuously_and_tracks_current_sentence() -> None:
    controller, player, _timer = make_controller()
    controller.set_mode(PlaybackMode.SHADOWING)

    controller.play_current()
    controller.on_position_ms(3_500)

    assert player.seeks == []
    assert player.play_count == 1
    assert controller.current_index == 1


def test_sync_background_loaded_sentences_keeps_position_and_play_state() -> None:
    controller, player, _timer = make_controller()

    controller.sync_background_load(3_500, playing=True)

    assert controller.current_index == 1
    assert controller.phase is SessionPhase.PLAYING
    assert player.seeks == []
    assert player.play_count == 0
