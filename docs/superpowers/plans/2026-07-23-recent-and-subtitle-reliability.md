# Recent Viewing and Subtitle Reliability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an eight-item recent-video menu and make sentence language roles and click-to-seek behavior reliable.

**Architecture:** Reuse the existing `videos.updated_at` column through focused `ProgressStore` query methods. Keep source-language resolution inside `SubtitleService`, orchestrate Chinese-only transcription in `MainWindow`, and fix seeking at the playback-controller boundary so every UI navigation path behaves consistently.

**Tech Stack:** Python 3.14, PySide6, SQLite, pytest/pytest-qt, python-mpv, faster-whisper

## Global Constraints

- Interface text remains Simplified Chinese.
- Support MKV and MP4.
- Preserve progress, favorites, and edited sentences.
- Do not add recording, child mode, or statistics.
- Use the bundled faster-whisper small CPU int8 model for missing English subtitles.

---

### Task 1: Sentence Navigation Seek

**Files:**
- Modify: `tests/unit/test_session_controller.py`
- Modify: `tests/integration/test_main_window.py`
- Modify: `src/shadowing_player/playback/session_controller.py`
- Modify: `src/shadowing_player/ui/main_window.py`

**Interfaces:**
- Consumes: `Sentence.play_window(video_duration_ms) -> tuple[int, int]`
- Produces: `SessionController.select_sentence(index: int, autoplay: bool)` that seeks in every playback mode

- [ ] **Step 1: Write failing controller and UI-click tests**

```python
def test_watch_mode_selection_seeks_then_plays():
    controller, player, _timer = make_controller()
    controller.set_mode(PlaybackMode.WATCH)
    controller.select_sentence(1, autoplay=True)
    assert player.seeks == [2_750]
    assert player.play_count == 1
```

Add a pytest-qt test clicking the center of column 1 and assert the fake backend seeks to
the selected sentence's padded start.

- [ ] **Step 2: Run the focused tests and confirm they fail because `seeks` is empty**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests/unit/test_session_controller.py tests/integration/test_main_window.py -q
```

- [ ] **Step 3: Implement one seek before continuous playback**

In `select_sentence`, route watching and shadowing autoplay through a small helper that
seeks to the current sentence start and then calls `play()`. Keep practice and loop modes
using `_start_iteration()` so they seek exactly once.

- [ ] **Step 4: Run the focused tests and confirm they pass**

Run the command from Step 2.

### Task 2: Reliable English and Chinese Source Roles

**Files:**
- Modify: `tests/unit/test_subtitle_service.py`
- Modify: `tests/integration/test_main_window.py`
- Modify: `src/shadowing_player/subtitles/subtitle_service.py`
- Modify: `src/shadowing_player/ui/main_window.py`

**Interfaces:**
- Consumes: `SubtitleService.choose_language_sources(sources)`
- Produces: `(english_source | None, chinese_source | None)` where both roles never refer to the same source
- Produces: Chinese-only orchestration that carries the Chinese source through transcription completion

- [ ] **Step 1: Write failing source-role tests**

```python
def test_only_chinese_source_does_not_become_english(tmp_path):
    source = SubtitleSource(..., language="zh")
    assert service.choose_language_sources([source]) == (None, source)
```

Also preserve the existing two-untagged-embedded-tracks expectation: first is English and
second is Chinese.

- [ ] **Step 2: Confirm the source-role test fails with English equal to the Chinese source**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests/unit/test_subtitle_service.py -q
```

- [ ] **Step 3: Implement explicit role resolution**

Select tagged English and Chinese first. Use the first unknown source only when English is
missing. Use the second suitable embedded source as the Chinese fallback. Never assign a
known Chinese source to English.

- [ ] **Step 4: Write failing Chinese-only integration tests**

Test that a Chinese-only source starts background English transcription, completion calls
`load_bilingual_sentences(generated_english, original_chinese)`, and an existing English
cache loads without prompting.

- [ ] **Step 5: Confirm the integration tests fail because Chinese currently loads as primary**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests/integration/test_main_window.py -q
```

- [ ] **Step 6: Carry the Chinese companion through transcription**

Store `_pending_chinese_source`. For Chinese-only input, automatically start transcription.
On completion populate the source menu without losing discovered sources and call
`_load_subtitle_source(generated_source, pending_chinese_source)`. Clear pending state on
completion, cancellation, failure, and new video.

- [ ] **Step 7: Confirm English and bilingual UI tests pass**

Run the command from Step 5.

### Task 3: Recent Viewing Store and Menu

**Files:**
- Modify: `tests/unit/test_progress_store.py`
- Modify: `tests/integration/test_main_window.py`
- Modify: `src/shadowing_player/storage/progress_store.py`
- Modify: `src/shadowing_player/ui/main_window.py`
- Modify: `src/shadowing_player/ui/strings.py`
- Modify: `src/shadowing_player/ui/theme.py`

**Interfaces:**
- Produces: `RecentVideo(path: Path, position_ms: int, updated_at: str)`
- Produces: `ProgressStore.mark_opened(video_path: Path) -> None`
- Produces: `ProgressStore.list_recent(limit: int = 8) -> list[RecentVideo]`

- [ ] **Step 1: Write failing store tests**

Create three files, save progress for one, call `mark_opened()` in a different order, and
assert `list_recent()` returns newest first without changing saved position.

- [ ] **Step 2: Confirm tests fail because the store methods do not exist**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests/unit/test_progress_store.py -q
```

- [ ] **Step 3: Implement store queries without a migration**

Insert a new video with its fingerprint and update only `updated_at` on conflict. Query
`path`, `last_position_ms`, and `updated_at` ordered descending with a parameterized limit.

- [ ] **Step 4: Write failing recent-menu integration tests**

Give the fake store two existing paths and one missing path. Open the menu, assert only the
existing two appear, and trigger an action to assert `open_video(path)` is called.

- [ ] **Step 5: Confirm the menu test fails because the recent button is absent**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests/integration/test_main_window.py -q
```

- [ ] **Step 6: Implement the compact recent menu**

Add a `QPushButton("最近观看")` beside “打开视频”, attach a `QMenu`, rebuild it on
`aboutToShow`, show at most eight existing videos, use full paths as tooltips, and call
`open_video()` from each action. Call `mark_opened()` after loading old progress.

- [ ] **Step 7: Run unit and integration tests**

```powershell
.venv\Scripts\python.exe -m pytest tests/unit/test_progress_store.py tests/integration/test_main_window.py -q
```

### Task 4: Regression, Documentation, and Portable Build

**Files:**
- Modify: `README.md`
- Modify: `packaging/README.txt`

**Interfaces:**
- Consumes: all previous tasks
- Produces: refreshed `dist/ShadowingPlayer` folder and desktop shortcut

- [ ] **Step 1: Document recent viewing and Chinese-only English generation**

Describe the “最近观看” menu, click-to-seek behavior, and automatic English generation when
only Chinese subtitles exist.

- [ ] **Step 2: Run the full verification suite**

```powershell
.venv\Scripts\python.exe -m compileall -q src tests
.venv\Scripts\python.exe -m pip check
.venv\Scripts\python.exe -m pytest -q
```

- [ ] **Step 3: Build the folder distribution**

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File packaging\build_windows.ps1
```

- [ ] **Step 4: Verify portable contents and frozen startup**

Confirm the EXE, icon, libmpv, ffmpeg, ffprobe, model, and README exist. Run:

```powershell
dist\ShadowingPlayer\ShadowingPlayer.exe --smoke-test
```

Expected exit code: `0`.

- [ ] **Step 5: Refresh the desktop shortcut**

Call `create_desktop_shortcut()` with the packaged EXE and verify its target,
working directory, and icon location.
