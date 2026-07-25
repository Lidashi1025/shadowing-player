from __future__ import annotations

import sqlite3
from pathlib import Path


CURRENT_SCHEMA_VERSION = 2


def _table_exists(connection: sqlite3.Connection, name: str) -> bool:
    return (
        connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
        ).fetchone()
        is not None
    )


def _column_names(connection: sqlite3.Connection, table: str) -> set[str]:
    return {str(row[1]) for row in connection.execute(f"PRAGMA table_info({table})")}


def _backup_v0(connection: sqlite3.Connection, database_path: Path) -> None:
    if not database_path.is_file() or database_path.stat().st_size == 0:
        return
    backup_path = database_path.with_name(f"{database_path.name}.v0.bak")
    if backup_path.exists():
        return
    backup = sqlite3.connect(backup_path)
    try:
        connection.backup(backup)
    finally:
        backup.close()


def _create_latest_tables(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS videos (
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
            is_favorite INTEGER NOT NULL DEFAULT 0,
            favorited_at TEXT,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS sentences (
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
        )
        """
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_sentences_starred ON sentences(starred, starred_at)"
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_videos_favorite
        ON videos(is_favorite, favorited_at)
        """
    )


def migrate_database(connection: sqlite3.Connection, database_path: Path) -> None:
    """Migrate an existing first-version database without deleting progress."""

    version = int(connection.execute("PRAGMA user_version").fetchone()[0])
    if version > CURRENT_SCHEMA_VERSION:
        raise RuntimeError(f"数据库版本 {version} 高于程序支持的版本")
    connection.execute("PRAGMA foreign_keys=ON")
    if version == CURRENT_SCHEMA_VERSION:
        _create_latest_tables(connection)
        connection.commit()
        return

    _backup_v0(connection, database_path)
    try:
        connection.execute("BEGIN IMMEDIATE")
        if _table_exists(connection, "videos") and "id" not in _column_names(
            connection, "videos"
        ):
            old_count = int(connection.execute("SELECT COUNT(*) FROM videos").fetchone()[0])
            connection.execute(
                """
                CREATE TABLE videos_new (
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
                    is_favorite INTEGER NOT NULL DEFAULT 0,
                    favorited_at TEXT,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            connection.execute(
                """
                INSERT INTO videos_new(
                    path, fingerprint, last_position_ms, speed, mode,
                    subtitle_source_id, updated_at
                )
                SELECT path, fingerprint, last_position_ms, speed, mode,
                       subtitle_source_id, updated_at
                FROM videos
                """
            )
            new_count = int(
                connection.execute("SELECT COUNT(*) FROM videos_new").fetchone()[0]
            )
            if old_count != new_count:
                raise RuntimeError("数据库迁移校验失败：影片进度数量不一致")
            connection.execute("DROP TABLE videos")
            connection.execute("ALTER TABLE videos_new RENAME TO videos")
        if _table_exists(connection, "videos"):
            video_columns = _column_names(connection, "videos")
            if "is_favorite" not in video_columns:
                connection.execute(
                    """
                    ALTER TABLE videos
                    ADD COLUMN is_favorite INTEGER NOT NULL DEFAULT 0
                    """
                )
            if "favorited_at" not in video_columns:
                connection.execute(
                    "ALTER TABLE videos ADD COLUMN favorited_at TEXT"
                )
        _create_latest_tables(connection)
        connection.execute(f"PRAGMA user_version={CURRENT_SCHEMA_VERSION}")
        connection.commit()
    except Exception:
        connection.rollback()
        raise
