from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from shadowing_player.transcription.service import (
    TranscriptionCancelled,
    TranscriptionService,
)


class FakeModel:
    def __init__(self) -> None:
        self.calls: list[tuple] = []

    def transcribe(self, path: str, **kwargs):
        self.calls.append((path, kwargs))
        words = [
            SimpleNamespace(start=0.0, end=1.0, word="Hello"),
            SimpleNamespace(start=1.1, end=2.0, word="world"),
        ]
        segments = iter(
            [SimpleNamespace(start=0.0, end=2.0, text="Hello world", words=words)]
        )
        return segments, SimpleNamespace(duration=4.0)


class FakeManager:
    def __init__(self, model_dir: Path) -> None:
        self.model_dir = model_dir
        self.calls = 0

    def ensure_model(self) -> Path:
        self.calls += 1
        return self.model_dir


def test_transcription_service_uses_fixed_english_cpu_configuration(tmp_path: Path) -> None:
    movie = tmp_path / "episode.mp4"
    movie.write_bytes(b"video")
    model = FakeModel()
    manager = FakeManager(tmp_path / "model")
    factory_calls: list[tuple] = []

    def factory(path: str, **kwargs):
        factory_calls.append((path, kwargs))
        return model

    progress: list[int] = []
    phases: list[str] = []
    service = TranscriptionService(
        tmp_path / "cache",
        manager,
        model_factory=factory,
    )

    result = service.transcribe(
        movie,
        on_progress=progress.append,
        on_phase=phases.append,
    )

    assert result.is_file()
    assert factory_calls == [
        (str(tmp_path / "model"), {"device": "cpu", "compute_type": "int8"})
    ]
    assert model.calls[0][1] == {
        "language": "en",
        "word_timestamps": True,
        "vad_filter": True,
    }
    assert progress[-1] == 100
    assert "transcribing" in phases


def test_transcription_service_reuses_cache_without_loading_model(tmp_path: Path) -> None:
    movie = tmp_path / "episode.mp4"
    movie.write_bytes(b"video")
    manager = FakeManager(tmp_path / "model")
    service = TranscriptionService(
        tmp_path / "cache",
        manager,
        model_factory=lambda *_args, **_kwargs: pytest.fail("model should not load"),
    )
    cache = service.cache_path_for(movie)
    cache.parent.mkdir(parents=True)
    cache.write_text(
        "1\n00:00:00,000 --> 00:00:01,000\nCached\n",
        encoding="utf-8",
    )

    assert service.transcribe(movie) == cache
    assert manager.calls == 0


def test_transcription_service_honors_cancellation_before_model_load(tmp_path: Path) -> None:
    movie = tmp_path / "episode.mp4"
    movie.write_bytes(b"video")
    manager = FakeManager(tmp_path / "model")
    service = TranscriptionService(tmp_path / "cache", manager)

    with pytest.raises(TranscriptionCancelled):
        service.transcribe(movie, is_cancelled=lambda: True)

    assert manager.calls == 0


def test_transcription_service_promotes_legacy_cache_without_loading_model(
    tmp_path: Path,
) -> None:
    movie = tmp_path / "episode.mp4"
    movie.write_bytes(b"video")
    primary = tmp_path / "portable-cache"
    legacy = tmp_path / "legacy-cache"
    manager = FakeManager(tmp_path / "model")
    service = TranscriptionService(
        primary,
        manager,
        model_factory=lambda *_args, **_kwargs: pytest.fail(
            "model should not load"
        ),
        fallback_cache_dirs=(legacy,),
    )
    legacy_path = legacy / service.cache_path_for(movie).name
    legacy_path.parent.mkdir(parents=True)
    legacy_path.write_text(
        "1\n00:00:00,000 --> 00:00:01,000\nLegacy cached line\n",
        encoding="utf-8",
    )

    result = service.transcribe(movie)

    assert result == primary / legacy_path.name
    assert result.read_text(encoding="utf-8") == legacy_path.read_text(
        encoding="utf-8"
    )
    assert manager.calls == 0


def test_existing_cache_lookup_promotes_legacy_before_ui_prompt(
    tmp_path: Path,
) -> None:
    movie = tmp_path / "episode.mp4"
    movie.write_bytes(b"video")
    primary = tmp_path / "portable-cache"
    legacy = tmp_path / "legacy-cache"
    service = TranscriptionService(
        primary,
        FakeManager(tmp_path / "model"),
        fallback_cache_dirs=(legacy,),
    )
    legacy_path = legacy / service.cache_path_for(movie).name
    legacy_path.parent.mkdir(parents=True)
    legacy_path.write_text("cached", encoding="utf-8")

    result = service.existing_cache_path_for(movie)

    assert result == primary / legacy_path.name
    assert result.read_text(encoding="utf-8") == "cached"
