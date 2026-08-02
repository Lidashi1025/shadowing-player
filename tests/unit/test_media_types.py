from pathlib import Path

from shadowing_player.media_types import VIDEO_EXTENSIONS, is_supported_video


def test_supported_video_extensions(tmp_path: Path) -> None:
    for suffix in (".mkv", ".mp4", ".webm", ".mov", ".avi", ".m4v"):
        path = tmp_path / f"clip{suffix}"
        path.write_bytes(b"x")
        assert is_supported_video(path)
    assert ".webm" in VIDEO_EXTENSIONS
    missing = tmp_path / "nope.mp4"
    assert not is_supported_video(missing)
