# Roadmap

## Now (maintenance)

- [x] Public MIT release, README, CONTRIBUTING
- [x] Version / About / logs / setup checklist
- [x] Unit-test CI (+ Python matrix)
- [x] Slim portable packaging + license NOTICE
- [x] Frozen cache under LocalAppData
- [x] ASR language options (auto/en/zh)
- [x] Export starred → SRT / Anki
- [x] Extra containers (webm/mov/avi/m4v)
- [ ] Respond to GitHub Issues promptly
- [ ] Confirm redistributed libmpv/ffmpeg LGPL/GPL status per build
- [ ] Code-signed release (optional cost)

## Next

1. Split `MainWindow` into loader / transcription / review coordinators
2. Move ffprobe/ffmpeg off the UI thread (background load pipeline)
3. Recording / self-compare for shadowing feedback
4. Light practice stats (`practiced_count`)
5. GPU/CUDA optional for ASR

## Later

- Child mode (if product returns to kid-focused UX)
- Installer + Azure Trusted Signing
- Non-Windows ports

## Priorities

1. Crash / data loss / compliance  
2. Install friction  
3. Practice workflow  
4. Nice-to-have UI  
