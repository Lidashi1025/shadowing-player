# Windows packaging

Build a portable folder app (no Python install required on the target PC).

## Prerequisites

- Windows x64
- Project venv with `.[dev]` installed (includes PyInstaller)
- `vendor/libmpv/libmpv-2.dll` (see `vendor/libmpv/README.md`)
- `assets/app-icon.ico`
- `ffmpeg.exe` and `ffprobe.exe` on `PATH` (same directory)
- For **full** package: local model at  
  `%LOCALAPPDATA%\ShadowingPlayer\models\faster-whisper-small`

## Commands

```powershell
# Full package (includes ~500MB whisper model)
.\packaging\build_windows.ps1

# Slim package (model downloads on first ASR use) + zip for GitHub Release
.\packaging\build_windows.ps1 -SkipModel -Zip
```

Outputs:

- Folder: `dist/ShadowingPlayer/`
- Zip (with `-Zip`): `dist/ShadowingPlayer-windows-x64-vX.Y.Z-slim.zip`

## Upload to GitHub Release

```powershell
gh release upload vX.Y.Z dist\ShadowingPlayer-windows-x64-vX.Y.Z-slim.zip --clobber
```

## Notes

- Keep the whole `ShadowingPlayer` folder; do not ship the exe alone.
- SmartScreen may warn (no code signing cert).
- End-user English/Chinese notes: `packaging/README.txt` (copied into the folder).
