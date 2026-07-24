from __future__ import annotations

from dataclasses import dataclass

from shadowing_player.subtitles.models import Sentence


@dataclass(frozen=True, slots=True)
class TranscriptWord:
    start_ms: int
    end_ms: int
    text: str


@dataclass(frozen=True, slots=True)
class TranscriptSegment:
    start_ms: int
    end_ms: int
    text: str
    words: tuple[TranscriptWord, ...] = ()

    @property
    def duration_ms(self) -> int:
        return max(0, self.end_ms - self.start_ms)


def _join_text(left: str, right: str) -> str:
    return f"{left.rstrip()} {right.lstrip()}".strip()


def _fallback_split(segment: TranscriptSegment, maximum_ms: int) -> list[TranscriptSegment]:
    pieces: list[TranscriptSegment] = []
    words = segment.text.split()
    start = segment.start_ms
    remaining_text = words
    while segment.end_ms - start > maximum_ms:
        split_ms = start + maximum_ms
        remaining_duration = max(1, segment.end_ms - start)
        ratio = maximum_ms / remaining_duration
        word_count = max(1, min(len(remaining_text) - 1, round(len(remaining_text) * ratio)))
        left_words, remaining_text = remaining_text[:word_count], remaining_text[word_count:]
        pieces.append(TranscriptSegment(start, split_ms, " ".join(left_words)))
        start = split_ms
    pieces.append(TranscriptSegment(start, segment.end_ms, " ".join(remaining_text)))
    return [piece for piece in pieces if piece.text.strip() and piece.end_ms > piece.start_ms]


def _split_long(segment: TranscriptSegment, maximum_ms: int) -> list[TranscriptSegment]:
    if segment.duration_ms <= maximum_ms:
        return [segment]
    if len(segment.words) < 2:
        return _fallback_split(segment, maximum_ms)

    output: list[TranscriptSegment] = []
    remaining = list(segment.words)
    while remaining and remaining[-1].end_ms - remaining[0].start_ms > maximum_ms:
        piece_start = remaining[0].start_ms
        candidates = [
            index
            for index in range(1, len(remaining))
            if remaining[index - 1].end_ms - piece_start <= maximum_ms
        ]
        if not candidates:
            return output + _fallback_split(
                TranscriptSegment(
                    remaining[0].start_ms,
                    remaining[-1].end_ms,
                    " ".join(word.text.strip() for word in remaining),
                    tuple(remaining),
                ),
                maximum_ms,
            )
        split_index = max(
            candidates,
            key=lambda index: (
                remaining[index].start_ms - remaining[index - 1].end_ms,
                remaining[index - 1].end_ms,
            ),
        )
        left_words = remaining[:split_index]
        output.append(
            TranscriptSegment(
                start_ms=left_words[0].start_ms,
                end_ms=left_words[-1].end_ms,
                text=" ".join(word.text.strip() for word in left_words).strip(),
                words=tuple(left_words),
            )
        )
        remaining = remaining[split_index:]
    if remaining:
        output.append(
            TranscriptSegment(
                start_ms=remaining[0].start_ms,
                end_ms=remaining[-1].end_ms,
                text=" ".join(word.text.strip() for word in remaining).strip(),
                words=tuple(remaining),
            )
        )
    return output


def _merge_short(segments: list[TranscriptSegment], minimum_ms: int) -> list[TranscriptSegment]:
    merged: list[TranscriptSegment] = []
    pending: TranscriptSegment | None = None
    for segment in segments:
        if pending is not None:
            segment = TranscriptSegment(
                pending.start_ms,
                max(pending.end_ms, segment.end_ms),
                _join_text(pending.text, segment.text),
                pending.words + segment.words,
            )
            pending = None
        if segment.duration_ms < minimum_ms:
            pending = segment
        else:
            merged.append(segment)
    if pending is not None:
        if merged:
            previous = merged.pop()
            merged.append(
                TranscriptSegment(
                    previous.start_ms,
                    max(previous.end_ms, pending.end_ms),
                    _join_text(previous.text, pending.text),
                    previous.words + pending.words,
                )
            )
        else:
            merged.append(pending)
    return merged


def postprocess_segments(
    segments: list[TranscriptSegment],
    minimum_ms: int = 1_000,
    maximum_ms: int = 8_000,
) -> list[Sentence]:
    split: list[TranscriptSegment] = []
    for segment in segments:
        if segment.text.strip() and segment.end_ms > segment.start_ms:
            split.extend(_split_long(segment, maximum_ms))
    merged = _merge_short(split, minimum_ms)
    return [
        Sentence(index, item.start_ms, item.end_ms, item.text.strip())
        for index, item in enumerate(merged)
    ]
