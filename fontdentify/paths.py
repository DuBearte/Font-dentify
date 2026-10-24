"""Where fonts and cached data live on each operating system."""

from __future__ import annotations

import os
import sys
from pathlib import Path

FONT_EXTENSIONS = {".ttf", ".otf", ".ttc"}


def system_font_dirs() -> list[Path]:
    """Return the folders where fonts are normally installed on this OS."""
    home = Path.home()
    if sys.platform.startswith("win"):
        windir = Path(os.environ.get("WINDIR", r"C:\Windows"))
        local = os.environ.get("LOCALAPPDATA")
        dirs = [windir / "Fonts"]
        if local:
            # Fonts installed "for this user only" on Windows 10/11.
            dirs.append(Path(local) / "Microsoft" / "Windows" / "Fonts")
    elif sys.platform == "darwin":
        dirs = [
            Path("/System/Library/Fonts"),
            Path("/Library/Fonts"),
            home / "Library" / "Fonts",
        ]
    else:
        dirs = [
            Path("/usr/share/fonts"),
            Path("/usr/local/share/fonts"),
            home / ".fonts",
            home / ".local" / "share" / "fonts",
        ]
        data_dirs = os.environ.get("XDG_DATA_DIRS", "")
        for d in data_dirs.split(os.pathsep):
            if d:
                dirs.append(Path(d) / "fonts")
    seen: set[Path] = set()
    unique = []
    for d in dirs:
        if d not in seen:
            seen.add(d)
            unique.append(d)
    return unique


def cache_dir() -> Path:
    """Folder where the fingerprint database is stored."""
    if sys.platform.startswith("win"):
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Caches"
    else:
        base = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
    path = base / "fontdentify"
    path.mkdir(parents=True, exist_ok=True)
    return path
