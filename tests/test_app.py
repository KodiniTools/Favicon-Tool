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
from favicon_core import (
    FitMode,
    IconStyle,
    ImageValidationError,
    apply_style,
    make_square,
    parse_color,
    parse_sizes,
    parse_style,
)
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
        "android-chrome-maskable-192x192.png": (192, 192),
        "android-chrome-maskable-512x512.png": (512, 512),
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
    assert len(manifest["icons"]) == 4
    assert [i.get("purpose") for i in manifest["icons"]] == [None, None, "maskable", "maskable"]
    # Ohne Optionen unverändert weiß
    assert manifest["theme_color"] == manifest["background_color"] == "#ffffff"
    assert zf.read("favicon-snippet.html").decode() == favicon_core.SNIPPET_HTML


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
    style = html[html.index("<style>") : html.index("</style>")]
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
    text = script.read_text(encoding="utf-8")
    assert 'HEALTH_URL-http://127.0.0.1:8005/}"' in text
    assert '"${HEALTH_URL%/}/health"' in text


# --- Paket 1: /health, SEO, Barrierefreiheit, Projekt-Setup ---------------------

ROOT = Path(__file__).resolve().parent.parent


def test_health():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


def head(html: str) -> str:
    return html[: html.index("</head>")]


def test_index_seo_german_default():
    for url in ("/", "/?lang=de", "/?lang=fr"):
        h = head(client.get(url).text)
        assert '<html lang="de">' in h
        assert "<title>Favicon Generator – favicon.ico &amp; Favicon-Paket erstellen | KodiniTools</title>" in h
        assert '<meta name="description" content="Kostenloser Favicon Generator' in h
        assert '<link rel="canonical" href="https://kodinitools.com/favicon-tool/">' in h
        assert '<meta property="og:locale" content="de_DE">' in h
        assert "<!--SEO-->" not in h


def test_index_seo_english():
    h = head(client.get("/?lang=en").text)
    assert '<html lang="en">' in h
    assert "<title>Favicon Generator – Create favicon.ico &amp; favicon package | KodiniTools</title>" in h
    assert '<meta name="description" content="Free favicon generator' in h
    assert '<link rel="canonical" href="https://kodinitools.com/favicon-tool/?lang=en">' in h
    assert '<meta property="og:locale" content="en_US">' in h


def test_index_hreflang_and_json_ld():
    for url in ("/", "/?lang=en"):
        h = head(client.get(url).text)
        assert '<link rel="alternate" hreflang="de" href="https://kodinitools.com/favicon-tool/">' in h
        assert '<link rel="alternate" hreflang="en" href="https://kodinitools.com/favicon-tool/?lang=en">' in h
        assert '<link rel="alternate" hreflang="x-default" href="https://kodinitools.com/favicon-tool/">' in h
        ld = re.search(r'<script type="application/ld\+json">(.*?)</script>', h).group(1)
        data = json.loads(ld)
        assert data["@type"] == "WebApplication"
        assert data["inLanguage"] in ("de", "en")


def test_render_index_requires_placeholders():
    import main

    with pytest.raises(RuntimeError):
        main.render_index('<html lang="de"><head></head></html>', main.Lang.EN)


def test_file_input_keyboard_accessible():
    html = client.get("/").text
    style = html[html.index("<style>") : html.index("</style>")]
    assert 'input[type="file"] { display: none; }' not in style
    assert "clip-path: inset(50%)" in style


def test_requirements_pinned():
    for name in ("requirements.txt", "requirements-dev.txt"):
        for line in (ROOT / name).read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith(("#", "-r")):
                assert re.fullmatch(r"[A-Za-z0-9_.\-]+==[0-9][0-9A-Za-z.]*", line), line


def test_ci_workflow_runs_pytest_and_ruff():
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    for cmd in ("pytest -q", "ruff check .", "ruff format --check ."):
        assert cmd in ci


# --- Paket 2: Gestaltung, maskable, Manifest-Farben, Snippet --------------------


def test_apply_style_default_is_noop():
    img = Image.new("RGBA", (64, 64), (255, 0, 0, 255))
    assert apply_style(img, IconStyle()) is img


def test_apply_style_padding_background_radius():
    img = Image.new("RGBA", (100, 100), (255, 0, 0, 255))
    padded = apply_style(img, IconStyle(padding=20))
    assert padded.size == (100, 100)
    assert padded.getpixel((5, 5))[3] == 0  # Rand transparent
    assert padded.getpixel((50, 50)) == (255, 0, 0, 255)

    with_bg = apply_style(img, IconStyle(background="#00ff00", padding=20))
    assert with_bg.getpixel((5, 5)) == (0, 255, 0, 255)

    rounded = apply_style(img, IconStyle(background="#00ff00", radius=50))
    assert rounded.getpixel((0, 0))[3] == 0  # Ecke abgerundet
    assert rounded.getpixel((50, 50))[3] == 255
    assert rounded.getpixel((50, 1))[3] > 0  # Kantenmitte bleibt


def test_parse_color_and_style_validation():
    assert parse_color(None) is None
    assert parse_color("  ") is None
    assert parse_color("#A1b2C3") == "#a1b2c3"
    for bad in ("red", "#fff", "#12345g", "123456"):
        with pytest.raises(ImageValidationError):
            parse_color(bad)
    assert parse_style(None, None, None) == IconStyle()
    assert parse_style("#000000", "40", "50") == IconStyle("#000000", 40, 50)
    for padding, radius in (("41", "0"), ("-1", "0"), ("0", "51"), ("x", "0"), ("1.5", "0")):
        with pytest.raises(ImageValidationError):
            parse_style(None, padding, radius)


def test_convert_with_style_non_square_small_image():
    res = post("/convert", image_bytes((9, 4)), sizes="16,32", background="#112233", padding="10", radius="25")
    assert res.status_code == 200
    ico = Image.open(io.BytesIO(res.content))
    assert ico.info["sizes"] == {(16, 16), (32, 32)}
    ico.size = (32, 32)
    frame = ico.convert("RGBA")
    assert frame.getpixel((0, 0))[3] == 0  # runde Ecke
    assert frame.getpixel((16, 2))[:3] == (0x11, 0x22, 0x33)  # Hintergrund im Innenabstand


def test_convert_invalid_style_localized():
    res = post("/convert", image_bytes(), padding="99", lang="en")
    assert res.status_code == 400
    assert res.json()["detail"] == "Error: Padding must be between 0 and 40"
    res = post("/convert", image_bytes(), background="blau")
    assert res.status_code == 400
    assert "Hintergrundfarbe ungültig" in res.json()["detail"]


def test_package_with_style_and_theme_color():
    res = post(
        "/package",
        image_bytes((40, 20), color=(255, 0, 0, 255)),
        background="#0000ff",
        padding="10",
        radius="50",
        theme_color="#ABCDEF",
    )
    assert res.status_code == 200
    zf = zipfile.ZipFile(io.BytesIO(res.content))
    manifest = json.loads(zf.read("site.webmanifest"))
    assert manifest["theme_color"] == "#abcdef"
    assert manifest["background_color"] == "#0000ff"
    assert '<meta name="theme-color" content="#abcdef">' in zf.read("favicon-snippet.html").decode()

    # Apple: deckend, ohne Eckenradius (iOS rundet selbst), Hintergrund = gewählte Farbe
    apple = Image.open(io.BytesIO(zf.read("apple-touch-icon.png")))
    assert apple.mode == "RGB"
    assert apple.getpixel((0, 0)) == (0, 0, 255)

    # Android: abgerundet -> Ecke transparent
    android = Image.open(io.BytesIO(zf.read("android-chrome-512x512.png"))).convert("RGBA")
    assert android.getpixel((0, 0))[3] == 0

    # Maskable: vollflächig, Motiv nur innerhalb der Safe Zone (Kreis mit 40 % Radius)
    mask = Image.open(io.BytesIO(zf.read("android-chrome-maskable-512x512.png")))
    assert mask.mode == "RGB"
    assert mask.getpixel((0, 0)) == (0, 0, 255)
    assert mask.getpixel((256, 256)) == (255, 0, 0)
    for x, y in ((256, 20), (20, 256), (256, 490)):
        assert mask.getpixel((x, y)) == (0, 0, 255)


def test_package_invalid_theme_color():
    res = post("/package", image_bytes(), theme_color="#zzzzzz", lang="en")
    assert res.status_code == 400
    assert res.json()["detail"].startswith("Error: Theme color invalid")


def test_snippet_endpoint():
    res = client.get("/snippet")
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("text/plain")
    assert res.text == favicon_core.SNIPPET_HTML
    res = client.get("/snippet", params={"theme_color": "#123456"})
    assert res.text.endswith('<meta name="theme-color" content="#123456">\n')
    assert client.get("/snippet", params={"theme_color": "x"}).status_code == 400


# --- Paket 3: SVG, Text/Emoji, Vorschau ------------------------------------------

SVG_OK = (
    '<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 10 10">'
    '<defs><linearGradient id="g"><stop offset="0" stop-color="red"/></linearGradient></defs>'
    '<rect width="10" height="10" fill="url(#g)"/><use xlink:href="#g"/>'
    "<style>rect { fill: url(#g); }</style></svg>"
)


def test_validate_svg_accepts_plain_svg():
    assert favicon_core.validate_svg(None) is None
    assert favicon_core.validate_svg("  ") is None
    assert favicon_core.validate_svg(SVG_OK) == SVG_OK
    assert favicon_core.validate_svg('<svg viewBox="0 0 1 1"/>') is not None  # ohne Namespace


@pytest.mark.parametrize(
    "svg",
    [
        '<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>',
        '<svg xmlns="http://www.w3.org/2000/svg" onload="alert(1)"/>',
        '<svg xmlns="http://www.w3.org/2000/svg"><foreignObject/></svg>',
        '<svg xmlns="http://www.w3.org/2000/svg"><image href="https://example.com/a.png"/></svg>',
        '<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">'
        '<use xlink:href="https://example.com/x.svg#a"/></svg>',
        '<svg xmlns="http://www.w3.org/2000/svg"><a href="javascript:alert(1)"><rect/></a></svg>',
        '<svg xmlns="http://www.w3.org/2000/svg"><rect style="fill: url(https://e.com/x)"/></svg>',
        '<svg xmlns="http://www.w3.org/2000/svg"><style>@import url(https://e.com/x.css);</style></svg>',
        '<!DOCTYPE svg [<!ENTITY x "y">]><svg xmlns="http://www.w3.org/2000/svg">&x;</svg>',
        "<html><body/></html>",
        "<svg",
    ],
)
def test_validate_svg_rejects_unsafe_or_invalid(svg):
    with pytest.raises(ImageValidationError):
        favicon_core.validate_svg(svg)


def test_validate_svg_too_large(monkeypatch):
    monkeypatch.setattr(favicon_core, "SVG_MAX_BYTES", 10)
    with pytest.raises(ImageValidationError):
        favicon_core.validate_svg(SVG_OK)


def test_package_with_svg():
    res = post("/package", image_bytes((64, 32)), svg=SVG_OK)
    assert res.status_code == 200
    zf = zipfile.ZipFile(io.BytesIO(res.content))
    assert zf.read("favicon.svg").decode() == SVG_OK
    snippet = zf.read("favicon-snippet.html").decode()
    assert '<link rel="icon" type="image/svg+xml" href="/favicon.svg">' in snippet
    # Chrome würde ein ICO mit sizes="any" dem SVG vorziehen
    assert 'href="/favicon.ico" sizes="32x32"' in snippet and 'sizes="any"' not in snippet


def test_package_without_svg_unchanged():
    zf = zipfile.ZipFile(io.BytesIO(post("/package", image_bytes(), svg="").content))
    assert "favicon.svg" not in zf.namelist()
    assert zf.read("favicon-snippet.html").decode() == favicon_core.SNIPPET_HTML


def test_package_rejects_unsafe_svg_localized():
    bad = '<svg xmlns="http://www.w3.org/2000/svg" onload="x()"/>'
    res = post("/package", image_bytes(), svg=bad, lang="en")
    assert res.status_code == 400
    assert res.json()["detail"].startswith("Error: SVG contains disallowed content")


def test_snippet_endpoint_svg():
    text = client.get("/snippet", params={"svg": "true", "theme_color": "#000000"}).text
    lines = text.splitlines()
    assert lines[0] == '<link rel="icon" href="/favicon.ico" sizes="32x32">'
    assert lines[1] == '<link rel="icon" type="image/svg+xml" href="/favicon.svg">'
    assert lines[-1] == '<meta name="theme-color" content="#000000">'


def test_index_offers_text_mode_svg_and_mockups():
    html = client.get("/").text
    assert 'name="mode" value="text"' in html
    assert "image/svg+xml" in html
    for el in ("mkTabLight", "mkTabDark", "mkIos", "mkAndroid"):
        assert f'id="{el}"' in html
