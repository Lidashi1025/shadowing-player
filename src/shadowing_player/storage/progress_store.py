from __future__ import annotations

import hashlib
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from shadowing_player.playback.session_controller import PlaybackMode
from shadowing_player.storage.migrations import migrate_database


@dataclass(frozen=True, slots=True)
class VideoProgress:
    position_ms: int
    speed: float
    mode: PlaybackMode
    subtitle_source_id: str
    subtitle_mode: str = "bilingual"


@dataclass(frozen=True, slots=True)
class RecentVideo:
    path: Path
    position_ms: int
    updated_at: str


@dataclass(frozen=True, slots=True)
class FavoriteVideo:
    path: Path
    position_ms: int
    favorited_at: str


def _fingerprint(video_path: Path) -> str:
    stat = video_path.stat()
    value = f"{video_path.resolve()}|{stat.st_size}|{stat.st_mtime_ns}"
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class ProgressStore:
    def __init__(self, database_path: Path) -> None:
        database_path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(database_path)
        migrate_database(self._connection, database_path)
        self._closed = False

    def save(
        self,
        video_path: Path,
        position_ms: int,
        speed: float,
        mode: PlaybackMode,
        subtitle_source_id: str,
        subtitle_mode: str = "bilingual",
    ) -> None:
        video = video_path.resolve()
        self._connection.execute(
            """
            INSERT INTO videos(
                path, fingerprint, last_position_ms, speed, mode,
                subtitle_source_id, subtitle_mode
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(path) DO UPDATE SET
                fingerprint=excluded.fingerprint,
                last_position_ms=excluded.last_position_ms,
                speed=excluded.speed,
                mode=excluded.mode,
                subtitle_source_id=excluded.subtitle_source_id,
                subtitle_mode=excluded.subtitle_mode,
                updated_at=CURRENT_TIMESTAMP
            """,
            (
                str(video),
                _fingerprint(video),
                max(0, int(position_ms)),
                float(speed),
                mode.value,
                subtitle_source_id,
                subtitle_mode,
            ),
        )
        self._connection.commit()

    def load(self, video_path: Path) -> VideoProgress | None:
        video = video_path.resolve()
        row = self._connection.execute(
            """
            SELECT fingerprint, last_position_ms, speed, mode,
                   subtitle_source_id, subtitle_mode
            FROM videos WHERE path = ?
            """,
            (str(video),),
        ).fetchone()
        if row is None or row[0] != _fingerprint(video):
            return None
        try:
            mode = PlaybackMode(row[3])
        except ValueError:
            mode = PlaybackMode.WATCH
        return VideoProgress(
            position_ms=int(row[1]),
            speed=float(row[2]),
            mode=mode,
            subtitle_source_id=str(row[4]),
            subtitle_mode=str(row[5]),
        )

    def mark_opened(self, video_path: Path) -> None:
        video = video_path.resolve()
        self._connection.execute(
            """
            INSERT INTO videos(path, fingerprint, updated_at)
            VALUES (?, ?, STRFTIME('%Y-%m-%d %H:%M:%f', 'now'))
            ON CONFLICT(path) DO UPDATE SET
                updated_at=STRFTIME('%Y-%m-%d %H:%M:%f', 'now')
            """,
            (str(video), _fingerprint(video)),
        )
        self._connection.commit()

    def list_recent(self, limit: int = 8) -> list[RecentVideo]:
        safe_limit = max(0, min(int(limit), 100))
        if safe_limit == 0:
            return []
        rows = self._connection.execute(
            """
            SELECT path, last_position_ms, updated_at
            FROM videos
            ORDER BY updated_at DESC, id DESC
            LIMIT ?
            """,
            (safe_limit,),
        ).fetchall()
        return [
            RecentVideo(
                path=Path(str(row[0])),
                position_ms=int(row[1]),
                updated_at=str(row[2]),
            )
            for row in rows
        ]

    def set_favorite(self, video_path: Path, favorite: bool) -> None:
        video = video_path.resolve()
        if favorite:
            self._connection.execute(
                """
                INSERT INTO videos(
                    path, fingerprint, is_favorite, favorited_at
                )
                VALUES (
                    ?, ?, 1, STRFTIME('%Y-%m-%d %H:%M:%f', 'now')
                )
                ON CONFLICT(path) DO UPDATE SET
                    is_favorite=1,
                    favorited_at=STRFTIME('%Y-%m-%d %H:%M:%f', 'now')
                """,
                (str(video), _fingerprint(video)),
            )
        else:
            self._connection.execute(
                """
                UPDATE videos
                SET is_favorite=0, favorited_at=NULL
                WHERE path=?
                """,
                (str(video),),
            )
        self._connection.commit()

    def is_favorite(self, video_path: Path) -> bool:
        row = self._connection.execute(
            "SELECT is_favorite FROM videos WHERE path=?",
            (str(video_path.resolve()),),
        ).fetchone()
        return bool(row and row[0])

    def list_favorites(self, limit: int = 100) -> list[FavoriteVideo]:
        safe_limit = max(0, min(int(limit), 100))
        if safe_limit == 0:
            return []
        rows = self._connection.execute(
            """
            SELECT path, last_position_ms, favorited_at
            FROM videos
            WHERE is_favorite=1
            ORDER BY favorited_at DESC, id DESC
            LIMIT ?
            """,
            (safe_limit,),
        ).fetchall()
        return [
            FavoriteVideo(
                path=Path(str(row[0])),
                position_ms=int(row[1]),
                favorited_at=str(row[2]),
            )
            for row in rows
        ]

    def list_resume_candidates(self, limit: int = 100) -> list[RecentVideo]:
        return self.list_recent(limit=limit)

    def close(self) -> None:
        if not self._closed:
            self._connection.close()
            self._closed = True
