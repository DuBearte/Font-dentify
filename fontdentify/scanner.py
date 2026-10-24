"""Find the font files installed on this machine and read their names."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator

from fontTools.ttLib import TTFont, TTCollection, TTLibError

from .paths import FONT_EXTENSIONS, system_font_dirs


@dataclass(frozen=True)
class FontFace:
    """One font face: a file plus, for collections (.ttc), the index inside the file."""

    path: Path
    index: int
    family: str
    style: str

    @property
    def name(self) -> str:
        return f"{self.family} {self.style}".strip()

    @property
    def key(self) -> str:
        return f"{self.path}#{self.index}"


def _read_names(tt: TTFont) -> tuple[str, str]:
    name_table = tt["name"]
    family = name_table.getBestFamilyName() or ""
    style = name_table.getBestSubFamilyName() or ""
    return family, style


def _faces_in_file(path: Path) -> Iterator[FontFace]:
    try:
        if path.suffix.lower() == ".ttc":
            collection = TTCollection(path, lazy=True)
            for i, tt in enumerate(collection.fonts):
                family, style = _read_names(tt)
                yield FontFace(path, i, family, style)
            collection.close()
        else:
            tt = TTFont(path, lazy=True)
            family, style = _read_names(tt)
            tt.close()
            yield FontFace(path, 0, family, style)
    except (TTLibError, OSError, KeyError, AssertionError):
        # Damaged or unusual font files are skipped rather than crashing the scan.
        return


def find_font_files(dirs: Iterable[Path] | None = None) -> list[Path]:
    """Walk the font folders and return every font file found."""
    files = []
    for folder in dirs if dirs is not None else system_font_dirs():
        if not folder.is_dir():
            continue
        for path in folder.rglob("*"):
            if path.is_file() and path.suffix.lower() in FONT_EXTENSIONS:
                files.append(path)
    return sorted(set(files))


def scan_fonts(dirs: Iterable[Path] | None = None) -> list[FontFace]:
    """Return every usable font face installed in the given (or default) folders."""
    faces = []
    for path in find_font_files(dirs):
        faces.extend(_faces_in_file(path))
    return sorted(faces, key=lambda f: (f.family.lower(), f.style.lower(), f.key))
