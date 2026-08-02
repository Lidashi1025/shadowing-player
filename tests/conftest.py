"""Pytest defaults for Shadowing Player."""

from __future__ import annotations

import os

# Keep MainWindow.open_video synchronous in tests (FakeSubtitleService is instant).
os.environ.setdefault("SHADOWING_SYNC_SUBTITLE_LOAD", "1")
