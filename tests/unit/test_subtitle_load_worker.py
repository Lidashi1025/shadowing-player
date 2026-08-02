from pathlib import Path

from shadowing_player.playback.subtitle_load_worker import (
    SubtitleLoadController,
    SubtitleLoadResult,
)
from shadowing_player.storage.sentence_repository import SentenceRepository
from shadowing_player.subtitles.models import Sentence, SubtitleSource


class FakeService:
    def load_sentences(self, source, video_duration_ms=None):
        return [Sentence(0, 0, 1000, "Hello")]


def test_sync_load_emits_result(qtbot, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("SHADOWING_SYNC_SUBTITLE_LOAD", "1")
    controller = SubtitleLoadController()
    source = SubtitleSource.external(tmp_path / "a.srt")
    results: list[SubtitleLoadResult] = []
    controller.finished.connect(lambda result: results.append(result))
    controller.load(
        FakeService(),  # type: ignore[arg-type]
        video_path=tmp_path / "v.mp4",
        source=source,
        chinese_source=None,
        video_duration_ms=5_000,
        source_key="k",
    )
    qtbot.waitUntil(lambda: bool(results), timeout=1_000)
    assert results[0].sentences[0].text == "Hello"
    assert results[0].source_key == "k"
    assert results[0].persisted is False


def test_sync_load_can_persist_to_sqlite(qtbot, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("SHADOWING_SYNC_SUBTITLE_LOAD", "1")
    video = tmp_path / "clip.mp4"
    video.write_bytes(b"x")
    db = tmp_path / "data.sqlite"
    controller = SubtitleLoadController()
    results: list[SubtitleLoadResult] = []
    controller.finished.connect(lambda result: results.append(result))
    controller.load(
        FakeService(),  # type: ignore[arg-type]
        video_path=video,
        source=SubtitleSource.external(tmp_path / "a.srt"),
        chinese_source=None,
        video_duration_ms=5_000,
        source_key="k1",
        database_path=db,
    )
    qtbot.waitUntil(lambda: bool(results), timeout=1_000)
    assert results[0].persisted is True
    assert results[0].sentences[0].id is not None

    repo = SentenceRepository(db)
    loaded = repo.load_sentences(video)
    repo.close()
    assert len(loaded) == 1
    assert loaded[0].text == "Hello"
