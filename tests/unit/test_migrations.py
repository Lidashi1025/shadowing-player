from __future__ import annotations

import sqlite3
from pathlib import Path

from shadowing_player.storage.migrations import CURRENT_SCHEMA_VERSION, migrate_database


def _create_first_version_database(path: Path) -> None:
    connection = sqlite3.connect(path)
    connection.execute(
        """
        CREATE TABLE videos (
            path TEXT PRIMARY KEY,
            fingerprint TEXT NOT NULL,
            last_position_ms INTEGER NOT NULL,
            speed REAL NOT NULL,
            mode TEXT NOT NULL,
            subtitle_source_id TEXT NOT NULL,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    connection.execute(
        """
        INSERT INTO videos(
            path, fingerprint, last_position_ms, speed, mode, subtitle_source_id
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        ("D:/cartoons/episode.mp4", "old-fingerprint", 12_345, 0.75, "shadowing", "embedded:2"),
    )
    connection.commit()
    connection.close()


def _create_schema_one_database(path: Path) -> None:
    connection = sqlite3.connect(path)
    connection.executescript(
        """
        CREATE TABLE videos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT NOT NULL UNIQUE,
            fingerprint TEXT NOT NULL,
            last_position_ms INTEGER NOT NULL DEFAULT 0,
            speed REAL NOT NULL DEFAULT 1.0,
            mode TEXT NOT NULL DEFAULT 'watch',
            subtitle_source_id TEXT NOT NULL DEFAULT '',
            subtitle_mode TEXT NOT NULL DEFAULT 'bilingual',
            content_hash TEXT,
            sentence_source_key TEXT,
            sentences_edited INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE sentences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            video_id INTEGER NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
            idx INTEGER NOT NULL,
            start_ms INTEGER NOT NULL,
            end_ms INTEGER NOT NULL,
            text_en TEXT NOT NULL,
            text_zh TEXT NOT NULL DEFAULT '',
            starred INTEGER NOT NULL DEFAULT 0,
            starred_at TEXT,
            UNIQUE(video_id, idx)
        );
        PRAGMA user_version=1;
        """
    )
    cursor = connection.execute(
        """
        INSERT INTO videos(
            path, fingerprint, last_position_ms, speed, mode,
            subtitle_source_id, subtitle_mode, sentences_edited
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "D:/cartoons/episode.mp4",
            "fingerprint",
            12_345,
            0.75,
            "shadowing",
            "embedded:2",
            "bilingual",
            1,
        ),
    )
    connection.execute(
        """
        INSERT INTO sentences(
            video_id, idx, start_ms, end_ms, text_en, text_zh, starred, starred_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (cursor.lastrowid, 0, 1_000, 2_000, "Hello", "你好", 1, "2026-07-25"),
    )
    connection.commit()
    connection.close()


def test_migration_preserves_first_version_progress_and_adds_sentences(tmp_path: Path) -> None:
    database = tmp_path / "data.sqlite"
    _create_first_version_database(database)

    connection = sqlite3.connect(database)
    migrate_database(connection, database)

    assert connection.execute("PRAGMA user_version").fetchone()[0] == CURRENT_SCHEMA_VERSION
    assert connection.execute(
        """
        SELECT path, fingerprint, last_position_ms, speed, mode, subtitle_source_id
        FROM videos
        """
    ).fetchone() == (
        "D:/cartoons/episode.mp4",
        "old-fingerprint",
        12_345,
        0.75,
        "shadowing",
        "embedded:2",
    )
    sentence_columns = {
        row[1] for row in connection.execute("PRAGMA table_info(sentences)").fetchall()
    }
    assert {"text_en", "text_zh", "starred", "starred_at"} <= sentence_columns
    assert (tmp_path / "data.sqlite.v0.bak").is_file()
    connection.close()


def test_migration_from_schema_one_preserves_video_and_sentence_data(
    tmp_path: Path,
) -> None:
    database = tmp_path / "data.sqlite"
    _create_schema_one_database(database)
    connection = sqlite3.connect(database)

    migrate_database(connection, database)

    assert connection.execute("PRAGMA user_version").fetchone()[0] == 2
    video_columns = {
        row[1] for row in connection.execute("PRAGMA table_info(videos)").fetchall()
    }
    assert {"is_favorite", "favorited_at"} <= video_columns
    assert connection.execute(
        """
        SELECT path, last_position_ms, speed, mode, sentences_edited, is_favorite
        FROM videos
        """
    ).fetchone() == (
        "D:/cartoons/episode.mp4",
        12_345,
        0.75,
        "shadowing",
        1,
        0,
    )
    assert connection.execute(
        "SELECT text_en, text_zh, starred FROM sentences"
    ).fetchone() == ("Hello", "你好", 1)
    assert connection.execute(
        """
        SELECT COUNT(*) FROM sqlite_master
        WHERE type='index' AND name='idx_videos_favorite'
        """
    ).fetchone()[0] == 1
    connection.close()


def test_fresh_database_contains_video_favorite_columns(tmp_path: Path) -> None:
    database = tmp_path / "data.sqlite"
    connection = sqlite3.connect(database)

    migrate_database(connection, database)

    columns = {
        row[1] for row in connection.execute("PRAGMA table_info(videos)").fetchall()
    }
    assert {"is_favorite", "favorited_at"} <= columns
    assert connection.execute("PRAGMA user_version").fetchone()[0] == 2
    connection.close()


def test_migration_is_idempotent(tmp_path: Path) -> None:
    database = tmp_path / "data.sqlite"
    connection = sqlite3.connect(database)

    migrate_database(connection, database)
    migrate_database(connection, database)

    assert connection.execute("PRAGMA user_version").fetchone()[0] == CURRENT_SCHEMA_VERSION
    assert connection.execute(
        "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='sentences'"
    ).fetchone()[0] == 1
    connection.close()
