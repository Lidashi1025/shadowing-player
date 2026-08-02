from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path

from shadowing_player.storage.migrations import migrate_database
from shadowing_player.subtitles.models import Sentence
from shadowing_player.review.review_controller import ReviewItem


def _fingerprint(path: Path) -> str:
    stat = path.stat()
    raw = f"{path.resolve()}|{stat.st_size}|{stat.st_mtime_ns}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class SentenceRepository:
    def __init__(self, database_path: Path) -> None:
        database_path.parent.mkdir(parents=True, exist_ok=True)
        # timeout helps when a background loader and UI share the same DB file.
        self._connection = sqlite3.connect(database_path, timeout=30.0)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA busy_timeout=30000")
        migrate_database(self._connection, database_path)
        self._closed = False

    def ensure_video(self, video_path: Path) -> int:
        video = video_path.resolve()
        self._connection.execute(
            """
            INSERT INTO videos(path, fingerprint)
            VALUES (?, ?)
            ON CONFLICT(path) DO NOTHING
            """,
            (str(video), _fingerprint(video)),
        )
        row = self._connection.execute(
            "SELECT id FROM videos WHERE path=?", (str(video),)
        ).fetchone()
        if row is None:
            raise RuntimeError("无法建立影片资料")
        return int(row["id"])

    def replace_source_sentences(
        self,
        video_path: Path,
        source_key: str,
        sentences: list[Sentence],
    ) -> list[Sentence]:
        video_id = self.ensure_video(video_path)
        state = self._connection.execute(
            "SELECT sentence_source_key, sentences_edited FROM videos WHERE id=?",
            (video_id,),
        ).fetchone()
        existing = self._connection.execute(
            "SELECT COUNT(*) FROM sentences WHERE video_id=?", (video_id,)
        ).fetchone()[0]
        if state["sentences_edited"] and existing:
            self._connection.commit()
            return self.load_sentences(video_path)
        if existing and state["sentence_source_key"] == source_key:
            self._connection.commit()
            return self.load_sentences(video_path)

        starred_rows = self._connection.execute(
            """
            SELECT text_en, start_ms, starred_at
            FROM sentences
            WHERE video_id=? AND starred=1
            """,
            (video_id,),
        ).fetchall()
        with self._connection:
            self._connection.execute("DELETE FROM sentences WHERE video_id=?", (video_id,))
            for index, sentence in enumerate(sentences):
                match = next(
                    (
                        row
                        for row in starred_rows
                        if row["text_en"].strip().casefold()
                        == sentence.text.strip().casefold()
                        and abs(int(row["start_ms"]) - sentence.start_ms) <= 1_000
                    ),
                    None,
                )
                self._connection.execute(
                    """
                    INSERT INTO sentences(
                        video_id, idx, start_ms, end_ms, text_en, text_zh,
                        starred, starred_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        video_id,
                        index,
                        sentence.start_ms,
                        sentence.end_ms,
                        sentence.text,
                        sentence.text_zh,
                        int(sentence.starred or match is not None),
                        match["starred_at"] if match is not None else None,
                    ),
                )
            self._connection.execute(
                """
                UPDATE videos
                SET sentence_source_key=?, sentences_edited=0, updated_at=CURRENT_TIMESTAMP
                WHERE id=?
                """,
                (source_key, video_id),
            )
        return self.load_sentences(video_path)

    def load_sentences(self, video_path: Path) -> list[Sentence]:
        video = video_path.resolve()
        rows = self._connection.execute(
            """
            SELECT s.id, s.video_id, s.idx, s.start_ms, s.end_ms,
                   s.text_en, s.text_zh, s.starred
            FROM sentences s
            JOIN videos v ON v.id=s.video_id
            WHERE v.path=?
            ORDER BY s.idx
            """,
            (str(video),),
        ).fetchall()
        return [self._sentence_from_row(row) for row in rows]

    def set_starred(self, sentence_id: int | None, starred: bool) -> None:
        if sentence_id is None:
            return
        self._connection.execute(
            """
            UPDATE sentences
            SET starred=?,
                starred_at=CASE WHEN ? THEN COALESCE(starred_at, CURRENT_TIMESTAMP) ELSE NULL END
            WHERE id=?
            """,
            (int(starred), int(starred), sentence_id),
        )
        self._connection.commit()

    def list_starred(self) -> list[ReviewItem]:
        rows = self._connection.execute(
            """
            SELECT s.id, s.video_id, s.idx, s.start_ms, s.end_ms,
                   s.text_en, s.text_zh, s.starred, v.path
            FROM sentences s
            JOIN videos v ON v.id=s.video_id
            WHERE s.starred=1
            ORDER BY COALESCE(s.starred_at, ''), v.path, s.idx
            """
        ).fetchall()
        return [
            ReviewItem(Path(str(row["path"])), self._sentence_from_row(row))
            for row in rows
        ]

    def merge_adjacent(self, first_id: int | None, second_id: int | None) -> list[Sentence]:
        if first_id is None or second_id is None:
            raise ValueError("请选择两个相邻句子")
        rows = self._connection.execute(
            "SELECT * FROM sentences WHERE id IN (?, ?) ORDER BY idx",
            (first_id, second_id),
        ).fetchall()
        if len(rows) != 2 or rows[0]["video_id"] != rows[1]["video_id"]:
            raise ValueError("请选择同一影片中的两个句子")
        left, right = rows
        if int(right["idx"]) != int(left["idx"]) + 1:
            raise ValueError("只能合并相邻句子")
        text_zh = f"{left['text_zh']}{right['text_zh']}"
        starred = bool(left["starred"] or right["starred"])
        video_id = int(left["video_id"])
        with self._connection:
            self._connection.execute(
                """
                UPDATE sentences
                SET start_ms=?, end_ms=?, text_en=?, text_zh=?, starred=?,
                    starred_at=CASE WHEN ? THEN COALESCE(starred_at, ?) ELSE NULL END
                WHERE id=?
                """,
                (
                    min(int(left["start_ms"]), int(right["start_ms"])),
                    max(int(left["end_ms"]), int(right["end_ms"])),
                    f"{left['text_en'].rstrip()} {right['text_en'].lstrip()}".strip(),
                    text_zh,
                    int(starred),
                    int(starred),
                    right["starred_at"],
                    left["id"],
                ),
            )
            self._connection.execute("DELETE FROM sentences WHERE id=?", (right["id"],))
            self._connection.execute(
                "UPDATE sentences SET idx=idx+1000000 WHERE video_id=? AND idx>?",
                (video_id, right["idx"]),
            )
            self._connection.execute(
                "UPDATE sentences SET idx=idx-1000001 WHERE video_id=? AND idx>=1000000",
                (video_id,),
            )
            self._connection.execute(
                "UPDATE videos SET sentences_edited=1 WHERE id=?", (video_id,)
            )
        return self._load_by_video_id(video_id)

    def split_sentence(
        self,
        sentence_id: int | None,
        split_ms: int,
        left_text_en: str,
        right_text_en: str,
        left_text_zh: str = "",
        right_text_zh: str = "",
    ) -> list[Sentence]:
        if sentence_id is None:
            raise ValueError("请选择要拆分的句子")
        row = self._connection.execute(
            "SELECT * FROM sentences WHERE id=?", (sentence_id,)
        ).fetchone()
        if row is None:
            raise ValueError("句子不存在")
        if not int(row["start_ms"]) < split_ms < int(row["end_ms"]):
            raise ValueError("播放位置必须位于句子中间")
        if not left_text_en.strip() or not right_text_en.strip():
            raise ValueError("拆分后的英文文字不可为空")
        video_id = int(row["video_id"])
        with self._connection:
            self._connection.execute(
                "UPDATE sentences SET idx=idx+1000000 WHERE video_id=? AND idx>?",
                (video_id, row["idx"]),
            )
            self._connection.execute(
                "UPDATE sentences SET idx=idx-999999 WHERE video_id=? AND idx>=1000000",
                (video_id,),
            )
            self._connection.execute(
                """
                UPDATE sentences
                SET end_ms=?, text_en=?, text_zh=?
                WHERE id=?
                """,
                (split_ms, left_text_en.strip(), left_text_zh.strip(), sentence_id),
            )
            self._connection.execute(
                """
                INSERT INTO sentences(
                    video_id, idx, start_ms, end_ms, text_en, text_zh,
                    starred, starred_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    video_id,
                    int(row["idx"]) + 1,
                    split_ms,
                    row["end_ms"],
                    right_text_en.strip(),
                    right_text_zh.strip(),
                    row["starred"],
                    row["starred_at"],
                ),
            )
            self._connection.execute(
                "UPDATE videos SET sentences_edited=1 WHERE id=?", (video_id,)
            )
        return self._load_by_video_id(video_id)

    def _load_by_video_id(self, video_id: int) -> list[Sentence]:
        rows = self._connection.execute(
            """
            SELECT id, video_id, idx, start_ms, end_ms, text_en, text_zh, starred
            FROM sentences WHERE video_id=? ORDER BY idx
            """,
            (video_id,),
        ).fetchall()
        return [self._sentence_from_row(row) for row in rows]

    @staticmethod
    def _sentence_from_row(row: sqlite3.Row) -> Sentence:
        return Sentence(
            index=int(row["idx"]),
            start_ms=int(row["start_ms"]),
            end_ms=int(row["end_ms"]),
            text=str(row["text_en"]),
            text_zh=str(row["text_zh"]),
            starred=bool(row["starred"]),
            id=int(row["id"]),
            video_id=int(row["video_id"]),
        )

    def close(self) -> None:
        if not self._closed:
            self._connection.close()
            self._closed = True
