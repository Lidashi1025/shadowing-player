# 便携启动身份与易用性迭代 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复便携 EXE 的 Windows 任务栏身份链，并加入桌面快捷方式、拖放开片、时间/句数信息和工具菜单。

**Architecture:** 单进程便携程序恢复使用 Windows 系统定义身份，Qt 与 EXE 继续负责窗口和文件图标。Windows 快捷方式创建隔离在运行时服务中；主窗口只调用服务并展示结果。拖放与信息标签复用现有 `open_video` 和播放器信号。

**Tech Stack:** Python 3.14、PySide6 6.11.1、Windows PowerShell/WScript.Shell、pytest/pytest-qt、PyInstaller 6.21。

## Global Constraints

- 保留第一、二版全部功能与简体中文界面。
- 不实现录音、孩童模式、统计、每日目标或 AI 发音评分。
- 不修改 SQLite 结构。
- 不自动固定或删除 Windows 任务栏项目。
- 文件夹移动后可重新创建快捷方式。

---

### Task 1: 系统定义任务栏身份与桌面快捷方式

**Files:**
- Modify: `src/shadowing_player/runtime/app_identity.py`
- Modify: `src/shadowing_player/app.py`
- Create: `src/shadowing_player/runtime/windows_shortcut.py`
- Modify: `tests/unit/test_app_identity.py`
- Create: `tests/unit/test_windows_shortcut.py`

**Interfaces:**
- Produces: `create_desktop_shortcut(executable: Path | None = None, runner=subprocess.run) -> Path`
- Retains: `apply_application_identity(application) -> Path`

- [ ] **Step 1: Write failing tests**

```python
def test_app_identity_has_no_explicit_process_app_id():
    assert not hasattr(app_identity, "set_windows_app_user_model_id")

def test_create_desktop_shortcut_passes_target_and_icon_to_powershell(tmp_path):
    calls = []
    result = create_desktop_shortcut(tmp_path / "ShadowingPlayer.exe", runner=calls.append)
    assert result.name == "儿童影子跟读播放器.lnk"
```

- [ ] **Step 2: Run focused tests**

Run: `.venv\Scripts\python.exe -m pytest tests/unit/test_app_identity.py tests/unit/test_windows_shortcut.py -q`

Expected: FAIL because the explicit AppID API still exists and shortcut module is missing.

- [ ] **Step 3: Implement minimal identity and shortcut changes**

Remove the explicit AppID setter and its call from `app.py`. Implement shortcut creation with environment variables passed to a non-interactive PowerShell command so file paths never need string interpolation.

- [ ] **Step 4: Run focused tests**

Run: `.venv\Scripts\python.exe -m pytest tests/unit/test_app_identity.py tests/unit/test_windows_shortcut.py tests/unit/test_app.py -q`

Expected: PASS.

### Task 2: Drag-and-drop video loading

**Files:**
- Modify: `src/shadowing_player/ui/main_window.py`
- Modify: `tests/integration/test_main_window.py`

**Interfaces:**
- Produces: `MainWindow.dragEnterEvent(event)`
- Produces: `MainWindow.dropEvent(event)`
- Consumes: existing `open_video(Path)`

- [ ] **Step 1: Write failing drag tests**

Create `QMimeData`/`QUrl` events for one `.mp4` and one `.txt`. Assert MP4 is accepted and calls `open_video`; TXT remains ignored.

- [ ] **Step 2: Run tests and confirm failure**

Run: `.venv\Scripts\python.exe -m pytest tests/integration/test_main_window.py -k drag -q`

Expected: FAIL because the window does not accept drops.

- [ ] **Step 3: Implement format validation and event handlers**

Add `_dropped_video_path(mime_data) -> Path | None` and accept only one local `.mkv`/`.mp4` file.

- [ ] **Step 4: Run drag tests**

Run: `.venv\Scripts\python.exe -m pytest tests/integration/test_main_window.py -k drag -q`

Expected: PASS.

### Task 3: Time, duration and sentence position

**Files:**
- Modify: `src/shadowing_player/ui/main_window.py`
- Modify: `src/shadowing_player/ui/theme.py`
- Modify: `tests/integration/test_main_window.py`

**Interfaces:**
- Produces: `_format_time(milliseconds: int) -> str`
- Produces widgets: `position_label`, `sentence_counter_label`, `duration_label`

- [ ] **Step 1: Write failing format and signal tests**

Assert `0 -> "00:00"`, `65_000 -> "01:05"`, `3_665_000 -> "1:01:05"`. Emit duration/position/current-sentence signals and assert the three labels update.

- [ ] **Step 2: Run focused tests**

Run: `.venv\Scripts\python.exe -m pytest tests/integration/test_main_window.py -k "time or counter" -q`

Expected: FAIL because labels and formatter are missing.

- [ ] **Step 3: Add the metadata row and signal updates**

Place the row under `SentenceProgressBar`; update it only from existing signal handlers and sentence application.

- [ ] **Step 4: Run focused and full integration tests**

Run: `.venv\Scripts\python.exe -m pytest tests/integration/test_main_window.py -q`

Expected: PASS.

### Task 4: Tools menu

**Files:**
- Modify: `src/shadowing_player/ui/main_window.py`
- Modify: `src/shadowing_player/ui/theme.py`
- Modify: `src/shadowing_player/ui/strings.py`
- Modify: `tests/integration/test_main_window.py`

**Interfaces:**
- Produces: `tools_button`, `tools_menu`
- Produces actions: `create_shortcut_action`, `open_data_action`, `shortcut_help_action`

- [ ] **Step 1: Write a failing menu test**

Assert all three actions exist with simplified-Chinese text and the shortcut help text contains the current `settings.shortcuts` values.

- [ ] **Step 2: Run focused test**

Run: `.venv\Scripts\python.exe -m pytest tests/integration/test_main_window.py -k tools_menu -q`

Expected: FAIL because the tools menu does not exist.

- [ ] **Step 3: Implement actions and dark menu style**

Call `create_desktop_shortcut`, open the data directory with `QDesktopServices`, and render shortcut mappings in a `QMessageBox`.

- [ ] **Step 4: Run integration and full tests**

Run: `.venv\Scripts\python.exe -m pytest tests/integration/test_main_window.py -q`

Run: `.venv\Scripts\python.exe -m pytest -q`

Expected: PASS.

### Task 5: Build, desktop shortcut and frozen verification

**Files:**
- Output: `dist/ShadowingPlayer/`
- Output: current Windows desktop `儿童影子跟读播放器.lnk`

**Interfaces:**
- Produces the rebuilt folder distribution and desktop shortcut.

- [ ] **Step 1: Compile and check dependencies**

Run: `.venv\Scripts\python.exe -m compileall -q src tests`

Run: `.venv\Scripts\python.exe -m pip check`

Expected: exit 0 and no broken requirements.

- [ ] **Step 2: Build**

Run: `powershell -NoProfile -ExecutionPolicy Bypass -File packaging\build_windows.ps1`

Expected: exit 0.

- [ ] **Step 3: Run frozen smoke test**

Start `dist/ShadowingPlayer/ShadowingPlayer.exe --smoke-test` with a fresh `LOCALAPPDATA` and assert exit code 0.

- [ ] **Step 4: Create and inspect desktop shortcut**

Call `create_desktop_shortcut()` using the rebuilt EXE. Read the resulting `.lnk` through WScript.Shell and assert target, working directory and icon location reference `dist\ShadowingPlayer\ShadowingPlayer.exe`.

- [ ] **Step 5: Run final complete tests**

Run: `.venv\Scripts\python.exe -m pytest -q`

Expected: all tests pass.
