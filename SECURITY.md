# Security Policy

## Supported versions

Security fixes are applied to the latest `main` branch and the most recent GitHub Release.

## Reporting a vulnerability

Please prefer **GitHub Security Advisories** for the repository  
https://github.com/Lidashi1025/shadowing-player  

If that is unavailable, open a private report or a public Issue **without** attaching secrets, personal media, or credentials.

## Local data & privacy

- Settings, progress, favorites, and logs live under  
  `%LOCALAPPDATA%\ShadowingPlayer\`
- Transcription cache (folder package):  
  `%LOCALAPPDATA%\ShadowingPlayer\cache\transcriptions\`
- The app does **not** phone home. Offline ASR may download the Whisper model from Hugging Face on first use when missing.
- Session logs may include file paths and error text; do not share logs that contain sensitive path names.

## Scope notes

Shadowing Player is a local desktop tool. Report issues such as path traversal via malicious subtitle paths, unsafe subprocess invocation, or privilege issues when writing under Program Files (frozen installs should use LocalAppData for caches).
