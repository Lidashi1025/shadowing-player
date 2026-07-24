from shadowing_player.ui.split_sentence_dialog import propose_text_split


def test_proposes_english_split_at_nearest_word_ratio() -> None:
    assert propose_text_split("One two three four", 0.5) == (
        "One two",
        "three four",
    )


def test_proposes_chinese_split_by_character_ratio() -> None:
    assert propose_text_split("你好再来一次", 0.5, chinese=True) == (
        "你好再",
        "来一次",
    )
