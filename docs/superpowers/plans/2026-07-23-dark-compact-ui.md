# 暗色紧凑界面与 Windows 图标 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将现有 PySide6 播放器重排为暗色紧凑双栏界面，保留所有功能，并让源码版和文件夹版 EXE 在 Windows 任务栏显示应用图标。

**Architecture:** 业务逻辑与控件属性留在 `MainWindow`，视觉 token/QSS 抽到独立主题模块。Windows 进程身份与运行时图标路径由独立运行时模块管理，`app.py` 只负责按正确顺序调用；PyInstaller 同时嵌入 EXE 图标并携带可由 Qt 读取的 ICO。

**Tech Stack:** Python 3.14、PySide6、pytest/pytest-qt、PyInstaller 6.21、Windows Shell API。

## Global Constraints

- 保留当前所有按钮、组合框、快捷键和功能，不删除或隐藏入口。
- 界面文字继续使用简体中文。
- 只做布局、视觉主题和 Windows 图标修复，不实现录音、孩童模式、统计或设置页。
- 不改变数据库结构、设置 JSON 格式和播放状态机。
- 文件夹版继续携带 faster-whisper small、libmpv、ffmpeg 与 ffprobe。

---

### Task 1: Windows 应用身份与图标路径

**Files:**
- Create: `src/shadowing_player/runtime/app_identity.py`
- Modify: `src/shadowing_player/app.py`
- Modify: `packaging/ShadowingPlayer.spec`
- Test: `tests/unit/test_app_identity.py`
- Test: `tests/unit/test_app.py`

**Interfaces:**
- Produces: `application_icon_path() -> Path`
- Produces: `set_windows_app_user_model_id(app_id: str = APP_USER_MODEL_ID) -> bool`
- Produces: `apply_application_identity(application: QApplication) -> Path`

- [ ] **Step 1: Write failing path and AppUserModelID tests**

```python
def test_application_icon_path_uses_source_assets(monkeypatch, tmp_path):
    monkeypatch.setattr(app_identity, "is_frozen", lambda: False)
    monkeypatch.setattr(app_identity, "project_root", lambda: tmp_path)
    assert app_identity.application_icon_path() == tmp_path / "assets" / "app-icon.ico"

def test_set_windows_app_id_calls_shell_api(monkeypatch):
    calls = []
    monkeypatch.setattr(app_identity.sys, "platform", "win32")
    monkeypatch.setattr(app_identity, "_set_current_process_app_id", calls.append)
    assert app_identity.set_windows_app_user_model_id("ShadowingPlayer.Test")
    assert calls == ["ShadowingPlayer.Test"]
```

- [ ] **Step 2: Run tests and confirm imports fail**

Run: `python -m pytest tests/unit/test_app_identity.py -q`

Expected: FAIL because `shadowing_player.runtime.app_identity` does not exist.

- [ ] **Step 3: Implement identity module and app initialization**

Implement source/frozen icon resolution with existing `bundle_paths` helpers. Call the Windows Shell API only on `win32`, then set application name, organization name and global QIcon before creating `MainWindow`.

- [ ] **Step 4: Include the runtime ICO in PyInstaller data**

Add:

```python
datas = [
    (str(project_root / "assets" / "app-icon.ico"), "assets"),
]
```

Keep the existing `EXE(icon=...)` setting.

- [ ] **Step 5: Run focused tests**

Run: `python -m pytest tests/unit/test_app_identity.py tests/unit/test_app.py -q`

Expected: PASS.

### Task 2: Theme module and compact main-window layout

**Files:**
- Create: `src/shadowing_player/ui/theme.py`
- Modify: `src/shadowing_player/ui/main_window.py`
- Test: `tests/integration/test_main_window.py`

**Interfaces:**
- Produces: `DARK_STYLESHEET: str`
- Produces: `apply_dark_theme(window: QWidget) -> None`
- `MainWindow` retains the existing named widgets such as `open_button`, `play_button`, `merge_button`, `subtitle_combo`, `mode_combo`, and `status_label`.

- [ ] **Step 1: Add failing layout-preservation tests**

```python
def test_compact_dark_layout_keeps_all_existing_controls(qtbot, tmp_path):
    window = make_window(tmp_path)
    qtbot.addWidget(window)
    assert window.objectName() == "mainWindow"
    assert window.play_button.objectName() == "primaryPlayButton"
    assert window.sentence_panel.objectName() == "sentencePanel"
    for widget in (
        window.previous_button, window.repeat_button, window.next_button,
        window.merge_button, window.split_button, window.review_button,
        window.subtitle_combo, window.subtitle_mode_combo, window.mode_combo,
        window.plays_combo, window.speed_combo, window.blank_combo,
        window.loop_combo, window.auto_advance_check,
    ):
        assert window.centralWidget().isAncestorOf(widget)
```

- [ ] **Step 2: Run the focused test and confirm missing object names/panel**

Run: `python -m pytest tests/integration/test_main_window.py::test_compact_dark_layout_keeps_all_existing_controls -q`

Expected: FAIL because the new panel and object names do not exist.

- [ ] **Step 3: Add theme tokens and global QSS**

Create a focused QSS module with application background, panel borders, buttons, primary playback button, combo boxes, checkbox, splitter, table, selection, headers, scrollbars and status typography. Do not alter widget behavior.

- [ ] **Step 4: Rebuild the layout using the same widget instances**

Build:

- compact top bar;
- 64/36 horizontal splitter;
- left video/subtitle/progress column;
- right sentence header/editor/list/review column;
- single compact bottom control bar;
- slim status row.

Keep every signal connection and public attribute name unchanged.

- [ ] **Step 5: Run all main-window tests**

Run: `python -m pytest tests/integration/test_main_window.py -q`

Expected: PASS.

### Task 3: Progress bar and real Qt visual verification

**Files:**
- Modify: `src/shadowing_player/ui/sentence_progress_bar.py`
- Modify: `tests/integration/test_main_window.py`

**Interfaces:**
- Existing `SentenceProgressBar.sentence_clicked(int)` remains unchanged.

- [ ] **Step 1: Add a failing visual-property test**

```python
def test_sentence_progress_bar_uses_compact_height(qtbot):
    progress = SentenceProgressBar()
    qtbot.addWidget(progress)
    assert progress.height() == 12
```

- [ ] **Step 2: Run the test and confirm current height is 18**

Run: `python -m pytest tests/integration/test_main_window.py::test_sentence_progress_bar_uses_compact_height -q`

Expected: FAIL with `18 != 12`.

- [ ] **Step 3: Update themed painting**

Use transparent/background surface, two-pixel gaps, muted inactive segments and blue current segment. Preserve click-index math and signal behavior.

- [ ] **Step 4: Capture real Qt screenshots**

Launch a fake-backend `MainWindow`, populate bilingual sentences, show at 1180×720, process events and save a screenshot under `build/ui-preview/`. Repeat at 1024×680. Inspect both images for overlap, clipping, unreadable contrast and missing controls.

- [ ] **Step 5: Run integration and full tests**

Run: `python -m pytest tests/integration/test_main_window.py -q`

Run: `python -m pytest -q`

Expected: all tests pass.

### Task 4: Rebuild and verify folder distribution

**Files:**
- Modify if needed: `packaging/build_windows.ps1`
- Output: `dist/ShadowingPlayer/`

**Interfaces:**
- Produces: `dist/ShadowingPlayer/ShadowingPlayer.exe`
- Produces: `dist/ShadowingPlayer/_internal/assets/app-icon.ico`

- [ ] **Step 1: Run source compilation and dependency check**

Run: `python -m compileall -q src tests`

Run: `python -m pip check`

Expected: exit 0 and no broken requirements.

- [ ] **Step 2: Build from a clean PyInstaller work directory**

Run: `powershell -NoProfile -ExecutionPolicy Bypass -File packaging\build_windows.ps1`

Expected: exit 0 and package completion message.

- [ ] **Step 3: Verify packaged files and icon resources**

Assert the EXE, adjacent model, bundled libmpv/ffmpeg/ffprobe and `_internal/assets/app-icon.ico` exist. Use `pefile` to confirm resource types 3 and 14 remain embedded in the EXE.

- [ ] **Step 4: Run frozen smoke test**

Start `dist/ShadowingPlayer/ShadowingPlayer.exe --smoke-test` from an empty temporary `LOCALAPPDATA`, wait for exit and assert exit code 0. This exercises the bundled model, tools, Qt window and libmpv lifecycle.

- [ ] **Step 5: Re-run the full test suite**

Run: `python -m pytest -q`

Expected: all tests pass with zero failures.
