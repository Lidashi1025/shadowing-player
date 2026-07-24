# Windows 文件夹版封装 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 生成带儿童友好图标、内置 small 模型和媒体运行库的 `dist/ShadowingPlayer/ShadowingPlayer.exe` 文件夹版。

**Architecture:** 使用 PyInstaller onedir 冻结 Python 与 Qt 运行环境。运行时路径解析集中在 `runtime/bundle_paths.py`，开发环境和冻结环境使用同一组接口；模型放在 EXE 同级 `models`，只读运行库放在 PyInstaller `_internal`。

**Tech Stack:** Python 3.14、PySide6、PyInstaller、Pillow、faster-whisper、libmpv、ffmpeg

## Global Constraints

- 输出必须是 Windows 文件夹版，不制作单文件或安装程序。
- `models/faster-whisper-small` 必须随输出文件夹分发。
- 用户设置、SQLite 和字幕缓存仍位于 `%LOCALAPPDATA%/ShadowingPlayer`。
- 图标不包含文字或水印。
- 不加入录音、孩童模式或统计功能。
- 当前目录不是 Git 仓库，因此所有计划中的提交步骤均省略。

---

### Task 1: 冻结环境路径解析

**Files:**
- Create: `src/shadowing_player/runtime/bundle_paths.py`
- Modify: `src/shadowing_player/runtime/libmpv_loader.py`
- Modify: `src/shadowing_player/ui/main_window.py`
- Test: `tests/unit/test_bundle_paths.py`

**Interfaces:**
- Produces: `executable_dir() -> Path`
- Produces: `bundle_internal_dir() -> Path`
- Produces: `bundled_model_dir() -> Path | None`
- Produces: `bundled_binary_dir() -> Path | None`

- [ ] **Step 1: Write failing tests**

```python
def test_frozen_paths_use_executable_and_meipass(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path / "_internal"), raising=False)
    monkeypatch.setattr(sys, "executable", str(tmp_path / "ShadowingPlayer.exe"))
    assert executable_dir() == tmp_path
    assert bundle_internal_dir() == tmp_path / "_internal"
```

- [ ] **Step 2: Verify RED**

Run: `.\.venv\Scripts\python.exe -m pytest -q tests\unit\test_bundle_paths.py`
Expected: import failure because `bundle_paths` does not exist.

- [ ] **Step 3: Implement path helpers**

Use `sys.frozen`, `sys.executable` and `sys._MEIPASS`; non-frozen execution continues to resolve the repository root.

- [ ] **Step 4: Update consumers**

`configure_libmpv_path()` selects bundled `vendor/libmpv` when frozen and prepends bundled ffmpeg directory. `MainWindow` selects the adjacent bundled model when it contains `model.bin` and `config.json`, otherwise uses `%LOCALAPPDATA%`.

- [ ] **Step 5: Verify GREEN**

Run: `.\.venv\Scripts\python.exe -m pytest -q tests\unit\test_bundle_paths.py tests\unit\test_libmpv_loader.py`
Expected: all tests pass.

### Task 2: 应用图标资产

**Files:**
- Create: `assets/app-icon-source.png`
- Create: `assets/app-icon.png`
- Create: `assets/app-icon.ico`

**Interfaces:**
- Produces: a 1024px project PNG and multi-size Windows ICO.

- [ ] **Step 1: Generate source artwork**

Generate a blue-purple rounded player icon with a white play triangle, speech bubble and echo shapes on a flat removable chroma-key background.

- [ ] **Step 2: Remove the chroma key**

Run the imagegen skill helper with soft matte and despill, writing `assets/app-icon.png`.

- [ ] **Step 3: Inspect the transparent PNG**

Verify transparent corners, centered subject, no text and no watermark.

- [ ] **Step 4: Convert to ICO**

Use Pillow to save sizes `16, 24, 32, 48, 64, 128, 256`.

- [ ] **Step 5: Verify icon assets**

Open PNG and ICO with Pillow; assert RGBA PNG, transparent corner and all required ICO sizes.

### Task 3: PyInstaller 配置与构建脚本

**Files:**
- Create: `packaging/ShadowingPlayer.spec`
- Create: `packaging/build_windows.ps1`
- Create: `packaging/README.txt`
- Modify: `pyproject.toml`
- Modify: `.gitignore`

**Interfaces:**
- Consumes: `assets/app-icon.ico`, vendor libmpv, system ffmpeg, local small model.
- Produces: `dist/ShadowingPlayer/ShadowingPlayer.exe`.

- [ ] **Step 1: Add packaging dependencies**

Add `pyinstaller` and `pillow` to the `dev` optional dependency group and install the editable project.

- [ ] **Step 2: Write the PyInstaller spec**

Collect faster-whisper, CTranslate2, onnxruntime, tokenizers, av and PySide6 metadata/binaries. Add `libmpv-2.dll`, `ffmpeg.exe`, `ffprobe.exe`, icon and README. Keep the model outside `_internal`.

- [ ] **Step 3: Write the PowerShell build script**

Validate all inputs, invoke PyInstaller with `--noconfirm --clean`, copy the model directory to `dist/ShadowingPlayer/models/faster-whisper-small`, and fail if the EXE or model is missing.

- [ ] **Step 4: Update ignore rules**

Ignore `build/` and `dist/`; keep `assets`, `packaging` and specs tracked if the folder later becomes a Git repository.

- [ ] **Step 5: Build**

Run: `powershell -ExecutionPolicy Bypass -File packaging\build_windows.ps1`
Expected: exit 0 and output folder containing EXE, `_internal`, model and README.

### Task 4: Frozen executable verification

**Files:**
- Modify as needed only when a failing verification identifies a packaging defect.

**Interfaces:**
- Consumes: `dist/ShadowingPlayer`.
- Produces: verified portable application folder.

- [ ] **Step 1: Run automated source tests**

Run: `.\.venv\Scripts\python.exe -m pytest -q`
Expected: zero failures.

- [ ] **Step 2: Verify output inventory**

Check EXE, icon resource, model files, libmpv DLL, ffmpeg and ffprobe. Confirm the output does not reference `.venv` or project `src`.

- [ ] **Step 3: Launch from outside the project**

Use `Start-Process` from a temporary working directory, wait for the main window, then close it and confirm exit code 0.

- [ ] **Step 4: Verify model resolution**

Temporarily point `%LOCALAPPDATA%` to an empty directory, launch the frozen app and confirm `models/faster-whisper-small` is selected without downloading.

- [ ] **Step 5: Media smoke test**

Open a generated MKV/MP4 through a test harness or startup automation and verify libmpv loads; run ffprobe from the bundled path and load the bundled Whisper model.

- [ ] **Step 6: Report delivery**

Report the executable folder, total size, main EXE and icon paths, plus verification evidence.
