# Video Favorites and Startup Resume Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a video-level favorites menu whose entries track each video's latest progress, and silently restore the last valid video and progress when the app next starts.

**Architecture:** Extend the existing SQLite `videos` rows with favorite metadata so favorites and playback progress cannot diverge. Add narrow persistence APIs to `ProgressStore`, expose them through a top-bar favorites menu, and schedule one startup restore after `MainWindow` initialization while reusing the existing `open_video()` and paused progress restoration path.

**Tech Stack:** Python 3.12–3.14, PySide6 6.11.1, SQLite, pytest, pytest-qt, PyInstaller.

## Global Constraints

- Startup restore must remain paused and must not emit audio until the user presses play.
- A video has at most one favorite entry; later playback updates that entry's current progress.
- Missing, moved, or unsupported files remain in SQLite but are hidden from favorites and skipped during startup restore.
- Video favorites and existing sentence-star favorites remain separate features.
- Existing video progress, sentence data, sentence favorites, and sentence edits must survive schema migration.
- Reuse `MainWindow.open_video()` for favorite selection and startup restore.
- Do not add a new dependency or a new keyboard shortcut.

---

## File Structure

- `src/shadowing_player/storage/migrations.py`: schema version 2, favorite columns, index, and lossless migration.
- `src/shadowing_player/storage/progress_store.py`: favorite records and resume-candidate queries.
- `src/shadowing_player/ui/strings.py`: Simplified Chinese UI copy for video favorites and startup errors.
- `src/shadowing_player/ui/main_window.py`: favorites menu, toggle action, and one-shot startup restore.
- `tests/unit/test_migrations.py`: schema 1-to-2 preservation tests.
- `tests/unit/test_progress_store.py`: favorite and resume-candidate persistence tests.
- `tests/integration/test_main_window.py`: favorites menu and paused startup restoration tests.
- `README.md`: source-build feature documentation.
- `packaging/README.txt`: packaged-app usage documentation.

### Task 1: Migrate the Database to Video Favorite Schema

**Files:**

- Modify: `src/shadowing_player/storage/migrations.py`
- Test: `tests/unit/test_migrations.py`

**Interfaces:**

- Consumes: existing SQLite schema versions 0 and 1.
- Produces: `CURRENT_SCHEMA_VERSION = 2`; `videos.is_favorite`; `videos.favorited_at`; `idx_videos_favorite`.

- [ ] **Step 1: Write the failing schema migration tests**

Append the following helpers and tests to `tests/unit/test_migrations.py`:

```python
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
```

- [ ] **Step 2: Run the tests and verify the schema assertions fail**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit/test_migrations.py -q
```

Expected: the schema-one migration test fails because `is_favorite` and `favorited_at` do not exist, and the version assertion reports `1` instead of `2`.

- [ ] **Step 3: Implement schema version 2 and the lossless migration**

In `src/shadowing_player/storage/migrations.py`, set the version and extend the latest table definition:

```python
CURRENT_SCHEMA_VERSION = 2
```

Use these columns at the end of the `videos` definition, before `updated_at`:

```sql
is_favorite INTEGER NOT NULL DEFAULT 0,
favorited_at TEXT,
updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
```

Add the same two columns to the `videos_new` definition used by the legacy version-0 migration. At the end of `_create_latest_tables()`, add:

```python
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_videos_favorite
        ON videos(is_favorite, favorited_at)
        """
    )
```

Immediately before `_create_latest_tables(connection)` in the migration transaction, add the version-1 upgrade:

```python
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
```

- [ ] **Step 4: Run migration tests and verify they pass**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit/test_migrations.py -q
```

Expected: all migration tests pass, including legacy migration and idempotency.

- [ ] **Step 5: Commit the migration**

```powershell
git add src/shadowing_player/storage/migrations.py tests/unit/test_migrations.py
git commit -m "feat: add video favorite schema"
```

### Task 2: Add Favorite and Resume Queries to ProgressStore

**Files:**

- Modify: `src/shadowing_player/storage/progress_store.py`
- Test: `tests/unit/test_progress_store.py`

**Interfaces:**

- Consumes: schema-2 `videos` rows and existing `_fingerprint(Path)`.
- Produces:
  - `FavoriteVideo(path: Path, position_ms: int, favorited_at: str)`
  - `ProgressStore.set_favorite(video_path: Path, favorite: bool) -> None`
  - `ProgressStore.is_favorite(video_path: Path) -> bool`
  - `ProgressStore.list_favorites(limit: int = 100) -> list[FavoriteVideo]`
  - `ProgressStore.list_resume_candidates(limit: int = 100) -> list[RecentVideo]`

- [ ] **Step 1: Write failing persistence tests**

Import `FavoriteVideo` in `tests/unit/test_progress_store.py` and append:

```python
def test_favorite_is_unique_and_tracks_latest_playback_progress(
    tmp_path: Path,
) -> None:
    movie = tmp_path / "episode.mp4"
    movie.write_bytes(b"video")
    store = ProgressStore(tmp_path / "data.sqlite")
    store.save(movie, 1_000, 1.0, PlaybackMode.WATCH, "")

    store.set_favorite(movie, True)
    store.set_favorite(movie, True)
    store.save(movie, 9_000, 0.75, PlaybackMode.SHADOWING, "")

    favorites = store.list_favorites()
    assert favorites == [
        FavoriteVideo(movie.resolve(), 9_000, favorites[0].favorited_at)
    ]
    assert store.is_favorite(movie) is True
    store.close()


def test_cancel_favorite_preserves_video_progress(tmp_path: Path) -> None:
    movie = tmp_path / "episode.mp4"
    movie.write_bytes(b"video")
    store = ProgressStore(tmp_path / "data.sqlite")
    store.save(movie, 4_200, 1.0, PlaybackMode.WATCH, "")
    store.set_favorite(movie, True)

    store.set_favorite(movie, False)

    assert store.is_favorite(movie) is False
    assert store.list_favorites() == []
    assert store.load(movie).position_ms == 4_200
    store.close()


def test_favorites_are_newest_first_and_respect_limit(tmp_path: Path) -> None:
    first = tmp_path / "first.mp4"
    second = tmp_path / "second.mkv"
    first.write_bytes(b"first")
    second.write_bytes(b"second")
    store = ProgressStore(tmp_path / "data.sqlite")
    store.set_favorite(first, True)
    time.sleep(0.01)
    store.set_favorite(second, True)

    favorites = store.list_favorites(limit=1)

    assert [item.path for item in favorites] == [second.resolve()]
    store.close()


def test_resume_candidates_reuse_recent_open_order(tmp_path: Path) -> None:
    first = tmp_path / "first.mp4"
    second = tmp_path / "second.mp4"
    first.write_bytes(b"first")
    second.write_bytes(b"second")
    store = ProgressStore(tmp_path / "data.sqlite")
    store.mark_opened(first)
    time.sleep(0.01)
    store.mark_opened(second)

    candidates = store.list_resume_candidates()

    assert [item.path for item in candidates] == [
        second.resolve(),
        first.resolve(),
    ]
    store.close()
```

- [ ] **Step 2: Run the focused tests and verify the new API is missing**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit/test_progress_store.py -q
```

Expected: collection or test failures report that `FavoriteVideo`, `set_favorite`, `is_favorite`, `list_favorites`, and `list_resume_candidates` are missing.

- [ ] **Step 3: Implement the minimal ProgressStore API**

Add the data class after `RecentVideo` in `src/shadowing_player/storage/progress_store.py`:

```python
@dataclass(frozen=True, slots=True)
class FavoriteVideo:
    path: Path
    position_ms: int
    favorited_at: str
```

Add these methods to `ProgressStore` before `close()`:

```python
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
```

- [ ] **Step 4: Run storage tests and verify they pass**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit/test_progress_store.py -q
```

Expected: every progress-store test passes.

- [ ] **Step 5: Commit the persistence API**

```powershell
git add src/shadowing_player/storage/progress_store.py tests/unit/test_progress_store.py
git commit -m "feat: persist video favorites"
```

### Task 3: Add the Top-Bar Favorites Menu

**Files:**

- Modify: `src/shadowing_player/ui/strings.py`
- Modify: `src/shadowing_player/ui/main_window.py`
- Modify: `tests/integration/test_main_window.py`

**Interfaces:**

- Consumes: all `ProgressStore` favorite methods from Task 2 and existing `_save_current_progress()` / `open_video(Path)`.
- Produces:
  - `MainWindow.favorites_button`
  - `MainWindow.favorites_menu`
  - `MainWindow._refresh_favorites_menu()`
  - `MainWindow._toggle_current_video_favorite()`

- [ ] **Step 1: Extend FakeProgressStore and write failing favorites-menu tests**

Import `sqlite3`, and import `FavoriteVideo` alongside `RecentVideo` in
`tests/integration/test_main_window.py`. Extend `FakeProgressStore.__init__` with:

```python
        self.favorites: list[FavoriteVideo] = []
        self.favorite_paths: set[Path] = set()
        self.favorite_changes: list[tuple[Path, bool]] = []
        self.resume_candidates: list[RecentVideo] = []
```

Add these methods to `FakeProgressStore`:

```python
    def set_favorite(self, path: Path, favorite: bool) -> None:
        resolved = path.resolve()
        self.favorite_changes.append((resolved, favorite))
        if favorite:
            self.favorite_paths.add(resolved)
        else:
            self.favorite_paths.discard(resolved)

    def is_favorite(self, path: Path) -> bool:
        return path.resolve() in self.favorite_paths

    def list_favorites(self, limit: int = 100) -> list[FavoriteVideo]:
        return self.favorites[:limit]

    def list_resume_candidates(self, limit: int = 100) -> list[RecentVideo]:
        return self.resume_candidates[:limit]
```

Append the following tests:

```python
def test_favorites_menu_toggles_current_video_after_saving_progress(
    qtbot, tmp_path: Path
) -> None:
    movie = tmp_path / "episode.mp4"
    movie.write_bytes(b"video")
    store = FakeProgressStore()
    window = MainWindow(
        backend_factory=FakeBackend,
        progress_store=store,
        settings_path=tmp_path / "settings.json",
    )
    qtbot.addWidget(window)
    window._current_video = movie.resolve()
    window.backend.position_ms = 4_200

    window._refresh_favorites_menu()
    window.favorites_menu.actions()[0].trigger()

    assert store.saved[-1][1]["position_ms"] == 4_200
    assert store.favorite_changes[-1] == (movie.resolve(), True)
    window._refresh_favorites_menu()
    assert window.favorites_menu.actions()[0].text() == strings.REMOVE_VIDEO_FAVORITE
    window.favorites_menu.actions()[0].trigger()
    assert store.favorite_changes[-1] == (movie.resolve(), False)


def test_favorites_menu_lists_only_existing_supported_videos(
    qtbot, tmp_path: Path
) -> None:
    first = tmp_path / "first.mp4"
    unsupported = tmp_path / "notes.txt"
    missing = tmp_path / "missing.mkv"
    first.write_bytes(b"video")
    unsupported.write_text("notes", encoding="utf-8")
    store = FakeProgressStore()
    store.favorites = [
        FavoriteVideo(first, 1_000, "2026-07-25 10:00:03"),
        FavoriteVideo(missing, 2_000, "2026-07-25 10:00:02"),
        FavoriteVideo(unsupported, 3_000, "2026-07-25 10:00:01"),
    ]
    window = MainWindow(
        backend_factory=FakeBackend,
        progress_store=store,
        settings_path=tmp_path / "settings.json",
    )
    qtbot.addWidget(window)
    opened: list[Path] = []
    window.open_video = opened.append

    window._refresh_favorites_menu()
    actions = [
        action
        for action in window.favorites_menu.actions()
        if action.isEnabled() and not action.isSeparator()
    ]

    assert [action.text() for action in actions] == [first.name]
    assert actions[0].toolTip() == str(first)
    actions[0].trigger()
    assert opened == [first]


def test_favorites_menu_disables_toggle_without_current_video(
    qtbot, tmp_path: Path
) -> None:
    window = MainWindow(
        backend_factory=FakeBackend,
        progress_store=FakeProgressStore(),
        settings_path=tmp_path / "settings.json",
    )
    qtbot.addWidget(window)

    window._refresh_favorites_menu()

    first_action = window.favorites_menu.actions()[0]
    assert first_action.text() == strings.NO_VIDEO_TO_FAVORITE
    assert first_action.isEnabled() is False


def test_favorites_menu_reports_database_read_failure(
    qtbot, tmp_path: Path
) -> None:
    class BrokenFavoritesStore(FakeProgressStore):
        def list_favorites(self, limit: int = 100) -> list[FavoriteVideo]:
            raise sqlite3.OperationalError("database unavailable")

    window = MainWindow(
        backend_factory=FakeBackend,
        progress_store=BrokenFavoritesStore(),
        settings_path=tmp_path / "settings.json",
    )
    qtbot.addWidget(window)

    window._refresh_favorites_menu()

    assert "database unavailable" in window.status_label.text()
    assert window.favorites_menu.actions()[0].isEnabled() is False
```

- [ ] **Step 2: Run the menu tests and verify the UI API is missing**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/integration/test_main_window.py -q -k "favorites_menu"
```

Expected: failures report missing `favorites_menu`, `_refresh_favorites_menu`, and favorite-related strings.

- [ ] **Step 3: Add exact UI strings**

Add to `src/shadowing_player/ui/strings.py`:

```python
FAVORITES = "收藏夹"
NO_VIDEO_TO_FAVORITE = "尚未载入影片"
ADD_VIDEO_FAVORITE = "收藏目前影片"
REMOVE_VIDEO_FAVORITE = "取消收藏目前影片"
NO_VIDEO_FAVORITES = "收藏夹是空的"
VIDEO_FAVORITED = "已收藏影片：{name}"
VIDEO_UNFAVORITED = "已取消收藏影片：{name}"
VIDEO_FAVORITE_ERROR = "更新影片收藏失败：{message}"
```

- [ ] **Step 4: Implement the favorites button, menu, and toggle**

Import `sqlite3` in `src/shadowing_player/ui/main_window.py`.

After constructing `recent_button` and `recent_menu`, construct:

```python
        self.favorites_button = QPushButton(strings.FAVORITES, top_bar)
        self.favorites_button.setObjectName("favoritesButton")
        self.favorites_menu = QMenu(self.favorites_button)
        self.favorites_button.setMenu(self.favorites_menu)
```

Add it immediately after `recent_button` in the top layout:

```python
        top.addWidget(self.open_button)
        top.addWidget(self.recent_button)
        top.addWidget(self.favorites_button)
```

Connect refresh in `_connect_signals()`:

```python
        self.favorites_menu.aboutToShow.connect(self._refresh_favorites_menu)
```

Add these methods after `_show_recent_menu()`:

```python
    def _refresh_favorites_menu(self) -> None:
        self.favorites_menu.clear()
        current = self._current_video
        try:
            if (
                current is None
                or not current.is_file()
                or current.suffix.lower() not in {".mkv", ".mp4"}
            ):
                toggle_action = self.favorites_menu.addAction(
                    strings.NO_VIDEO_TO_FAVORITE
                )
                toggle_action.setEnabled(False)
            else:
                is_favorite = self._progress_store.is_favorite(current)
                toggle_action = self.favorites_menu.addAction(
                    strings.REMOVE_VIDEO_FAVORITE
                    if is_favorite
                    else strings.ADD_VIDEO_FAVORITE
                )
                toggle_action.triggered.connect(
                    self._toggle_current_video_favorite
                )

            self.favorites_menu.addSeparator()
            available = [
                item
                for item in self._progress_store.list_favorites(limit=100)
                if item.path.is_file()
                and item.path.suffix.lower() in {".mkv", ".mp4"}
            ]
        except sqlite3.Error as exc:
            self.favorites_menu.clear()
            error_action = self.favorites_menu.addAction(
                strings.VIDEO_FAVORITE_ERROR.format(message=exc)
            )
            error_action.setEnabled(False)
            self.status_label.setText(error_action.text())
            return
        if not available:
            empty_action = self.favorites_menu.addAction(
                strings.NO_VIDEO_FAVORITES
            )
            empty_action.setEnabled(False)
            return
        for item in available:
            action = self.favorites_menu.addAction(item.path.name)
            action.setToolTip(str(item.path))
            action.triggered.connect(
                lambda _checked=False, path=item.path: self.open_video(path)
            )

    def _toggle_current_video_favorite(self) -> None:
        video = self._current_video
        if (
            video is None
            or not video.is_file()
            or video.suffix.lower() not in {".mkv", ".mp4"}
        ):
            return
        try:
            self._save_current_progress()
            favorite = not self._progress_store.is_favorite(video)
            self._progress_store.set_favorite(video, favorite)
        except (OSError, sqlite3.Error) as exc:
            self.status_label.setText(
                strings.VIDEO_FAVORITE_ERROR.format(message=exc)
            )
            return
        self.status_label.setText(
            (
                strings.VIDEO_FAVORITED
                if favorite
                else strings.VIDEO_UNFAVORITED
            ).format(name=video.name)
        )
        self._refresh_favorites_menu()
```

- [ ] **Step 5: Run the favorites-menu tests and verify they pass**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/integration/test_main_window.py -q -k "favorites_menu"
```

Expected: all favorites-menu tests pass.

- [ ] **Step 6: Run existing main-window tests to catch integration regressions**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/integration/test_main_window.py -q
```

Expected: every main-window integration test passes.

- [ ] **Step 7: Commit the favorites UI**

```powershell
git add src/shadowing_player/ui/strings.py src/shadowing_player/ui/main_window.py tests/integration/test_main_window.py
git commit -m "feat: add video favorites menu"
```

### Task 4: Restore the Last Valid Video Paused at Startup

**Files:**

- Modify: `src/shadowing_player/ui/strings.py`
- Modify: `src/shadowing_player/ui/main_window.py`
- Modify: `tests/integration/test_main_window.py`

**Interfaces:**

- Consumes: `ProgressStore.list_resume_candidates()`, `ProgressStore.load()`, and `MainWindow.open_video(Path)`.
- Produces: `MainWindow._restore_last_session() -> None`, scheduled once with `QTimer.singleShot(0, ...)`.

- [ ] **Step 1: Write failing startup restoration tests**

Append to `tests/integration/test_main_window.py`:

```python
def test_startup_restores_last_existing_video_and_remains_paused(
    qtbot, tmp_path: Path
) -> None:
    missing = tmp_path / "missing.mp4"
    movie = tmp_path / "episode.mp4"
    movie.write_bytes(b"video")
    subtitle = tmp_path / "episode.srt"
    subtitle.touch()
    source = SubtitleSource.external(subtitle)
    store = FakeProgressStore(
        VideoProgress(
            3_200,
            0.75,
            PlaybackMode.SHADOWING,
            source.identifier,
        )
    )
    store.resume_candidates = [
        RecentVideo(missing, 8_000, "2026-07-25 10:00:02"),
        RecentVideo(movie, 3_200, "2026-07-25 10:00:01"),
    ]
    window = MainWindow(
        backend_factory=FakeBackend,
        subtitle_service=FakeSubtitleService(
            source,
            [Sentence(0, 1_000, 2_000, "Hello")],
        ),
        progress_store=store,
        settings_path=tmp_path / "settings.json",
    )
    qtbot.addWidget(window)

    qtbot.waitUntil(lambda: bool(window.backend.opened), timeout=1_000)

    assert window.backend.opened[-1] == str(movie.resolve())
    assert window.backend.seeks[-1] == 3_200
    assert window.backend.is_paused is True
    assert window._current_video == movie.resolve()


def test_startup_with_no_valid_video_stays_on_empty_screen(
    qtbot, tmp_path: Path
) -> None:
    store = FakeProgressStore()
    store.resume_candidates = [
        RecentVideo(
            tmp_path / "missing.mp4",
            3_200,
            "2026-07-25 10:00:01",
        )
    ]
    window = MainWindow(
        backend_factory=FakeBackend,
        progress_store=store,
        settings_path=tmp_path / "settings.json",
    )
    qtbot.addWidget(window)

    qtbot.wait(20)

    assert window.backend.opened == []
    assert window._current_video is None
    assert window.file_label.text() == strings.READY
```

- [ ] **Step 2: Run the startup tests and verify no automatic restore occurs**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/integration/test_main_window.py -q -k "startup_"
```

Expected: `test_startup_restores_last_existing_video_and_remains_paused` fails because the backend never opens a file.

- [ ] **Step 3: Add the startup error string**

Add to `src/shadowing_player/ui/strings.py`:

```python
STARTUP_RESTORE_ERROR = "无法恢复上次播放：{message}"
```

- [ ] **Step 4: Implement one-shot silent startup restoration**

At the end of `MainWindow.__init__()`, after the settings-warning handling, schedule:

```python
        QTimer.singleShot(0, self._restore_last_session)
```

Add this method before `_choose_video()`:

```python
    def _restore_last_session(self) -> None:
        if self._current_video is not None or self._close_pending:
            return
        try:
            candidates = self._progress_store.list_resume_candidates(limit=100)
            for item in candidates:
                path = item.path
                if (
                    not path.is_file()
                    or path.suffix.lower() not in {".mkv", ".mp4"}
                ):
                    continue
                # A changed file has no valid saved progress. Skipping it keeps
                # startup silent because open_video() plays brand-new files.
                if self._progress_store.load(path) is None:
                    continue
                self.open_video(path)
                return
        except Exception as exc:
            LOGGER.exception("恢复上次播放失败")
            self.status_label.setText(
                strings.STARTUP_RESTORE_ERROR.format(message=exc)
            )
```

The broad exception is deliberate at this one-shot application boundary: startup restore must never prevent manual use of the player, and the traceback is retained in the log.

- [ ] **Step 5: Run startup tests and verify paused restoration passes**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/integration/test_main_window.py -q -k "startup_"
```

Expected: both startup tests pass; the restored backend reports `is_paused is True`.

- [ ] **Step 6: Run the full main-window integration suite**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/integration/test_main_window.py -q
```

Expected: every main-window integration test passes without warnings or Qt timer exceptions.

- [ ] **Step 7: Commit startup restoration**

```powershell
git add src/shadowing_player/ui/strings.py src/shadowing_player/ui/main_window.py tests/integration/test_main_window.py
git commit -m "feat: restore last playback on startup"
```

### Task 5: Document and Verify the Complete Feature

**Files:**

- Modify: `README.md`
- Modify: `packaging/README.txt`

**Interfaces:**

- Consumes: completed favorites and startup restore behavior.
- Produces: user-facing usage instructions and fresh verification evidence.

- [ ] **Step 1: Update source-build documentation**

In the README feature list, add:

```markdown
- 顶部“收藏夹”可收藏当前影片并快速重新打开；收藏影片会持续记录最新播放进度。
- 启动时自动恢复最后一部仍存在的影片与播放进度，并保持暂停等待播放。
```

Update the data-storage sentence to state that video favorites are stored in the same SQLite database:

```markdown
全局设置保存在 `%LOCALAPPDATA%\ShadowingPlayer\settings.json`，播放进度与影片收藏保存在 `%LOCALAPPDATA%\ShadowingPlayer\data.sqlite`。
```

- [ ] **Step 2: Update packaged-app documentation**

After the existing “最近观看” sentence in `packaging/README.txt`, add:

```text
顶部“收藏夹”可收藏当前影片并快速重新打开，收藏影片会持续记录最新
播放进度。再次启动播放器时，会恢复最后一部仍存在的影片与进度，并
保持暂停，等待按播放。
```

- [ ] **Step 3: Run the complete automated test suite**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Expected: all unit and integration tests pass with zero failures.

- [ ] **Step 4: Run source compilation verification**

Run:

```powershell
.\.venv\Scripts\python.exe -m compileall -q src tests
```

Expected: exit code 0 with no output.

- [ ] **Step 5: Build and validate the Windows folder package**

Run:

```powershell
powershell -ExecutionPolicy Bypass -File packaging\build_windows.ps1
```

Expected: exit code 0, `dist\ShadowingPlayer\ShadowingPlayer.exe` exists, and the script prints `Package complete`.

- [ ] **Step 6: Run the packaged smoke test**

Run:

```powershell
.\dist\ShadowingPlayer\ShadowingPlayer.exe --smoke-test
```

Expected: the packaged app starts and exits automatically without an error dialog or nonzero exit code.

- [ ] **Step 7: Review the final diff against the approved specification**

Run:

```powershell
git diff bf6fe95 --check
git status --short
```

Confirm:

- schema 2 preserves all version-1 data;
- favorites have no duplicate progress store;
- toggling a favorite saves current progress first;
- startup skips invalid or changed files and remains paused;
- missing favorites are hidden, not deleted;
- sentence-star behavior is unchanged;
- no unrelated files are modified.

- [ ] **Step 8: Commit documentation**

```powershell
git add README.md packaging/README.txt
git commit -m "docs: explain video favorites and startup resume"
```
