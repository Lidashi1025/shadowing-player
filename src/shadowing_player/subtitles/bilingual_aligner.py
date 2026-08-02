from __future__ import annotations

from dataclasses import replace

from shadowing_player.subtitles.models import Sentence


def _overlap_ms(left: Sentence, right: Sentence) -> int:
    return max(0, min(left.end_ms, right.end_ms) - max(left.start_ms, right.start_ms))


def align_bilingual(
    english: list[Sentence],
    chinese: list[Sentence],
    minimum_overlap_ratio: float = 0.30,
) -> list[Sentence]:
    """Assign each Chinese cue to its best-overlapping English sentence.

    Assumes both lists are ordered by start time (subtitle order). Uses an
    advancing window so typical work is near O(n + m) instead of O(n * m).
    """

    assigned: dict[int, list[Sentence]] = {index: [] for index in range(len(english))}
    start_index = 0
    english_count = len(english)
    for cue in chinese:
        while start_index < english_count and english[start_index].end_ms <= cue.start_ms:
            start_index += 1
        candidates: list[tuple[int, float, int]] = []
        index = start_index
        while index < english_count and english[index].start_ms < cue.end_ms:
            sentence = english[index]
            overlap = _overlap_ms(sentence, cue)
            denominator = max(1, min(sentence.duration_ms, cue.duration_ms))
            ratio = overlap / denominator
            if ratio >= minimum_overlap_ratio:
                candidates.append((overlap, ratio, index))
            index += 1
        if candidates:
            _overlap, _ratio, best_index = max(candidates)
            assigned[best_index].append(cue)

    result: list[Sentence] = []
    for index, sentence in enumerate(english):
        translations = sorted(assigned[index], key=lambda item: (item.start_ms, item.end_ms))
        text_zh = "".join(item.text.strip() for item in translations)
        result.append(replace(sentence, text_zh=text_zh))
    return result
