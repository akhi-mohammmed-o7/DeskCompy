"""Small JSON memory for perch position, rituals, and the day's glimmer."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field

import focus_history
from activity import CHILL, GAMING, STUDY, WORK
from characters import CHARACTERS, DEFAULT_CHARACTER
from paths import settings_file
from rewards import ACCESSORY_KEYS, DEFAULT_ACCESSORY
from safety import clean_text
from theme import AMBER, COAT_LABELS, NATURAL, PALETTES


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
    # Dim the desktop while a focus timer runs. Never a standing state.
    dim_focus: bool = True
    # Which buddy is perched: a built-in or a custom folder id.
    character: str = DEFAULT_CHARACTER
    # What the plate and bubble call them. Blank keeps the buddy's own name.
    nickname: str = ""
    # quiet / balanced / chatty: how often small talk appears.
    chatter: str = "balanced"
    idle_animations: bool = True
    mirror_particles: bool = True
    auto_talk: bool = False
    # Start with Windows. The registry entry, not this flag, is the truth.
    launch_at_start: bool = False
    # "auto" lets the rhythm decide; anything else is a deliberate pin.
    activity_pin: str = "auto"
    # Coat colour mixed into the buddy's own palette.
    coat: str = NATURAL
    # Equipped accessory id; only an earned one is ever drawn.
    accessory: str = DEFAULT_ACCESSORY
    # Last chosen focus length, and the reward ledger.
    focus_minutes: int = 25
    focus_sessions: int = 0
    focus_minutes_total: float = 0.0
    # Finished sessions as "YYYY-MM-DDTHH:MM|minutes"; drives the log and streaks.
    focus_log: list[str] = field(default_factory=list)

    def save(self) -> None:
        path = settings_file()
        data = asdict(self)
        data["schema_version"] = 2
        payload = json.dumps(data, indent=2)
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
    # Older builds had a standing "dim the lights" switch. Dimming is now
    # tied to the focus timer, so a saved veil only means "keep dimming".
    if isinstance(raw.get("dim_focus"), bool):
        settings.dim_focus = raw["dim_focus"]
    elif isinstance(raw.get("veil"), bool) and raw["veil"]:
        settings.dim_focus = True
    character = raw.get("character")
    if isinstance(character, str) and character in CHARACTERS:
        settings.character = character
    nickname = raw.get("nickname")
    if isinstance(nickname, str):
        settings.nickname = clean_text(nickname, 16)
    chatter = raw.get("chatter")
    if isinstance(chatter, str) and chatter in ("quiet", "balanced", "chatty"):
        settings.chatter = chatter
    for field_name in ("idle_animations", "mirror_particles", "launch_at_start"):
        if isinstance(raw.get(field_name), bool):
            setattr(settings, field_name, raw[field_name])
    # Ambient lines were enabled by default in early builds. Turn that legacy
    # default off once; an explicit opt-in in newer settings is respected.
    schema_version = raw.get("schema_version", 1)
    if isinstance(schema_version, int) and not isinstance(schema_version, bool) and schema_version >= 2:
        if isinstance(raw.get("auto_talk"), bool):
            settings.auto_talk = raw["auto_talk"]
    pin = raw.get("activity_pin")
    if pin in ("auto", STUDY, GAMING, WORK, CHILL):
        settings.activity_pin = pin
    coat = raw.get("coat")
    if isinstance(coat, str) and coat in COAT_LABELS:
        settings.coat = coat
    accessory = raw.get("accessory")
    if isinstance(accessory, str) and accessory in ACCESSORY_KEYS:
        settings.accessory = accessory
    focus_minutes = _opt_int(raw.get("focus_minutes"))
    if focus_minutes is not None:
        settings.focus_minutes = max(5, min(60, focus_minutes))
    sessions = _opt_int(raw.get("focus_sessions"))
    if sessions is not None and sessions >= 0:
        settings.focus_sessions = sessions
    total = raw.get("focus_minutes_total")
    if isinstance(total, (int, float)) and not isinstance(total, bool) and total >= 0:
        settings.focus_minutes_total = float(total)
    log = raw.get("focus_log")
    if isinstance(log, list):
        clean_log = [
            item
            for item in log
            if isinstance(item, str) and focus_history.parse(item) is not None
        ]
        settings.focus_log = clean_log[-focus_history.MAX_ENTRIES:]
    return settings
