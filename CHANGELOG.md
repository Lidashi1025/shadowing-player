# Changelog

All notable changes to this project are documented in this file.

## [0.3.1] — 2026-08-02

### Architecture (Kimi K3 iteration A)

- Split open-video planning into `playback/video_open_plan.py`
- Background subtitle discovery via `SubtitleDiscoverController` (tests force sync with `SHADOWING_SYNC_SUBTITLE_LOAD=1`)
- Extract `TranscriptionJobManager` and `ReviewSession` from `MainWindow`
- Faster bilingual aligner sliding window retained from 0.3.0

## [0.3.0] — 2026-08-02

### Added

- ASR language menu: auto / English / Chinese (`Tools → 转写语言`)
- Export starred sentences to **SRT** or **Anki TSV** (`Tools → 导出收藏句子`)
- More video containers: WebM, MOV, AVI, M4V
- `SECURITY.md`, PR template, packaging `licenses/NOTICE.txt`
- GitHub `release.yml` workflow scaffold; CI matrix Python 3.12 + 3.13

### Fixed / improved (Kimi K3 review P0–P1)

- Frozen transcription cache writes to `%LOCALAPPDATA%\ShadowingPlayer\...` (Program Files safe)
- Opening a video during review correctly stops review mode
- Wait cursor + status while parsing subtitles
- Speed range extended to **0.50×–1.50×**
- Rotating log file (2 MB × 3)
- Empty failed-exception messages no longer blank
- Bilingual aligner uses a sliding time window (faster on long cue lists)
- Packaging: copy LICENSE + licenses/, disable UPX, exclude dev packages, run `--smoke-test`
- libmpv README documents GPL/LGPL redistribution risk

## [0.2.2] — 2026-08-02

### Added

- **Tools → 环境检查** first-run setup checklist
- Slim packaging `-SkipModel -Zip`

## [0.2.1] — 2026-08-02

### Added

- `--version`, About dialog, file logging, ffprobe probe, CI unit tests

## [0.2.0] — 2026-07-25

### Added

- Video favorites, startup resume, click/double-click video, MIT public release
