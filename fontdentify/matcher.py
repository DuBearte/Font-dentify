"""Compare letters from a picture against the fingerprint database and rank fonts."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .fingerprint import CHARSET, FontDatabase
from .scanner import FontFace


@dataclass
class Match:
    face: FontFace
    score: float  # 0..100, higher is better
    guessed_text: str


def _distances(glyph_vectors: np.ndarray, db_vectors: np.ndarray) -> np.ndarray:
    """Mean squared pixel difference. Shapes: (G, V) and (F, C, V) -> (G, F, C)."""
    g = glyph_vectors.astype(np.float32) / 255.0
    d = db_vectors.astype(np.float32) / 255.0
    F, C, V = d.shape
    flat = d.reshape(F * C, V)
    # |a-b|^2 = |a|^2 + |b|^2 - 2ab, computed in one matrix multiply.
    sq = (g**2).sum(axis=1)[:, None] + (flat**2).sum(axis=1)[None, :] - 2.0 * g @ flat.T
    return np.maximum(sq, 0.0).reshape(len(g), F, C) / V


def rank_fonts(glyphs: list[np.ndarray], db: FontDatabase, text: str | None = None, top: int = 5) -> list[Match]:
    """Rank the fonts in `db` by how well they match the glyphs taken from a picture.

    If `text` is given and has one character per glyph, each glyph is compared only
    with that character, which makes matching much more accurate. Otherwise every
    glyph is compared with every character and the closest one wins.
    """
    if not glyphs or len(db) == 0:
        return []
    vectors = np.stack([g.ravel() for g in glyphs])
    dist = _distances(vectors, db.vectors)  # (G, F, C)
    dist[:, ~db.available] = np.inf

    hint = [ch for ch in text if not ch.isspace()] if text else None
    if hint and len(hint) == len(glyphs):
        picked = np.zeros((len(glyphs), len(db)), dtype=np.float32)
        chars = []
        for gi, ch in enumerate(hint):
            ci = CHARSET.find(ch)
            if ci < 0:
                picked[gi] = np.nanmin(np.where(np.isfinite(dist[gi]), dist[gi], np.nan), axis=1)
            else:
                picked[gi] = dist[gi, :, ci]
            chars.append(ch)
        per_font_text = ["".join(chars)] * len(db)
    else:
        best_char = dist.argmin(axis=2)  # (G, F)
        picked = np.take_along_axis(dist, best_char[:, :, None], axis=2)[:, :, 0]
        per_font_text = ["".join(CHARSET[c] for c in best_char[:, fi]) for fi in range(len(db))]

    picked = np.where(np.isfinite(picked), picked, 1.0)
    per_font = picked.mean(axis=0)  # (F,)
    order = np.argsort(per_font)[:top]
    return [
        Match(db.faces[fi], float(100.0 * (1.0 - min(per_font[fi], 1.0))), per_font_text[fi])
        for fi in order
    ]
