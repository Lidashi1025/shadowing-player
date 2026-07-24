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
