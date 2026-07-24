from __future__ import annotations

from PySide6.QtCore import Qt

from shadowing_player.subtitles.models import Sentence
from shadowing_player.ui.sentence_table_model import SentenceTableModel


def test_star_column_displays_real_star_and_emits_sentence_change(qtbot) -> None:
    sentence = Sentence(0, 0, 1_000, "Hello", id=7)
    model = SentenceTableModel()
    model.set_sentences([sentence])
    changes: list[tuple[int, bool]] = []
    model.starred_changed.connect(lambda item, starred: changes.append((item.id, starred)))
    index = model.index(0, 1)

    assert model.data(index, Qt.ItemDataRole.DisplayRole) == "☆"
    model.toggle_star(0)

    assert changes == [(7, True)]
    assert model.sentences[0].starred is True
    assert model.data(index, Qt.ItemDataRole.DisplayRole) == "★"


def test_current_row_role_changes_without_changing_sentences() -> None:
    model = SentenceTableModel()
    model.set_sentences(
        [
            Sentence(0, 0, 1_000, "First"),
            Sentence(1, 1_000, 2_000, "Second"),
        ]
    )

    model.set_current_row(1)

    assert model.data(model.index(0, 0), model.CurrentRole) is False
    assert model.data(model.index(1, 0), model.CurrentRole) is True
    assert [sentence.text for sentence in model.sentences] == ["First", "Second"]


def test_bilingual_display_adds_chinese_on_second_line() -> None:
    model = SentenceTableModel()
    model.set_sentences([Sentence(0, 0, 1_000, "Hello", text_zh="你好")])

    model.set_subtitle_mode("bilingual")
    assert model.data(model.index(0, 0), Qt.ItemDataRole.DisplayRole) == "1.  Hello\n你好"

    model.set_subtitle_mode("english")
    assert model.data(model.index(0, 0), Qt.ItemDataRole.DisplayRole) == "1.  Hello"
