"""Build and store the fingerprint database of installed fonts.

For each font we draw a fixed set of characters and keep a small normalized
image of each one. Those images are what a picture's letters get compared to.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

import numpy as np
from fontTools.ttLib import TTFont, TTCollection, TTLibError
from PIL import Image, ImageDraw, ImageFont

from .glyphs import GLYPH_SIZE, VECTOR_LENGTH, normalize_glyph
from .paths import cache_dir
from .scanner import FontFace, scan_fonts

CHARSET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
RENDER_SIZE = 96  # pixel height used when drawing each character
# Fonts missing more than this share of CHARSET are ignored (icon and symbol fonts).
MIN_COVERAGE = 0.8

DB_FORMAT_VERSION = 1


@dataclass
class FontDatabase:
    """Fingerprints for a set of fonts.

    `vectors` has shape (fonts, len(CHARSET), VECTOR_LENGTH) and holds uint8 pixels.
    `available[f, c]` is False when font `f` has no glyph for character `c`.
    """

    faces: list[FontFace]
    vectors: np.ndarray
    available: np.ndarray

    def __len__(self) -> int:
        return len(self.faces)

    def save(self, folder: Path | None = None) -> Path:
        folder = folder or cache_dir()
        folder.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(folder / "fingerprints.npz", vectors=self.vectors, available=self.available)
        meta = {
            "format": DB_FORMAT_VERSION,
            "charset": CHARSET,
            "glyph_size": GLYPH_SIZE,
            "faces": [
                {"path": str(f.path), "index": f.index, "family": f.family, "style": f.style}
                for f in self.faces
            ],
        }
        (folder / "fonts.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
        return folder

    @classmethod
    def load(cls, folder: Path | None = None) -> "FontDatabase":
        folder = folder or cache_dir()
        meta_path = folder / "fonts.json"
        if not meta_path.exists():
            raise FileNotFoundError(
                f"No font database in {folder}. Run `fontdentify index` first."
            )
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        if meta.get("format") != DB_FORMAT_VERSION or meta.get("charset") != CHARSET:
            raise ValueError("Font database is from an older version. Run `fontdentify index` again.")
        data = np.load(folder / "fingerprints.npz")
        faces = [FontFace(Path(f["path"]), f["index"], f["family"], f["style"]) for f in meta["faces"]]
        return cls(faces, data["vectors"], data["available"])


def _supported_chars(face: FontFace) -> set[str]:
    """Which characters of CHARSET the font actually contains."""
    try:
        if face.path.suffix.lower() == ".ttc":
            tt = TTCollection(face.path, lazy=True).fonts[face.index]
        else:
            tt = TTFont(face.path, lazy=True)
        cmap = tt.getBestCmap() or {}
        tt.close()
    except (TTLibError, OSError, KeyError, AssertionError):
        return set()
    return {ch for ch in CHARSET if ord(ch) in cmap}


def render_char(font: ImageFont.FreeTypeFont, char: str) -> np.ndarray | None:
    """Draw one character and return its normalized glyph, or None if it is blank."""
    left, top, right, bottom = font.getbbox(char)
    width, height = right - left, bottom - top
    if width <= 0 or height <= 0:
        return None
    pad = 4
    img = Image.new("L", (width + 2 * pad, height + 2 * pad), 0)
    ImageDraw.Draw(img).text((pad - left, pad - top), char, fill=255, font=font)
    mask = np.asarray(img) > 127
    return normalize_glyph(mask)


def fingerprint_face(face: FontFace) -> tuple[np.ndarray, np.ndarray] | None:
    """Fingerprint one font face. Returns (vectors, available) or None if unusable."""
    chars = _supported_chars(face)
    if len(chars) < MIN_COVERAGE * len(CHARSET):
        return None
    try:
        font = ImageFont.truetype(str(face.path), RENDER_SIZE, index=face.index)
    except OSError:
        return None

    vectors = np.zeros((len(CHARSET), VECTOR_LENGTH), dtype=np.uint8)
    available = np.zeros(len(CHARSET), dtype=bool)
    for i, ch in enumerate(CHARSET):
        if ch not in chars:
            continue
        try:
            glyph = render_char(font, ch)
        except (OSError, ValueError):
            glyph = None
        if glyph is None:
            continue
        vectors[i] = glyph.ravel()
        available[i] = True
    if available.sum() < MIN_COVERAGE * len(CHARSET):
        return None
    return vectors, available


def build_database(
    faces: Iterable[FontFace] | None = None,
    progress: Callable[[int, int, FontFace], None] | None = None,
) -> FontDatabase:
    """Fingerprint every installed font (or the given faces)."""
    faces = list(faces) if faces is not None else scan_fonts()
    kept: list[FontFace] = []
    all_vectors = []
    all_available = []
    for n, face in enumerate(faces, start=1):
        if progress:
            progress(n, len(faces), face)
        result = fingerprint_face(face)
        if result is None:
            continue
        vectors, available = result
        kept.append(face)
        all_vectors.append(vectors)
        all_available.append(available)
    if not kept:
        return FontDatabase([], np.zeros((0, len(CHARSET), VECTOR_LENGTH), np.uint8), np.zeros((0, len(CHARSET)), bool))
    return FontDatabase(kept, np.stack(all_vectors), np.stack(all_available))
