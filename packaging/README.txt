Shadowing Player / 儿童影子跟读播放器（Windows 文件夹版）
========================================================

Start
-----
Double-click ShadowingPlayer.exe.

To create a desktop icon: Tools → Create desktop shortcut.
If you move the whole folder later, run that action again.

Keep the entire ShadowingPlayer folder. The player, libmpv, ffmpeg,
ffprobe, and (if included) the faster-whisper model all live here.

Environment check
-----------------
Tools → 环境检查 shows libmpv / ffmpeg / model status.
Tools → About shows version and log path.

Usage tips
----------
Drag a single MKV/MP4/WebM/MOV onto the window.
Tools → 转写语言 switches offline ASR language.
Tools → 导出收藏句子 writes SRT or Anki TSV.
Sentence list: click a row to jump; star to favorite.
Review list practices starred sentences across videos.
Favorites menu bookmarks whole videos with progress.
Startup restores the last existing video and stays paused.
Bottom dock exposes all shortcuts; hover a button to see the key.

If the video only has Chinese subs, offline ASR can generate English
and align bilingual text. Second open uses the cache.

Model note (slim builds)
------------------------
If models\faster-whisper-small is empty, the model downloads on the
first auto-transcription, or place model.bin + config.json there.

Migrate to another Windows x64 PC
---------------------------------
Copy the whole folder. Python is not required on the target PC.

User data
---------
Settings and progress:

  %LOCALAPPDATA%\ShadowingPlayer

Transcription cache: %LOCALAPPDATA%\ShadowingPlayer\cache\transcriptions
Model (folder package): models\faster-whisper-small (or download on first ASR)
Third-party notices: licenses\NOTICE.txt

Requirements
------------
Windows 11 x64. SmartScreen may warn because the build is not code-signed.
Choose More info → Run anyway after verifying the source.

Source / issues
---------------
https://github.com/Lidashi1025/shadowing-player
