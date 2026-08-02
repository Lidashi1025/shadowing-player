from pathlib import Path

from shadowing_player.audio.sentence_recorder import recording_path_for


def test_recording_path_is_stable_and_safe(tmp_path: Path) -> None:
    video = tmp_path / "My Video!.mp4"
    path = recording_path_for(tmp_path, video, 1_000, 2_500)
    assert path.parent.name == "recordings"
    assert path.suffix == ".wav"
    assert "My" in path.name
    assert "1000_2500" in path.name
