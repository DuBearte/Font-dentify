"""End-to-end checks: render text in a known font, then ask the tool which font it is."""

from PIL import Image, ImageDraw, ImageFont

from fontdentify.fingerprint import CHARSET, FontDatabase
from fontdentify.matcher import rank_fonts
from fontdentify.segment import extract_glyphs


def render_text(face, text, size=72, invert=False):
    font = ImageFont.truetype(str(face.path), size, index=face.index)
    left, top, right, bottom = font.getbbox(text)
    bg, fg = (255, 0) if not invert else (0, 255)
    img = Image.new("L", (right - left + 40, bottom - top + 40), bg)
    ImageDraw.Draw(img).text((20 - left, 20 - top), text, fill=fg, font=font)
    return img


def test_scanner_reads_names(faces):
    assert all(face.family for face in faces)


def test_database_round_trip(db, tmp_path):
    db.save(tmp_path)
    loaded = FontDatabase.load(tmp_path)
    assert len(loaded) == len(db)
    assert (loaded.vectors == db.vectors).all()
    assert loaded.faces[0].name == db.faces[0].name


def test_extracts_one_glyph_per_letter(db):
    face = db.faces[0]
    glyphs = extract_glyphs(render_text(face, "HELLO"))
    assert len(glyphs) == 5


def test_identifies_rendered_font_in_top_three(db):
    misses = []
    for face in db.faces[: min(len(db), 15)]:
        glyphs = extract_glyphs(render_text(face, "Fontdentify"))
        names = [m.face.name for m in rank_fonts(glyphs, db, top=3)]
        if face.name not in names:
            misses.append((face.name, names))
    # Allow a little slack: some families ship near-identical faces.
    assert len(misses) <= 2, misses


def test_text_hint_puts_font_first(db):
    face = db.faces[0]
    glyphs = extract_glyphs(render_text(face, "Quick", size=60, invert=True))
    matches = rank_fonts(glyphs, db, text="Quick", top=3)
    assert matches[0].face.name == face.name
    assert matches[0].guessed_text == "Quick"


def test_charset_only_letters_and_digits():
    assert all(c.isalnum() for c in CHARSET)
