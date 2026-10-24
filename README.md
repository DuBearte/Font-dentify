# Font-dentify

Identify the font in a picture by matching it against the fonts **installed on your own machine**.

Give it a screenshot or photo of some text and it tells you which of your installed fonts
it most likely is. Works on Windows, Linux, and macOS.

## How it works

1. **Scan.** The tool finds every font file in your system font folders
   (for example `C:\Windows\Fonts` on Windows or `/usr/share/fonts` on Linux).
2. **Fingerprint.** For each font it draws the letters A-Z, a-z and 0-9, shrinks each one
   into a small 24x24 image, and stores those images. This is your local font database.
3. **Read the picture.** The picture is turned into black-and-white, then split into lines
   and individual letters by looking for empty rows and columns.
4. **Compare.** Each letter from the picture is compared with every letter of every font.
   The fonts whose letters look most alike come out on top, as a ranked list.

No internet connection, no cloud service, and nothing leaves your computer.

## Install

Python 3.9 or newer is required.

```bash
pip install -e .
```

## Use

```bash
# See which fonts the tool can find on your machine
fontdentify scan

# Build the fingerprint database (run once, and again after installing new fonts)
fontdentify index

# Identify the font in a picture
fontdentify identify screenshot.png

# If you know what the picture says, tell the tool. This makes matching much more accurate.
fontdentify identify screenshot.png --text "Hello World"
```

Example output:

```
Found 9 letters. Best matches among 106 installed fonts:

1. DejaVu Serif Bold                         96.9%   read as: Hellomrld
2. Caladea Bold                              93.5%   read as: nellomrld
3. Liberation Serif Bold                     92.1%   read as: HelloWrld
```

The "read as" column shows which letters the tool thinks it saw. It is a quick way to check
that the picture was split into letters correctly.

## Tips for good results

- **Screenshots work best.** Photos work too if they are sharp, straight, and evenly lit.
- **Crop to the text.** Logos, borders, and other graphics confuse the letter splitter.
- **Letters that touch** (tight kerning, script fonts) get treated as one shape.
  The tool still ranks fonts, but accuracy drops and the `--text` hint is ignored.
- **Look at the top few,** not just the first. Many fonts are near-identical
  (Arial and Liberation Sans, for example).

## Project layout

| File | What it does |
|------|--------------|
| `fontdentify/paths.py` | Font folders and cache folder for each operating system |
| `fontdentify/scanner.py` | Finds font files and reads their family and style names |
| `fontdentify/glyphs.py` | Shrinks a letter image into a fixed-size fingerprint |
| `fontdentify/fingerprint.py` | Builds, saves, and loads the font database |
| `fontdentify/segment.py` | Turns a picture into separate letter images |
| `fontdentify/matcher.py` | Compares letters with the database and ranks the fonts |
| `fontdentify/cli.py` | The `fontdentify` command |

## Running the tests

```bash
pip install -e ".[dev]"
pytest
```

The tests render text in fonts found on the machine and check that the tool identifies them.

## Ideas for later

- Smarter letter splitting that separates touching letters.
- Optional OCR (such as Tesseract) to read the text automatically instead of guessing.
- A small desktop window with drag-and-drop instead of the command line.
- Straightening photos taken at an angle.
