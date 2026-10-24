"""Pull the individual letters out of a picture of text."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

from .glyphs import normalize_glyph

# Blobs smaller than this fraction of the tallest letter are treated as noise.
MIN_RELATIVE_HEIGHT = 0.25


def otsu_threshold(gray: np.ndarray) -> int:
    """Pick the brightness cut-off that best separates ink from background."""
    hist = np.bincount(gray.ravel(), minlength=256).astype(np.float64)
    total = hist.sum()
    weight_bg = np.cumsum(hist)
    weight_fg = total - weight_bg
    levels = np.arange(256)
    sum_bg = np.cumsum(hist * levels)
    mean_bg = np.divide(sum_bg, weight_bg, out=np.zeros(256), where=weight_bg > 0)
    mean_fg = np.divide(sum_bg[-1] - sum_bg, weight_fg, out=np.zeros(256), where=weight_fg > 0)
    between = weight_bg * weight_fg * (mean_bg - mean_fg) ** 2
    return int(np.argmax(between))


def binarize(image: Image.Image) -> np.ndarray:
    """Return a boolean array where True marks ink, whatever the picture's colors."""
    gray = np.asarray(ImageOps.exif_transpose(image).convert("L"))
    cut = otsu_threshold(gray)
    dark = gray <= cut
    # Text is usually the minority color; the border is usually background.
    border = np.concatenate([dark[0], dark[-1], dark[:, 0], dark[:, -1]])
    ink = ~dark if border.mean() > 0.5 else dark
    return ink


def _runs(flags: np.ndarray) -> list[tuple[int, int]]:
    """Return (start, end) index pairs for each stretch of True values."""
    padded = np.concatenate([[False], flags, [False]]).astype(np.int8)
    edges = np.diff(padded)
    starts = np.flatnonzero(edges == 1)
    ends = np.flatnonzero(edges == -1)
    return list(zip(starts.tolist(), ends.tolist()))


def split_glyphs(ink: np.ndarray) -> list[np.ndarray]:
    """Split an ink mask into letter masks, reading left to right, line by line.

    Lines are found by looking for empty rows; letters inside a line are found by
    looking for empty columns. This is simple and works well for screenshots.
    """
    glyphs = []
    for top, bottom in _runs(ink.any(axis=1)):
        line = ink[top:bottom]
        for left, right in _runs(line.any(axis=0)):
            piece = line[:, left:right]
            rows = np.flatnonzero(piece.any(axis=1))
            glyphs.append(piece[rows[0] : rows[-1] + 1])
    if not glyphs:
        return []
    tallest = max(g.shape[0] for g in glyphs)
    return [g for g in glyphs if g.shape[0] >= MIN_RELATIVE_HEIGHT * tallest]


def extract_glyphs(source: str | Path | Image.Image) -> list[np.ndarray]:
    """Load a picture and return its letters as normalized glyph images."""
    image = Image.open(source) if not isinstance(source, Image.Image) else source
    ink = binarize(image)
    normalized = [normalize_glyph(mask) for mask in split_glyphs(ink)]
    return [g for g in normalized if g is not None]
