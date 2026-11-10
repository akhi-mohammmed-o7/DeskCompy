"""Load companion art from ``assets``, including simple frame animations.

Each state can be a single picture (``working.png``) or a numbered sequence
(``working_0.png``, ``working_1.png``, ...). A sequence is played at a fixed
rate while that state is showing; a single picture is simply held. Both may
sit beside each other, so adding frames later never means deleting the still.

``assets/<character>/<state>`` is looked for first, then root state pictures
from the original single-companion layout, then a root portrait named after
the character, then ``companion.*``. The drawn buddy is the fallback for
everything. External folders are searched before the bundled copy, and the
cache refreshes when the user reloads custom buddies or switches characters.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QImageReader, QPixmap

from paths import asset_dirs
from safety import clean_slug

_IMAGE_SUFFIXES = (".png", ".webp", ".jpg", ".jpeg")
_MAX_HEIGHT = 168
_MAX_FRAMES = 24
# Reject before decoding, so a tiny compressed file cannot become a huge image.
_MAX_FILE_BYTES = 4 * 1024 * 1024
_MAX_DIMENSION = 1024
_MAX_SEQUENCE_PIXELS = 24_000_000
# A calm, readable flipbook. Fast states like Flicker still read at this rate.
FRAME_RATE = 6.0


@dataclass(frozen=True)
class Sprite:
    """One state's art: one still frame, or a loop of frames."""

    frames: tuple[QPixmap, ...]
    fps: float = FRAME_RATE

    def frame(self, elapsed: float) -> QPixmap:
        if len(self.frames) == 1 or self.fps <= 0:
            return self.frames[0]
        index = int(max(0.0, elapsed) * self.fps) % len(self.frames)
        return self.frames[index]


class SpriteLibrary:
    def __init__(
        self,
        folders: list[Path] | None = None,
        character: str = "moth",
    ) -> None:
        self.folders = (
            [Path(folder) for folder in folders] if folders is not None else asset_dirs()
        )
        self.character = character
        self._cache: dict[str, Sprite | None] = {}
        self._state = ""
        self._state_since = 0.0

    def set_character(self, character: str) -> None:
        if character == self.character:
            return
        self.character = character
        self._cache.clear()
        self._state = ""
        self._state_since = 0.0

    def refresh_if_due(self, force: bool = False) -> None:
        if force:
            self._cache.clear()

    def get(self, state: str) -> Sprite | None:
        if state not in self._cache:
            self._cache[state] = self._find(state)
        return self._cache[state]

    def frame(self, state: str) -> QPixmap | None:
        """The frame that should be on screen right now for ``state``."""
        now = time.monotonic()
        if state != self._state:
            self._state = state
            self._state_since = now
        sprite = self.get(state)
        if sprite is None:
            return None
        return sprite.frame(now - self._state_since)

    def _find(self, state: str) -> Sprite | None:
        # 1. A folder named after the character, board/<character>/working_0.png.
        # 2. A state picture at the root, for the old single-companion layout.
        # 3. A portrait at the root named after the character.
        # 4. companion.png, the original catch-all.
        # The id also becomes a folder name. Only a strict slug is joined to a
        # path; built-in and custom keys both fit, and a hand-edited settings
        # file cannot introduce ``..`` here.
        folder_name = clean_slug(self.character)
        if folder_name:
            for folder in self.folders:
                character_dir = folder / folder_name
                for stem in (state, "companion"):
                    sprite = self._at(character_dir, stem)
                    if sprite is not None:
                        return sprite
        for folder in self.folders:
            sprite = self._at(folder, state)
            if sprite is not None:
                return sprite
        for folder in self.folders:
            sprite = self._at(folder, self.character)
            if sprite is not None:
                return sprite
        for folder in self.folders:
            sprite = self._at(folder, "companion")
            if sprite is not None:
                return sprite
        return None

    def _at(self, folder: Path, stem: str) -> Sprite | None:
        frames = self._sequence(folder, stem)
        if frames:
            return Sprite(tuple(frames))
        still = self._still(folder, stem)
        if still is not None:
            return Sprite((still,))
        return None

    def _sequence(self, folder: Path, stem: str) -> list[QPixmap]:
        frames: list[QPixmap] = []
        pixels = 0
        for index in range(_MAX_FRAMES):
            hit = None
            for suffix in _IMAGE_SUFFIXES:
                hit = self._read(folder / f"{stem}_{index}{suffix}")
                if hit is not None:
                    break
            if hit is None:
                break
            pixels += hit.width() * hit.height()
            if pixels > _MAX_SEQUENCE_PIXELS:
                break
            frames.append(hit)
        return frames

    def _still(self, folder: Path, stem: str) -> QPixmap | None:
        for suffix in _IMAGE_SUFFIXES:
            hit = self._read(folder / f"{stem}{suffix}")
            if hit is not None:
                return hit
        return None

    @staticmethod
    def _read(path: Path) -> QPixmap | None:
        try:
            if path.is_symlink() or not path.is_file():
                return None
            if path.stat().st_size > _MAX_FILE_BYTES:
                return None
        except OSError:
            return None
        reader = QImageReader(str(path))
        reader.setAutoTransform(True)
        size: QSize = reader.size()
        if (
            not size.isValid()
            or size.width() <= 0
            or size.height() <= 0
            or size.width() > _MAX_DIMENSION
            or size.height() > _MAX_DIMENSION
        ):
            return None
        image = reader.read()
        if image.isNull():
            return None
        pixmap = QPixmap.fromImage(image)
        if pixmap.isNull():
            return None
        if pixmap.height() > _MAX_HEIGHT:
            pixmap = pixmap.scaledToHeight(
                _MAX_HEIGHT,
                Qt.TransformationMode.SmoothTransformation,
            )
        return pixmap
