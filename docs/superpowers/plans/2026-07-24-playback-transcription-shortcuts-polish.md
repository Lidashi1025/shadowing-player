# Playback, Transcription, and Shortcut Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Repair sentence-state visuals and replay, make transcription unobtrusively portable, add an editable shortcut system, and publish the verified source to GitHub.

**Architecture:** Keep playback decisions in `SessionController`, sentence presentation in a focused model/delegate pair, and portable path resolution in runtime helpers. Replace the progress dialog with an embedded activity strip driven by the existing worker signals. Use one shortcut catalog for defaults, registration, and the editor dialog.

**Tech Stack:** Python 3.14, PySide6, SQLite, python-mpv, faster-whisper small CPU int8, pytest/pytest-qt, PyInstaller, Git/GitHub CLI

## Global Constraints

- Interface text remains Simplified Chinese.
- Support MKV and MP4.
- Preserve progress, favorites, edited sentences, and existing transcription cache.
- Do not add recording, child mode, or statistics.
- Keep faster-whisper small, CPU, int8, English, VAD, word timestamps, and beam 5.
- Do not commit DLLs, models, caches, build products, videos, or benchmark audio.
- Publish to a private GitHub repository unless the user explicitly changes visibility.

---

### Task 1: Sentence State and Visible Favorites

**Files:**
- Create: `src/shadowing_player/ui/sentence_item_delegate.py`
- Modify: `src/shadowing_player/ui/sentence_table_model.py`
- Modify: `src/shadowing_player/ui/main_window.py`
- Modify: `src/shadowing_player/ui/theme.py`
- Modify: `tests/unit/test_sentence_table_model.py`
- Modify: `tests/integration/test_main_window.py`

**Interfaces:**
- Produces: `SentenceTableModel.CurrentRole`
- Produces: `SentenceTableModel.set_current_row(row: int) -> None`
- Produces: `SentenceTableModel.toggle_star(row: int) -> None`
- Produces: `SentenceItemDelegate` that removes cell focus and draws one current-row bar

- [ ] **Step 1: Write failing model tests**

```python
model.set_sentences([Sentence(0, 0, 1000, "Hello")])
assert model.data(model.index(0, 1), Qt.DisplayRole) == "☆"
model.toggle_star(0)
assert model.data(model.index(0, 1), Qt.DisplayRole) == "★"
model.set_current_row(0)
assert model.data(model.index(0, 0), model.CurrentRole) is True
```

- [ ] **Step 2: Run the tests and verify the current star/check-state implementation fails**

```powershell
.venv\Scripts\python.exe -m pytest tests/unit/test_sentence_table_model.py -q
```

- [ ] **Step 3: Implement the text/star columns and current role**

Column 0 returns sentence text; column 1 returns `☆` or `★`. `toggle_star()` replaces the
sentence, emits data changes, and emits `starred_changed`.

- [ ] **Step 4: Write failing Qt click and state tests**

Assert clicking column 1 persists a star without seeking; clicking column 0 seeks; position
updates do not call `setCurrentIndex`; and the star column is at the right edge.

- [ ] **Step 5: Implement the delegate and table wiring**

Install the delegate, set the star column to 44px, stretch the text column, route clicks by
column, and update `set_current_row()` from `_current_sentence_changed()`.

- [ ] **Step 6: Run focused tests**

```powershell
.venv\Scripts\python.exe -m pytest tests/unit/test_sentence_table_model.py tests/integration/test_main_window.py -q
```

### Task 2: Reliable Replay

**Files:**
- Modify: `src/shadowing_player/playback/session_controller.py`
- Modify: `tests/unit/test_session_controller.py`
- Modify: `tests/integration/test_main_window.py`

**Interfaces:**
- Produces: `repeat_current()` that seeks before playback in every mode

- [ ] **Step 1: Write failing watch and shadow replay tests**

```python
controller.set_mode(PlaybackMode.WATCH)
controller.select_sentence(1, autoplay=False)
player.seeks.clear()
controller.repeat_current()
assert player.seeks == [2750]
assert player.play_count == 1
```

- [ ] **Step 2: Confirm the tests fail because replay only calls `play()`**

```powershell
.venv\Scripts\python.exe -m pytest tests/unit/test_session_controller.py -q
```

- [ ] **Step 3: Implement replay through the current sentence**

For continuous modes seek to the padded sentence start and play. For sentence modes call
the existing iteration start.

- [ ] **Step 4: Add and pass a single-left-arrow integration test**

Invoke `_left_pressed()` once with a current sentence and assert the backend seek.

### Task 3: Portable Transcription Cache

**Files:**
- Modify: `src/shadowing_player/runtime/bundle_paths.py`
- Modify: `src/shadowing_player/transcription/service.py`
- Modify: `src/shadowing_player/ui/main_window.py`
- Modify: `.gitignore`
- Modify: `tests/unit/test_bundle_paths.py`
- Modify: `tests/unit/test_transcription_service.py`

**Interfaces:**
- Produces: `transcription_cache_dir() -> Path`
- Extends: `TranscriptionService(..., fallback_cache_dirs: tuple[Path, ...] = ())`
- Produces: cache lookup that promotes a legacy SRT into the portable directory

- [ ] **Step 1: Write failing path tests**

Assert source mode returns `<project>/cache/transcriptions` and frozen mode returns
`<executable>/cache/transcriptions`.

- [ ] **Step 2: Write failing legacy-cache promotion tests**

Place an SRT at a fallback hash path, call `transcribe()`, and assert it appears in the
primary path without model loading.

- [ ] **Step 3: Implement portable paths and promotion**

Resolve the primary path from `executable_dir()`, create it only when writing, use atomic
copy/replace for legacy cache, and add `/cache/` to `.gitignore`.

- [ ] **Step 4: Run path and service tests**

```powershell
.venv\Scripts\python.exe -m pytest tests/unit/test_bundle_paths.py tests/unit/test_transcription_service.py -q
```

### Task 4: Embedded Background Activity Strip

**Files:**
- Create: `src/shadowing_player/ui/transcription_status_bar.py`
- Modify: `src/shadowing_player/ui/main_window.py`
- Modify: `src/shadowing_player/ui/theme.py`
- Modify: `src/shadowing_player/ui/strings.py`
- Modify: `tests/integration/test_main_window.py`

**Interfaces:**
- Produces: `TranscriptionStatusBar.set_phase(phase: str)`, `set_progress(value: int)`, `reset()`
- Emits: `cancel_requested`
- Consumes: existing `TranscriptionWorker` signals

- [ ] **Step 1: Write failing status-bar tests**

Assert it is hidden initially, displays percent and ETA after progress, emits cancel, and
resets after completion.

- [ ] **Step 2: Write failing non-blocking open test**

Open a no-subtitle video with a controllable worker and assert the backend is not paused,
the embedded bar is visible, no `QProgressDialog` exists, and speed/play controls work.

- [ ] **Step 3: Implement the status bar**

Use `QFrame`, `QLabel`, `QProgressBar`, and a compact cancel button. Use `time.monotonic()`
to calculate elapsed time and ETA after nonzero progress.

- [ ] **Step 4: Replace dialog wiring**

Connect worker phase/progress to the embedded bar, remove all `QProgressDialog` state, do
not pause on transcription start, and hide/reset on every terminal path.

- [ ] **Step 5: Preserve playback position on completion**

Load generated sentences without reopening the file or calling `_finish_open()` a second
time. Select the sentence containing the backend's current position without seeking.

- [ ] **Step 6: Run the full Qt integration file**

```powershell
.venv\Scripts\python.exe -m pytest tests/integration/test_main_window.py -q
```

### Task 5: Editable Shortcut System

**Files:**
- Create: `src/shadowing_player/shortcut_catalog.py`
- Create: `src/shadowing_player/ui/shortcut_dialog.py`
- Modify: `src/shadowing_player/storage/settings.py`
- Modify: `src/shadowing_player/ui/main_window.py`
- Modify: `src/shadowing_player/ui/theme.py`
- Modify: `src/shadowing_player/ui/strings.py`
- Create: `tests/unit/test_shortcut_catalog.py`
- Create: `tests/integration/test_shortcut_dialog.py`
- Modify: `tests/integration/test_main_window.py`

**Interfaces:**
- Produces: `ShortcutDefinition(key, category, label, description, default)`
- Produces: `SHORTCUT_DEFINITIONS`
- Produces: `find_conflicts(bindings: dict[str, str]) -> set[str]`
- Produces: `ShortcutDialog.edit(parent, bindings) -> dict[str, str] | None`
- Produces: `_rebuild_shortcuts(bindings)` in `MainWindow`

- [ ] **Step 1: Write failing catalog tests**

Assert every key is unique, every default is parseable, required actions are present, and
duplicate sequences are returned by `find_conflicts()`.

- [ ] **Step 2: Implement the central catalog**

Add all defaults approved in the design. Make `settings.default_shortcuts()` derive from
the catalog so old files automatically receive new keys.

- [ ] **Step 3: Write failing dialog tests**

Assert all definitions render, conflicts disable Save and show an error, Restore Defaults
fills catalog values, and a valid edit returns normalized portable key strings.

- [ ] **Step 4: Implement the dark categorized dialog**

Use `QDialog`, section headings, `QKeySequenceEdit`, inline conflict text, and
Save/Restore/Cancel buttons. Keep the dialog within 720px height using a scroll area.

- [ ] **Step 5: Replace the old message box and support live rebind**

Map every catalog key to its handler, including open, recent, previous, star, review, and
F1. Destroy old `QShortcut` objects before rebuilding and save immediately after edits.

- [ ] **Step 6: Run shortcut and settings tests**

```powershell
.venv\Scripts\python.exe -m pytest tests/unit/test_settings.py tests/unit/test_shortcut_catalog.py tests/integration/test_shortcut_dialog.py tests/integration/test_main_window.py -q
```

### Task 6: Text Clipping and Visual Regression

**Files:**
- Modify: `src/shadowing_player/ui/main_window.py`
- Modify: `src/shadowing_player/ui/theme.py`
- Modify: `tests/integration/test_main_window.py`

**Interfaces:**
- Produces: controls whose font metrics fit their content at 1024px

- [ ] **Step 1: Add a failing checkbox width test**

Measure `auto_advance_check.fontMetrics().horizontalAdvance(text)` plus indicator, spacing,
padding, and borders; assert it is no greater than the widget width.

- [ ] **Step 2: Replace the unsafe fixed width**

Use `sizeHint()` plus a small safety margin and retain compact horizontal spacing.

- [ ] **Step 3: Render a 1024x680 screenshot**

Use the existing Qt preview fixture, inspect one current row, one starred row, the
transcription strip, and the shortcut dialog. Confirm no double blue line or clipped text.

- [ ] **Step 4: Run integration tests**

```powershell
.venv\Scripts\python.exe -m pytest tests/integration -q
```

### Task 7: Verification, Packaging, and GitHub Publication

**Files:**
- Modify: `README.md`
- Modify: `packaging/README.txt`
- Modify: `.gitignore`

**Interfaces:**
- Produces: refreshed folder distribution, desktop shortcut, private GitHub repository

- [ ] **Step 1: Update user documentation**

Document portable cache, background activity strip, star behavior, replay, and the editable
shortcut panel.

- [ ] **Step 2: Run complete verification**

```powershell
.venv\Scripts\python.exe -m compileall -q src tests
.venv\Scripts\python.exe -m pip check
.venv\Scripts\python.exe -m pytest -q
```

- [ ] **Step 3: Rebuild and smoke-test**

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File packaging\build_windows.ps1
dist\ShadowingPlayer\ShadowingPlayer.exe --smoke-test
```

- [ ] **Step 4: Refresh and launch the desktop shortcut**

Verify the target, working directory, icon, clean close, and zero remaining processes.

- [ ] **Step 5: Initialize Git safely**

Confirm `.gitignore` excludes `.venv`, DLLs, models, cache, build, dist, media, database,
and settings. Initialize `main`, inspect all staged files, and commit only source scope.

- [ ] **Step 6: Authenticate and publish**

Require successful `gh auth status`. Create a private `shadowing-player` repository, add
origin, push `main`, and report the repository URL and commit SHA. If the name exists, use
`shadowing-player-desktop` without changing visibility.
