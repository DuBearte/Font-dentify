"""Turn a picture of a single letter into a small, comparable fingerprint."""

from __future__ import annotations

import numpy as np
from PIL import Image

# Every glyph is squeezed into a square this many pixels wide before comparing.
GLYPH_SIZE = 24
VECTOR_LENGTH = GLYPH_SIZE * GLYPH_SIZE


def crop_to_ink(mask: np.ndarray) -> np.ndarray | None:
    """Cut away blank borders. `mask` is a boolean array where True means ink."""
    rows = np.flatnonzero(mask.any(axis=1))
    cols = np.flatnonzero(mask.any(axis=0))
    if rows.size == 0 or cols.size == 0:
        return None
    return mask[rows[0] : rows[-1] + 1, cols[0] : cols[-1] + 1]


def normalize_glyph(mask: np.ndarray) -> np.ndarray | None:
    """Return a GLYPH_SIZE x GLYPH_SIZE uint8 image (0-255) of the glyph.

    The glyph is cropped to its ink, padded to a square so its proportions are
    kept, then shrunk. This makes letters of different sizes comparable.
    """
    cropped = crop_to_ink(mask)
    if cropped is None:
        return None
    h, w = cropped.shape
    side = max(h, w)
    square = np.zeros((side, side), dtype=np.uint8)
    top = (side - h) // 2
    left = (side - w) // 2
    square[top : top + h, left : left + w] = cropped.astype(np.uint8) * 255
    img = Image.fromarray(square, mode="L").resize((GLYPH_SIZE, GLYPH_SIZE), Image.BOX)
    return np.asarray(img, dtype=np.uint8)


def to_vector(glyph: np.ndarray) -> np.ndarray:
    """Flatten a normalized glyph into a float vector scaled to 0..1."""
    return glyph.astype(np.float32).ravel() / 255.0
