from __future__ import annotations

import hashlib
from pathlib import Path


SAMPLE_SIZE = 1024 * 1024


def quick_video_hash(video_path: Path, sample_size: int = SAMPLE_SIZE) -> str:
    """Hash file size plus head/tail samples without reading the whole video."""

    size = video_path.stat().st_size
    digest = hashlib.sha256()
    digest.update(size.to_bytes(8, "big", signed=False))
    with video_path.open("rb") as stream:
        digest.update(stream.read(sample_size))
        if size > sample_size:
            stream.seek(max(sample_size, size - sample_size))
            digest.update(stream.read(sample_size))
    return digest.hexdigest()
