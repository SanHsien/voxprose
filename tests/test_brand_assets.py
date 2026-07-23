import struct
from pathlib import Path


ASSETS = Path(__file__).resolve().parents[1] / "assets"


def _png_metadata(path):
    data = path.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    assert data[12:16] == b"IHDR"
    width, height = struct.unpack(">II", data[16:24])
    color_type = data[25]
    return width, height, color_type


def test_primary_icon_is_large_rgba_png():
    width, height, color_type = _png_metadata(ASSETS / "icon.png")

    assert width == height
    assert width >= 512
    assert color_type == 6  # RGBA


def test_tray_icon_is_rgba_png():
    width, height, color_type = _png_metadata(ASSETS / "icon-menubar-w.png")

    assert (width, height) == (256, 256)
    assert color_type == 6


def test_windows_icon_contains_multiple_sizes():
    reserved, icon_type, image_count = struct.unpack(
        "<HHH", (ASSETS / "icon.ico").read_bytes()[:6]
    )

    assert reserved == 0
    assert icon_type == 1
    assert image_count >= 7
