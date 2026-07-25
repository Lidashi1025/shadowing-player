# Click Video to Toggle Playback Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Toggle the existing playback action when the user left-clicks the video surface.

**Architecture:** Add a focused `ClickableVideoWidget` that emits a signal for valid clicks, then connect it to `MainWindow._toggle_if_available()`. Preserve the QWidget native-window attributes required by libmpv.

**Tech Stack:** Python, PySide6, pytest, pytest-qt.

## Global Constraints

- Reuse existing playback and blank-countdown behavior.
- Ignore clicks before a video is loaded.
- Ignore right-clicks and mouse drags.
- Do not add shortcuts or dependencies.

---

### Task 1: Clickable Video Widget

**Files:**

- Create: `src/shadowing_player/ui/clickable_video_widget.py`
- Create: `tests/unit/test_clickable_video_widget.py`

**Interfaces:**

- Produces: `ClickableVideoWidget.clicked`.

- [ ] Write tests proving left-click emits once while right-click and drag do not.
- [ ] Run the tests and confirm import failure.
- [ ] Implement press/release tracking with `QApplication.startDragDistance()`.
- [ ] Run the focused tests and confirm they pass.

### Task 2: Main Window Wiring

**Files:**

- Modify: `src/shadowing_player/ui/main_window.py`
- Modify: `tests/integration/test_main_window.py`

**Interfaces:**

- Consumes: `ClickableVideoWidget.clicked`.
- Produces: click-to-toggle through `_toggle_if_available()`.

- [ ] Add integration tests for loaded and unloaded video states.
- [ ] Run tests and confirm clicks do not yet toggle.
- [ ] Replace the render widget class and connect its signal.
- [ ] Run focused and complete main-window tests.

### Task 3: Verification

- [ ] Run `python -m pytest -q`.
- [ ] Run `python -m compileall -q src tests`.
- [ ] Build with `packaging/build_windows.ps1`.
- [ ] Run the frozen executable with `--smoke-test`.
- [ ] Confirm a clean Git worktree.
