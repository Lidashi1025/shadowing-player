from __future__ import annotations

from pathlib import Path

from shadowing_player.storage.sentence_repository import SentenceRepository
from shadowing_player.subtitles.models import Sentence


def test_sentence_repository_round_trips_bilingual_and_starred_sentences(tmp_path: Path) -> None:
    movie = tmp_path / "episode.mp4"
    movie.write_bytes(b"video")
    repository = SentenceRepository(tmp_path / "data.sqlite")
    sentences = [
        Sentence(0, 1_000, 2_000, "Hello", text_zh="你好"),
        Sentence(1, 3_000, 4_000, "Again", text_zh="再来一次"),
    ]

    stored = repository.replace_source_sentences(movie, "external:episode.srt", sentences)
    repository.set_starred(stored[1].id, True)
    loaded = repository.load_sentences(movie)

    assert [item.text for item in loaded] == ["Hello", "Again"]
    assert [item.text_zh for item in loaded] == ["你好", "再来一次"]
    assert [item.starred for item in loaded] == [False, True]
    assert loaded[1].video_id is not None
    repository.close()


def test_edited_sentences_override_a_new_raw_source(tmp_path: Path) -> None:
    movie = tmp_path / "episode.mkv"
    movie.write_bytes(b"video")
    repository = SentenceRepository(tmp_path / "data.sqlite")
    original = repository.replace_source_sentences(
        movie,
        "source:a",
        [Sentence(0, 0, 2_000, "One"), Sentence(1, 2_000, 4_000, "Two")],
    )
    repository.merge_adjacent(original[0].id, original[1].id)

    loaded = repository.replace_source_sentences(
        movie,
        "source:b",
        [Sentence(0, 0, 1_000, "Replacement")],
    )

    assert [(item.start_ms, item.end_ms, item.text) for item in loaded] == [
        (0, 4_000, "One Two")
    ]
    repository.close()


def test_split_sentence_persists_and_reindexes(tmp_path: Path) -> None:
    movie = tmp_path / "episode.mp4"
    movie.write_bytes(b"video")
    repository = SentenceRepository(tmp_path / "data.sqlite")
    stored = repository.replace_source_sentences(
        movie,
        "source:a",
        [Sentence(0, 0, 4_000, "Hello again", text_zh="你好再来", starred=True)],
    )

    repository.split_sentence(
        stored[0].id,
        split_ms=2_000,
        left_text_en="Hello",
        right_text_en="again",
        left_text_zh="你好",
        right_text_zh="再来",
    )
    repository.close()
    reopened = SentenceRepository(tmp_path / "data.sqlite")
    loaded = reopened.load_sentences(movie)

    assert [(item.index, item.start_ms, item.end_ms, item.text) for item in loaded] == [
        (0, 0, 2_000, "Hello"),
        (1, 2_000, 4_000, "again"),
    ]
    assert all(item.starred for item in loaded)
    reopened.close()


def test_lists_starred_sentences_across_videos_in_collection_order(tmp_path: Path) -> None:
    first_movie = tmp_path / "one.mp4"
    second_movie = tmp_path / "two.mp4"
    first_movie.write_bytes(b"one")
    second_movie.write_bytes(b"two")
    repository = SentenceRepository(tmp_path / "data.sqlite")
    first = repository.replace_source_sentences(
        first_movie, "one", [Sentence(0, 0, 1_000, "First")]
    )[0]
    second = repository.replace_source_sentences(
        second_movie, "two", [Sentence(0, 0, 1_000, "Second")]
    )[0]
    repository.set_starred(first.id, True)
    repository.set_starred(second.id, True)

    review = repository.list_starred()

    assert [(item.video_path, item.sentence.text) for item in review] == [
        (first_movie.resolve(), "First"),
        (second_movie.resolve(), "Second"),
    ]
    repository.close()


def test_split_first_of_three_sentences_reindexes_without_unique_collision(
    tmp_path: Path,
) -> None:
    movie = tmp_path / "episode.mp4"
    movie.write_bytes(b"video")
    repository = SentenceRepository(tmp_path / "data.sqlite")
    stored = repository.replace_source_sentences(
        movie,
        "source",
        [
            Sentence(0, 0, 2_000, "One part"),
            Sentence(1, 2_000, 3_000, "Two"),
            Sentence(2, 3_000, 4_000, "Three"),
        ],
    )

    repository.split_sentence(stored[0].id, 1_000, "One", "part")

    assert [item.text for item in repository.load_sentences(movie)] == [
        "One",
        "part",
        "Two",
        "Three",
    ]
    repository.close()
