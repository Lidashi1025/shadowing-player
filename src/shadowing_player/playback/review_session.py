from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from shadowing_player.playback.session_controller import PlaybackMode


@dataclass(slots=True)
class ReviewSession:
    """Tracks whether the user is inside cross-video review mode."""

    active: bool = False
    return_video: Path | None = None
    return_mode: PlaybackMode | None = None

    def begin(self, current_video: Path | None, current_mode: PlaybackMode) -> None:
        self.active = True
        self.return_video = current_video
        self.return_mode = current_mode

    def stop(self) -> tuple[Path | None, PlaybackMode | None]:
        video, mode = self.return_video, self.return_mode
        self.active = False
        self.return_video = None
        self.return_mode = None
        return video, mode

    def cancel(self) -> None:
        self.active = False
        self.return_video = None
        self.return_mode = None
