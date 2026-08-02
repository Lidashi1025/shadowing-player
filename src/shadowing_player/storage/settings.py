from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from shadowing_player.playback.session_controller import PlaybackMode
from shadowing_player.shortcut_catalog import default_shortcuts


@dataclass(slots=True)
class AppSettings:
    speed: float = 1.0
    mode: PlaybackMode = PlaybackMode.WATCH
    blank_multiplier: float = 1.5
    plays_per_sentence: int = 1
    auto_advance: bool = True
    subtitle_visible: bool = True
    subtitle_mode: str = "bilingual"
    asr_language: str = "en"
    setup_checklist_dismissed: bool = False
    shortcuts: dict[str, str] = field(default_factory=default_shortcuts)


def load_settings(path: Path) -> tuple[AppSettings, str | None]:
    if not path.is_file():
        return AppSettings(), None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        subtitle_visible = bool(payload.get("subtitle_visible", True))
        subtitle_mode = str(
            payload.get("subtitle_mode", "bilingual" if subtitle_visible else "hidden")
        )
        settings = AppSettings(
            speed=float(payload.get("speed", 1.0)),
            mode=PlaybackMode(payload.get("mode", PlaybackMode.WATCH.value)),
            blank_multiplier=float(payload.get("blank_multiplier", 1.5)),
            plays_per_sentence=int(payload.get("plays_per_sentence", 1)),
            auto_advance=bool(payload.get("auto_advance", True)),
            subtitle_visible=subtitle_visible,
            subtitle_mode=subtitle_mode,
            asr_language=str(payload.get("asr_language", "en")),
            setup_checklist_dismissed=bool(
                payload.get("setup_checklist_dismissed", False)
            ),
            shortcuts={**default_shortcuts(), **dict(payload.get("shortcuts", {}))},
        )
        if not 0.5 <= settings.speed <= 1.5:
            raise ValueError("speed")
        if not 1.2 <= settings.blank_multiplier <= 2.5:
            raise ValueError("blank_multiplier")
        if not 1 <= settings.plays_per_sentence <= 3:
            raise ValueError("plays_per_sentence")
        if settings.subtitle_mode not in {"english", "bilingual", "hidden"}:
            raise ValueError("subtitle_mode")
        if settings.asr_language not in {"auto", "en", "zh"}:
            raise ValueError("asr_language")
        return settings, None
    except (OSError, TypeError, ValueError, json.JSONDecodeError):
        return AppSettings(), "设置文件格式错误，已恢复默认设置"


def save_settings(path: Path, settings: AppSettings) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = asdict(settings)
    payload["mode"] = settings.mode.value
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporary.replace(path)
