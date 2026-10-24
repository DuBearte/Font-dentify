from pathlib import Path

import pytest

from fontdentify.fingerprint import build_database
from fontdentify.scanner import scan_fonts

# Fonts that are reliably available on Linux containers and most desktops.
FONT_DIRS = [Path("/usr/share/fonts"), Path("C:/Windows/Fonts")]


@pytest.fixture(scope="session")
def faces():
    found = scan_fonts([d for d in FONT_DIRS if d.is_dir()])
    if len(found) < 3:
        pytest.skip("not enough system fonts available for tests")
    return found


@pytest.fixture(scope="session")
def db(faces):
    # Cap the number of fonts so the test suite stays fast.
    return build_database(faces[:60])
