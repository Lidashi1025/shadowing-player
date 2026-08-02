# Third-party licenses for Windows packages

`build_windows.ps1` copies this directory into `dist/ShadowingPlayer/licenses/`.

## Checklist before public redistribution

1. Confirm **libmpv** build license (prefer LGPL-safe Shinchiro or self-built LGPL).
2. Confirm **ffmpeg/ffprobe** build is acceptable for your license goals (GPL vs LGPL).
3. Add full license text files for every binary you ship (mpv, ffmpeg, Qt/PySide6, ASR stack).
4. Keep `NOTICE.txt` and the project root `LICENSE` in the package.

## Suggested files to add manually

| File | Source |
|---|---|
| `mpv-COPYING.LESSER` / GPL | mpv release you downloaded |
| `ffmpeg-LICENSE` | ffmpeg build tree |
| `qt-lgpl` / PySide6 notices | Qt / PySide6 packages |
| `faster-whisper` / `ctranslate2` | PyPI / upstream repos |

This folder ships a baseline `NOTICE.txt` so empty packages are not license-silent.
