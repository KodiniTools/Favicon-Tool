import io
import json
import os
import re
import subprocess
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

import favicon_core
from favicon_core import FitMode, ImageValidationError, make_square, parse_sizes
from main import app

client = TestClient(app)


def image_bytes(size=(100, 50), fmt="PNG", mode="RGBA", color=(255, 0, 0, 255)) -> bytes:
    img = Image.new(mode, size, color if mode == "RGBA" else color[:3])
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return buf.getvalue()


def ico_sizes(data: bytes) -> set[tuple[int, int]]:
    return Image.open(io.BytesIO(data)).info["sizes"]


def post(endpoint, data: bytes, filename="logo.png", **fields):
    return client.post(endpoint, files={"file": (filename, data, "image/png")}, data=fields)


# --- parse_sizes -------------------------------------------------------------

def test_parse_sizes_default():
    assert parse_sizes(None) == (16, 32, 48, 64)
    assert parse_sizes("  ") == (16, 32, 48, 64)


def test_parse_sizes_sorted_and_deduplicated():
    assert parse_sizes("48, 16,16,256") == (16, 48, 256)


@pytest.mark.parametrize("raw", ["abc", "17", "512", ",", "0"])
def test_parse_sizes_invalid(raw):
    with pytest.raises(ImageValidationError):
        parse_sizes(raw)


# --- make_square -------------------------------------------------------------

def test_make_square_pad_keeps_full_image_transparent_edges():
    img = Image.new("RGBA", (100, 50), (255, 0, 0, 255))
    sq = make_square(img, FitMode.PAD, 16)
    assert sq.size == (100, 100)
    assert sq.getpixel((50, 0))[3] == 0  # aufgefüllter Rand transparent
    assert sq.getpixel((50, 50)) == (255, 0, 0, 255)


def test_make_square_crop():
    img = Image.new("RGBA", (100, 50), (255, 0, 0, 255))
    sq = make_square(img, FitMode.CROP, 16)
    assert sq.size == (50, 50)
    assert sq.getpixel((0, 0)) == (255, 0, 0, 255)


def test_make_square_upscales_small_images():
    img = Image.new("RGBA", (10, 10))
    assert make_square(img, FitMode.PAD, 64).size == (64, 64)


# --- /convert ------------------------------------------------------------------

def test_index():
    res = client.get("/")
    assert res.status_code == 200
    assert "Favicon Konverter" in res.text


def test_convert_default_sizes_backward_compatible():
    res = post("/convert", image_bytes((256, 256)))
    assert res.status_code == 200
    assert res.headers["content-type"] == "image/x-icon"
    assert ico_sizes(res.content) == {(16, 16), (32, 32), (48, 48), (64, 64)}


def test_convert_non_square_and_small_image_contains_all_sizes():
    # Vorher: nur ein verzerrtes 16x8-Icon
    res = post("/convert", image_bytes((40, 20)))
    assert res.status_code == 200
    assert ico_sizes(res.content) == {(16, 16), (32, 32), (48, 48), (64, 64)}


def test_convert_custom_sizes_and_crop():
    res = post("/convert", image_bytes((300, 100)), sizes="16,256", fit="crop")
    assert res.status_code == 200
    assert ico_sizes(res.content) == {(16, 16), (256, 256)}


def test_convert_jpeg_rgb():
    res = post("/convert", image_bytes((64, 64), fmt="JPEG", mode="RGB"), filename="a.jpg")
    assert res.status_code == 200


def test_convert_invalid_size_param():
    res = post("/convert", image_bytes(), sizes="999")
    assert res.status_code == 400
    assert "nicht erlaubt" in res.json()["detail"].lower()


def test_convert_invalid_fit_param():
    assert post("/convert", image_bytes(), fit="stretch").status_code == 422


def test_convert_not_an_image():
    res = post("/convert", b"hello world", filename="x.png")
    assert res.status_code == 415


def test_convert_empty_file():
    assert post("/convert", b"").status_code == 400


def test_convert_unsupported_format():
    buf = io.BytesIO()
    Image.new("RGB", (32, 32)).save(buf, format="TIFF")
    assert post("/convert", buf.getvalue(), filename="a.tiff").status_code == 415


def test_convert_too_large_upload(monkeypatch):
    monkeypatch.setattr("main.MAX_UPLOAD_BYTES", 100)
    assert post("/convert", image_bytes((256, 256))).status_code == 413


def test_convert_too_many_pixels(monkeypatch):
    monkeypatch.setattr(favicon_core, "MAX_PIXELS", 100)
    res = post("/convert", image_bytes((20, 20)))
    assert res.status_code == 400
    assert "abmessungen" in res.json()["detail"].lower()


def test_error_messages_english_with_lang_en():
    res = post("/convert", image_bytes(), sizes="999", lang="en")
    assert res.status_code == 400
    assert res.json()["detail"].startswith("Error: Size 999 not allowed")
    res = post("/convert", b"hello world", filename="x.png", lang="en")
    assert res.json()["detail"] == "Error: File is not a valid image"
    res = post("/package", image_bytes((40, 10)), app_name="x" * 61, lang="en")
    assert res.json()["detail"].startswith("Error: App name too long")


def test_error_messages_default_german_and_invalid_lang():
    assert post("/convert", b"").json()["detail"] == "Fehler: Leere Datei"
    assert post("/convert", b"", lang="de").json()["detail"] == "Fehler: Leere Datei"
    assert post("/convert", image_bytes(), lang="fr").status_code == 422


def test_too_large_upload_english(monkeypatch):
    monkeypatch.setattr("main.MAX_UPLOAD_BYTES", 100)
    res = post("/package", image_bytes((256, 256)), lang="en")
    assert res.status_code == 413
    assert res.json()["detail"] == "File too large (max. 10 MB)"


def test_success_with_lang_en_small_non_square():
    res = post("/convert", image_bytes((7, 3)), sizes="16,32", lang="en")
    assert res.status_code == 200
    assert ico_sizes(res.content) == {(16, 16), (32, 32)}


def test_validation_error_localized():
    err = ImageValidationError("Leere Datei", "Empty file")
    assert str(err) == "Leere Datei"
    assert err.localized("en") == "Empty file"
    assert err.localized("de") == "Leere Datei"
    assert ImageValidationError("Nur deutsch").localized("en") == "Nur deutsch"


def test_index_has_i18n_like_collage_maker():
    html = client.get("/").text
    assert "localStorage.getItem('locale')" in html
    assert "'locale-changed'" in html and ".global-nav-lang-btn" in html
    assert "Favicon Converter" in html and "Choose a file or drag it here" in html
    assert "formData.append('lang', locale)" in html


# --- /package ------------------------------------------------------------------

def test_package_contents():
    res = post("/package", image_bytes((300, 200)), app_name="Meine Seite")
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/zip"

    zf = zipfile.ZipFile(io.BytesIO(res.content))
    expected = {
        "favicon.ico": None,
        "favicon-16x16.png": (16, 16),
        "favicon-32x32.png": (32, 32),
        "apple-touch-icon.png": (180, 180),
        "android-chrome-192x192.png": (192, 192),
        "android-chrome-512x512.png": (512, 512),
        "site.webmanifest": None,
        "favicon-snippet.html": None,
    }
    assert set(zf.namelist()) == set(expected)
    for name, size in expected.items():
        if size:
            assert Image.open(io.BytesIO(zf.read(name))).size == size

    assert ico_sizes(zf.read("favicon.ico")) == {(16, 16), (32, 32), (48, 48)}
    assert Image.open(io.BytesIO(zf.read("apple-touch-icon.png"))).mode == "RGB"

    manifest = json.loads(zf.read("site.webmanifest"))
    assert manifest["name"] == "Meine Seite"
    assert len(manifest["icons"]) == 2


def test_package_app_name_too_long():
    assert post("/package", image_bytes(), app_name="x" * 61).status_code == 400


# --- Design System / Partials ------------------------------------------------

def test_index_uses_design_system_and_partials():
    html = client.get("/").text
    assert 'href="static/design-system/tokens-v2.css"' in html
    for partial in ("nav", "footer", "cookie-banner"):
        assert f'<!--#include virtual="/partials/{partial}.html" -->' in html
    # App-Inhalt liegt in #app, damit die Partial-Regeln ihn nicht treffen
    assert '<main id="app">' in html
    # Farben nur über Tokens; feste Hex-Werte allein in den theme-color-Metas
    style = html[html.index("<style>"):html.index("</style>")]
    assert not re.search(r"#[0-9a-fA-F]{3,8}\b", style)


def test_static_tokens_and_fonts_served():
    css = client.get("/static/design-system/tokens-v2.css")
    assert css.status_code == 200
    assert css.headers["content-type"].startswith("text/css")
    assert "--ds-accent:" in css.text and ":root[data-theme='light']" in css.text
    for weight in ("Regular", "Medium", "Bold"):
        font = client.get(f"/static/fonts/Supreme-{weight}.woff2")
        assert font.status_code == 200
        assert font.content[:4] == b"wOF2"


# --- deploy.sh -----------------------------------------------------------------

def test_deploy_script_is_executable_and_valid_bash():
    script = Path(__file__).resolve().parent.parent / "deploy.sh"
    assert os.access(script, os.X_OK)
    assert subprocess.run(["bash", "-n", str(script)]).returncode == 0
