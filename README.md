# Shadowing Player · 儿童影子跟读播放器

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows%2011-0078D6)](#environment)
[![Python](https://img.shields.io/badge/python-3.12%E2%80%933.14-3776AB)](#environment)

Local Windows player for **sentence-level shadowing practice**. It treats subtitle cues as practice units, supports MKV/MP4, single-sentence loop, gap pauses, pitch-preserving speed control, bilingual subtitles, and offline English transcription via faster-whisper.

Windows 本机播放器：以字幕时间轴为句子边界，支持 MKV／MP4、逐句跟读、单句精听、变速不变调、双语字幕，以及 faster-whisper 离线英文转写。

> Current focus: product v2 playback / practice loop. Recording, child lock, and learning analytics are intentionally out of scope for now.

## Why this exists

Most video players are built for watching. Language practice needs:

- jump by **sentence**, not only by second
- repeat with **controlled gaps**
- keep pitch when slowing down
- work **offline** after model download
- keep progress and favorites across sessions

Shadowing Player is a small, local tool for that workflow—useful for parents, self-learners, and anyone drilling with subtitled video.

## Features

- **Watch mode**: continuous playback with sentence list + large subtitle panel
- **Sentence shadowing**: play each sentence 1–3 times, pause by duration × gap multiplier
- **Single-sentence loop**: infinite loop of the current cue; Space pauses/resumes
- **Speed control**: `0.50×–1.00×` with mpv `scaletempo2` (pitch preserved)
- **Subtitles**: external `.srt`/`.ass`, embedded text tracks, or offline English ASR
- **Bilingual display**: English / bilingual / hidden; Chinese from existing subs aligned by time overlap
- **Favorites & resume**: per-video progress, video favorites, sentence favorites, cross-video review list
- **Local-first**: settings and SQLite progress under `%LOCALAPPDATA%\ShadowingPlayer\`

## Environment

- Windows 11 x64
- Python 3.12–3.14 x64 (validated on 3.14.3)
- `vendor/libmpv/libmpv-2.dll` — see [vendor/libmpv/README.md](vendor/libmpv/README.md)
- `ffmpeg.exe` and `ffprobe.exe` on `PATH` (embedded subtitle extraction)
- First-time ASR downloads faster-whisper `small` over the network; transcription runs on local CPU

## Install & run

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m shadowing_player
```

Open a `.mkv` / `.mp4`, or drag a file onto the window.

Subtitle resolution order:

1. External `.srt` / `.ass` next to the video (same name or language suffix)
2. Embedded text tracks (English preferred)
3. Optional offline English transcription with faster-whisper when no text subs exist

Image-based subtitles cannot build a sentence list; the app shows a clear message.

Recent files list the last 8 still-existing videos. Folder-package users can create a desktop shortcut via **Tools**.

## Keyboard shortcuts

| Key | Action |
|---|---|
| Ctrl+O | Open video |
| Ctrl+H | Recent files |
| Space | Play/pause; also pause/resume gap countdown |
| ← | Replay current sentence (double-tap within 400ms = previous) |
| Ctrl+← | Previous sentence |
| → | Next sentence |
| ↑ / ↓ | Speed ±0.05 |
| L | Toggle single-sentence loop |
| M | Cycle English / bilingual / hide subs |
| Tab | Cycle playback mode |
| S | Favorite current sentence |
| R | Open cross-video review list |
| F | Fullscreen |
| F1 | Shortcut settings |

All of the above also have dock buttons. Shortcuts are editable under **Tools → Shortcut settings**.

## Data locations

| Kind | Path |
|---|---|
| Settings | `%LOCALAPPDATA%\ShadowingPlayer\settings.json` |
| Progress / favorites | `%LOCALAPPDATA%\ShadowingPlayer\data.sqlite` |
| Source-install models | `%LOCALAPPDATA%\ShadowingPlayer\models\faster-whisper-small` |
| Folder-package models | `models\faster-whisper-small` next to the app |
| Transcription cache | `cache\transcriptions\<hash>.srt` (app directory) |

## Version & logs

```powershell
.\.venv\Scripts\python.exe -m shadowing_player --version
```

Inside the app: **Tools → About** shows version, repo link, and log path.

Runtime log:

```text
%LOCALAPPDATA%\ShadowingPlayer\shadowing-player.log
```

If embedded subtitles fail, confirm `ffprobe` is on `PATH`. External `.srt`/`.ass` still work without it; the status bar warns at startup when ffprobe is missing.

**Tools → 环境检查** shows libmpv / ffmpeg / model status. On first runs with optional gaps, a checklist may open automatically (you can dismiss future prompts).

## Tests

```powershell
# Preferred for CI / day-to-day: unit tests only
.\.venv\Scripts\python.exe -m pytest tests/unit -q

# Full suite (includes Qt integration tests)
.\.venv\Scripts\python.exe -m pytest -q
```

## Packaging notes

Windows folder packaging scripts live under `packaging/`. See [packaging/README.md](packaging/README.md).

```powershell
# Slim portable zip for GitHub Releases (model downloads on first ASR)
.\packaging\build_windows.ps1 -SkipModel -Zip
```

Built artifacts in `build/` and `dist/` are not committed.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md), [ROADMAP.md](ROADMAP.md), and [CHANGELOG.md](CHANGELOG.md).  
Issues and PRs are welcome—especially install friction on clean Windows machines, subtitle edge cases, and accessibility.

## License

[MIT](LICENSE)

Third-party runtimes (libmpv, ffmpeg, faster-whisper models, PySide6/Qt) remain under their own licenses. Place redistributable binaries according to their terms when you ship a packaged build.
