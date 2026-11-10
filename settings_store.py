"""Small JSON memory for perch position, rituals, and the day's glimmer."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field

from activity import CHILL, GAMING, STUDY, WORK
from characters import CHARACTERS, DEFAULT_CHARACTER
from paths import settings_file
from safety import clean_text
from theme import AMBER, PALETTES


@dataclass
class Settings:
    x: int | None = None
    y: int | None = None
    water_enabled: bool = False
    next_water_epoch: float | None = None
    muted: bool = False
    intention: str = ""
    click_through: bool = False
    palette: str = AMBER
    glimmer_date: str = ""
    glimmer_seconds: float = 0.0
    # ISO date -> seconds finished on that day.
    history: dict[str, float] = field(default_factory=dict)
    # Keep the room dimmed for the whole focus vigil.
    veil: bool = False
    # Which buddy is perched: a built-in or a custom folder id.
    character: str = DEFAULT_CHARACTER
    # What the plate and bubble call them. Blank keeps the buddy's own name.
    nickname: str = ""
    # quiet / balanced / chatty: how often small talk appears.
    chatter: str = "balanced"
    idle_animations: bool = True
    mirror_particles: bool = True
    auto_talk: bool = True
    # "auto" lets the rhythm decide; anything else is a deliberate pin.
    activity_pin: str = "auto"

    def save(self) -> None:
        path = settings_file()
        payload = json.dumps(asdict(self), indent=2)
        temporary = path.with_suffix(".json.tmp")
        try:
            temporary.write_text(payload, encoding="utf-8")
            temporary.replace(path)
        except OSError as exc:
            logging.getLogger("lumen").warning("Could not save settings: %s", exc)


def _opt_int(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return int(value)


def _opt_float(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def load_settings() -> Settings:
    path = settings_file()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeError):
        return Settings()
    if not isinstance(raw, dict):
        return Settings()

    settings = Settings()
    settings.x = _opt_int(raw.get("x"))
    settings.y = _opt_int(raw.get("y"))
    if isinstance(raw.get("water_enabled"), bool):
        settings.water_enabled = raw["water_enabled"]
    settings.next_water_epoch = _opt_float(raw.get("next_water_epoch"))
    if isinstance(raw.get("muted"), bool):
        settings.muted = raw["muted"]
    if isinstance(raw.get("intention"), str):
        settings.intention = clean_text(raw["intention"], 80)
    if isinstance(raw.get("click_through"), bool):
        settings.click_through = raw["click_through"]
    palette = raw.get("palette")
    if isinstance(palette, str) and palette in PALETTES:
        settings.palette = palette
    if isinstance(raw.get("glimmer_date"), str):
        settings.glimmer_date = raw["glimmer_date"]
    glimmer = raw.get("glimmer_seconds")
    if isinstance(glimmer, (int, float)) and not isinstance(glimmer, bool) and glimmer >= 0:
        settings.glimmer_seconds = float(glimmer)
    history = raw.get("history")
    if isinstance(history, dict):
        clean: dict[str, float] = {}
        for key, value in history.items():
            if not isinstance(key, str) or len(key) != 10:
                continue
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                continue
            if value < 0 or value != value:
                continue
            clean[key] = float(value)
        settings.history = dict(sorted(clean.items())[-14:])
    if isinstance(raw.get("veil"), bool):
        settings.veil = raw["veil"]
    character = raw.get("character")
    if isinstance(character, str) and character in CHARACTERS:
        settings.character = character
    nickname = raw.get("nickname")
    if isinstance(nickname, str):
        settings.nickname = clean_text(nickname, 16)
    chatter = raw.get("chatter")
    if isinstance(chatter, str) and chatter in ("quiet", "balanced", "chatty"):
        settings.chatter = chatter
    for field_name in ("idle_animations", "mirror_particles", "auto_talk"):
        if isinstance(raw.get(field_name), bool):
            setattr(settings, field_name, raw[field_name])
    pin = raw.get("activity_pin")
    if pin in ("auto", STUDY, GAMING, WORK, CHILL):
        settings.activity_pin = pin
    return settings
