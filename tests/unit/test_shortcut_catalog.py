from shadowing_player.shortcut_catalog import (
    default_shortcuts,
    find_shortcut_conflicts,
    shortcut_definitions,
)


def test_shortcut_catalog_covers_all_visible_actions() -> None:
    names = {item.name for item in shortcut_definitions()}

    assert {
        "open_video",
        "recent",
        "play_pause",
        "repeat",
        "previous",
        "next",
        "speed_up",
        "speed_down",
        "single_loop",
        "subtitle",
        "mode",
        "star",
        "review",
        "record",
        "play_recording",
        "play_original",
        "fullscreen",
        "shortcut_help",
    } == names
    assert set(default_shortcuts()) == names
    assert all(item.description for item in shortcut_definitions())


def test_shortcut_conflicts_are_normalized_and_empty_keys_are_ignored() -> None:
    conflicts = find_shortcut_conflicts(
        {
            "play_pause": "Space",
            "repeat": "space",
            "next": "",
            "previous": "",
        }
    )

    assert conflicts == {"Space": ("play_pause", "repeat")}
