import time
from pathlib import Path

from shadowing_player.playback.session_controller import PlaybackMode
from shadowing_player.storage.progress_store import (
    ProgressStore,
    RecentVideo,
    VideoProgress,
)


def test_progress_round_trip_for_mp4(tmp_path: Path) -> None:
    movie = tmp_path / "episode.mp4"
    movie.write_bytes(b"video")
    store = ProgressStore(tmp_path / "data.sqlite")

    store.save(
        movie,
        position_ms=12_345,
        speed=0.75,
        mode=PlaybackMode.SHADOWING,
        subtitle_source_id="embedded:2",
    )

    assert store.load(movie) == VideoProgress(
        position_ms=12_345,
        speed=0.75,
        mode=PlaybackMode.SHADOWING,
        subtitle_source_id="embedded:2",
    )
    store.close()


def test_changed_video_does_not_restore_stale_progress(tmp_path: Path) -> None:
    movie = tmp_path / "episode.mkv"
    movie.write_bytes(b"first")
    store = ProgressStore(tmp_path / "data.sqlite")
    store.save(movie, 5_000, 1.0, PlaybackMode.WATCH, "external:episode.srt")

    movie.write_bytes(b"changed-content")

    assert store.load(movie) is None
    store.close()


def test_progress_round_trip_includes_subtitle_display_mode(tmp_path: Path) -> None:
    movie = tmp_path / "episode.mp4"
    movie.write_bytes(b"video")
    store = ProgressStore(tmp_path / "data.sqlite")

    store.save(
        movie,
        1_000,
        1.0,
        PlaybackMode.WATCH,
        "external:episode.srt",
        subtitle_mode="english",
    )

    assert store.load(movie).subtitle_mode == "english"
    store.close()


def test_recent_videos_are_newest_first_without_overwriting_progress(
    tmp_path: Path,
) -> None:
    first = tmp_path / "first.mp4"
    second = tmp_path / "second.mkv"
    first.write_bytes(b"first")
    second.write_bytes(b"second")
    store = ProgressStore(tmp_path / "data.sqlite")
    store.save(
        first,
        12_345,
        0.75,
        PlaybackMode.SHADOWING,
        "external:first.en.srt",
        subtitle_mode="bilingual",
    )
    store.mark_opened(second)
    time.sleep(0.01)
    store.mark_opened(first)

    recent = store.list_recent()

    assert all(isinstance(item, RecentVideo) for item in recent)
    assert [item.path for item in recent] == [first.resolve(), second.resolve()]
    assert store.load(first).position_ms == 12_345
    store.close()


def test_recent_videos_respect_limit(tmp_path: Path) -> None:
    store = ProgressStore(tmp_path / "data.sqlite")
    movies = [tmp_path / f"episode-{index}.mp4" for index in range(3)]
    for movie in movies:
        movie.write_bytes(movie.name.encode("utf-8"))
        store.mark_opened(movie)

    recent = store.list_recent(limit=2)

    assert len(recent) == 2
    store.close()
