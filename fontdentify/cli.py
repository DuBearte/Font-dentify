"""Command line interface: `fontdentify scan`, `fontdentify index`, `fontdentify identify`."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .fingerprint import FontDatabase, build_database
from .matcher import rank_fonts
from .paths import cache_dir, system_font_dirs
from .scanner import scan_fonts
from .segment import extract_glyphs


def cmd_scan(args: argparse.Namespace) -> int:
    dirs = [Path(d) for d in args.dirs] if args.dirs else None
    faces = scan_fonts(dirs)
    for face in faces:
        print(f"{face.name}\t{face.path}" + (f"#{face.index}" if face.index else ""))
    print(f"\n{len(faces)} font faces found in: " + ", ".join(str(d) for d in (dirs or system_font_dirs())), file=sys.stderr)
    return 0


def cmd_index(args: argparse.Namespace) -> int:
    dirs = [Path(d) for d in args.dirs] if args.dirs else None
    faces = scan_fonts(dirs)
    if not faces:
        print("No fonts found.", file=sys.stderr)
        return 1

    def progress(n: int, total: int, face) -> None:
        if not args.quiet:
            print(f"\r[{n}/{total}] {face.name[:50]:<50}", end="", file=sys.stderr, flush=True)

    db = build_database(faces, progress)
    if not args.quiet:
        print(file=sys.stderr)
    folder = db.save(Path(args.cache) if args.cache else None)
    print(f"Indexed {len(db)} of {len(faces)} fonts into {folder}")
    return 0


def cmd_identify(args: argparse.Namespace) -> int:
    try:
        db = FontDatabase.load(Path(args.cache) if args.cache else None)
    except (FileNotFoundError, ValueError) as exc:
        print(exc, file=sys.stderr)
        return 1
    glyphs = extract_glyphs(args.image)
    if not glyphs:
        print("No letters found in the picture.", file=sys.stderr)
        return 1
    if args.text:
        expected = sum(1 for ch in args.text if not ch.isspace())
        if expected != len(glyphs):
            print(
                f"Note: the picture split into {len(glyphs)} letters but the text hint has {expected}. "
                "Some letters probably touch each other, so the hint was ignored.",
                file=sys.stderr,
            )
    matches = rank_fonts(glyphs, db, text=args.text, top=args.top)
    print(f"Found {len(glyphs)} letters. Best matches among {len(db)} installed fonts:\n")
    for i, m in enumerate(matches, start=1):
        print(f"{i}. {m.face.name:<40} {m.score:5.1f}%   read as: {m.guessed_text}")
        if args.verbose:
            print(f"   {m.face.path}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="fontdentify", description=__doc__)
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--cache", help=f"folder for the font database (default: {cache_dir()})")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("scan", help="list the fonts installed on this machine")
    p.add_argument("dirs", nargs="*", help="font folders to scan instead of the system defaults")
    p.set_defaults(func=cmd_scan)

    p = sub.add_parser("index", help="fingerprint the installed fonts (run once, and after installing fonts)")
    p.add_argument("dirs", nargs="*", help="font folders to scan instead of the system defaults")
    p.add_argument("-q", "--quiet", action="store_true")
    p.set_defaults(func=cmd_index)

    p = sub.add_parser("identify", help="find which installed font a picture uses")
    p.add_argument("image", help="screenshot or photo containing text")
    p.add_argument("-t", "--text", help="the text shown in the picture, if you know it (improves accuracy)")
    p.add_argument("-n", "--top", type=int, default=5, help="how many matches to show")
    p.add_argument("-v", "--verbose", action="store_true", help="also print the font file paths")
    p.set_defaults(func=cmd_identify)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
