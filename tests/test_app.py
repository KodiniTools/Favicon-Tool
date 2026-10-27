import base64
import io
import json
import os
import re
import subprocess
import xml.etree.ElementTree as ET
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
from main import STATIC_DIR, app

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


def test_convert_format_png_single_size():
    res = post("/convert", image_bytes((100, 50)), sizes="32", format="png")
    assert res.status_code == 200
    assert res.headers["content-type"] == "image/png"
    assert "filename=favicon-32x32.png" in res.headers["content-disposition"]
    img = Image.open(io.BytesIO(res.content))
    assert img.format == "PNG" and img.size == (32, 32)
    # pad: transparente Ränder bleiben erhalten
    assert img.convert("RGBA").getpixel((0, 0))[3] == 0


def test_convert_format_webp_multiple_sizes_zip():
    res = post("/convert", image_bytes((64, 64)), sizes="48,16", format="webp")
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/zip"
    assert "filename=favicon-webp.zip" in res.headers["content-disposition"]
    with zipfile.ZipFile(io.BytesIO(res.content)) as zf:
        assert sorted(zf.namelist()) == ["favicon-16x16.webp", "favicon-48x48.webp"]
        img = Image.open(io.BytesIO(zf.read("favicon-48x48.webp")))
        assert img.format == "WEBP" and img.size == (48, 48)


def test_convert_format_ico_explicit_and_invalid():
    res = post("/convert", image_bytes((64, 64)), format="ico")
    assert res.headers["content-type"] == "image/x-icon"
    assert "filename=favicon.ico" in res.headers["content-disposition"]
    assert post("/convert", image_bytes(), format="tiff").status_code == 422


@pytest.mark.parametrize("fmt", ["gif", "bmp"])
def test_convert_format_gif_bmp(fmt):
    res = post("/convert", image_bytes((100, 50)), sizes="32", format=fmt)
    assert res.status_code == 200
    assert res.headers["content-type"] == f"image/{fmt}"
    assert f"filename=favicon-32x32.{fmt}" in res.headers["content-disposition"]
    img = Image.open(io.BytesIO(res.content))
    assert img.format == fmt.upper() and img.size == (32, 32)


def test_gif_keeps_transparency_bmp_uses_background():
    img = Image.new("RGBA", (40, 20), (255, 0, 0, 255))
    gif, _, _ = favicon_core.build_icons(img, (32,), FitMode.PAD, None, favicon_core.OutputFormat.GIF)
    assert Image.open(io.BytesIO(gif)).convert("RGBA").getpixel((0, 0))[3] == 0
    bmp, _, _ = favicon_core.build_icons(img, (32,), FitMode.PAD, None, favicon_core.OutputFormat.BMP)
    assert Image.open(io.BytesIO(bmp)).convert("RGB").getpixel((0, 0)) == (255, 255, 255)
    styled = IconStyle(background="#00ff00")
    bmp, _, _ = favicon_core.build_icons(img, (32,), FitMode.PAD, styled, favicon_core.OutputFormat.BMP)
    assert Image.open(io.BytesIO(bmp)).convert("RGB").getpixel((0, 0)) == (0, 255, 0)


def test_convert_format_svg_embeds_raster():
    res = post("/convert", image_bytes((64, 64)), sizes="16,32", format="svg")
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("image/svg+xml")
    assert "filename=favicon.svg" in res.headers["content-disposition"]
    root = ET.fromstring(res.content)
    assert root.get("viewBox") == "0 0 256 256"
    image = root.find("{http://www.w3.org/2000/svg}image")
    href = image.get("href")
    assert href.startswith("data:image/png;base64,")
    png = Image.open(io.BytesIO(base64.b64decode(href.split(",", 1)[1])))
    assert png.size == (256, 256)


def test_convert_format_svg_returns_original_svg_without_style():
    svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><rect width="10" height="10"/></svg>'
    res = post("/convert", image_bytes((64, 64)), format="svg", svg=svg)
    assert res.text == svg
    # mit Gestaltung: eingebettetes Raster, damit die Gestaltung erhalten bleibt
    res = post("/convert", image_bytes((64, 64)), format="svg", svg=svg, background="#ffffff")
    assert "data:image/png;base64," in res.text
    # unsicheres SVG wird abgelehnt
    bad = '<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'
    assert post("/convert", image_bytes((64, 64)), format="svg", svg=bad).status_code == 400


def test_build_icons_applies_style():
    content, media, name = favicon_core.build_icons(
        Image.new("RGBA", (10, 10), (0, 0, 0, 0)),
        (16,),
        FitMode.PAD,
        IconStyle(background="#ff0000"),
        favicon_core.OutputFormat.PNG,
    )
    assert (media, name) == ("image/png", "favicon-16x16.png")
    assert Image.open(io.BytesIO(content)).convert("RGBA").getpixel((8, 8)) == (255, 0, 0, 255)


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


def index_asset(kind: str) -> str:
    """Inhalt der vom Vite-Build eingebundenen JS- bzw. CSS-Datei (über /assets ausgeliefert)."""
    html = client.get("/").text
    pattern = r'src="\./(assets/[^"]+\.js)"' if kind == "js" else r'href="\./(assets/[^"]+\.css)"'
    match = re.search(pattern, html)
    assert match, f"kein {kind}-Bundle in index.html"
    res = client.get("/" + match.group(1))
    assert res.status_code == 200
    return res.text


def test_index_has_i18n_like_collage_maker():
    html = client.get("/").text
    # Pre-Paint-Skript: Sprache vor dem ersten Rendern aus ?lang= / localStorage
    assert "localStorage.getItem('locale')" in html
    js = index_asset("js")
    assert "locale-changed" in js and ".global-nav-lang-btn" in js
    assert "Favicon Converter" in js and "Choose a file or drag it here" in js


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
    for partial in ("nav", "footer", "cookie-banner"):
        assert f'<!--#include virtual="/partials/{partial}.html" -->' in html
    # Vue-App mountet in #app, damit die Partial-Regeln sie nicht treffen
    assert '<main id="app">' in html
    assert '<script type="module" crossorigin src="./assets/' in html
    css = index_asset("css")
    # Design-Tokens sind im Bundle; Farben nur über Tokens (Hex-Werte nur in tokens + theme-color-Metas)
    assert "--ds-accent:" in css
    assert "var(--ds-accent)" in css


def test_read_index_template_requires_build(tmp_path):
    import main

    with pytest.raises(RuntimeError, match="npm run build"):
        main.read_index_template(tmp_path)
    (tmp_path / "index.html").write_text("<html></html>", encoding="utf-8")
    assert main.read_index_template(tmp_path) == "<html></html>"


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
    assert 'curl -fsS -o /dev/null "$url/health"' in text
    # curl-Fehler während des Neustarts unterdrückt, beim letzten Versuch sichtbar
    assert 'check_health "$HEALTH_URL" 2>/dev/null' in text


def test_deploy_check_health_function():
    """check_health aus deploy.sh gegen einen nicht erreichbaren Port: Fehlschlag ohne Abbruch des Skripts."""
    script = ROOT / "deploy.sh"
    body = script.read_text(encoding="utf-8").replace('main "$@"', "")
    res = subprocess.run(
        ["bash", "-c", body + "\ncheck_health http://127.0.0.1:9/ 2>/dev/null && echo up || echo down"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert res.stdout.strip() == "down"


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


def test_index_og_image_twitter_and_robots():
    for lang in ("de", "en"):
        h = head(client.get(f"/?lang={lang}").text)
        image = f"https://kodinitools.com/favicon-tool/static/favicon-landingpage-{lang}.webp"
        assert f'<meta property="og:image" content="{image}">' in h
        assert '<meta name="twitter:card" content="summary_large_image">' in h
        assert f'<meta name="twitter:image" content="{image}">' in h
        assert '<meta name="robots" content="index, follow, max-image-preview:large">' in h
        ld = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', h).group(1))
        assert ld["screenshot"] == image
        # Bild wird ausgeliefert und passt zu og:image:width/height
        res = client.get(f"/static/favicon-landingpage-{lang}.webp")
        assert res.status_code == 200
        assert Image.open(io.BytesIO(res.content)).size == (1920, 945)


def test_index_server_rendered_content_per_language():
    de = client.get("/").text
    en = client.get("/?lang=en").text
    assert "<!--CONTENT-->" not in de and "<!--CONTENT-->" not in en
    body_de = de[de.index('<main id="app">') : de.index("</main>")]
    body_en = en[en.index('<main id="app">') : en.index("</main>")]
    assert "<h1>Favicon Konverter</h1>" in body_de and "<h2>Funktionen</h2>" in body_de
    assert "<h1>Favicon Converter</h1>" in body_en and "<h2>Features</h2>" in body_en
    assert "Lade ein Bild hoch" not in body_en
    assert body_en.count("<li>") == 4


def test_sitemap_lists_both_languages_with_hreflang():
    res = client.get("/sitemap.xml")
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("application/xml")
    ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9", "x": "http://www.w3.org/1999/xhtml"}
    root = ET.fromstring(res.content)
    locs = [el.text for el in root.findall("s:url/s:loc", ns)]
    assert locs == ["https://kodinitools.com/favicon-tool/", "https://kodinitools.com/favicon-tool/?lang=en"]
    for url in root.findall("s:url", ns):
        links = {link.get("hreflang"): link.get("href") for link in url.findall("x:link", ns)}
        assert links == {"de": locs[0], "en": locs[1], "x-default": locs[0]}


def test_render_index_requires_placeholders():
    import main

    with pytest.raises(RuntimeError):
        main.render_index('<html lang="de"><head></head></html>', main.Lang.EN)


def test_file_input_keyboard_accessible():
    css = index_asset("css")
    assert "display:none" not in css.replace(" ", "").split("type=file]")[-1][:40]
    assert "clip-path:inset(50%)" in css.replace(" ", "")


def test_requirements_pinned():
    for name in ("requirements.txt", "requirements-dev.txt"):
        for line in (ROOT / name).read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith(("#", "-r")):
                assert re.fullmatch(
                    r"[A-Za-z0-9_.\-]+==[0-9][0-9A-Za-z.]*(; python_version [<>]=? \"[0-9.]+\")?", line
                ), line


def test_ci_workflow_runs_pytest_and_ruff():
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    for cmd in ("pytest -q", "ruff check .", "ruff format --check ."):
        assert cmd in ci
    # Frontend: Lint, Typen, Vitest, Build; pytest braucht das gebaute dist/
    for cmd in ("npm run lint", "npm run typecheck", "npm test", "npm ci && npm run build"):
        assert cmd in ci


def test_deploy_builds_frontend_before_switching():
    text = (ROOT / "deploy.sh").read_text(encoding="utf-8")
    build = text.index("npx vite build --outDir dist.new")
    tests = text.index('FRONTEND_DIST="$SCRIPT_DIR/dist.new" "$VPY" -m pytest -q')
    switch = text.index("mv dist.new dist")
    restart = text.index('systemctl restart "$SERVICE"')
    assert build < tests < switch < restart
    assert 'for tool in git "$PYTHON" node npm; do' in text


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
    js = index_asset("js")
    assert "image/svg+xml" in js
    for el in ("mkTabLight", "mkTabDark", "mkIos", "mkAndroid"):
        assert el in js


# --- Eigene Schriften (static/fonts) ---------------------------------------------


def test_fonts_lists_static_fonts_and_urls_are_served():
    res = client.get("/fonts")
    assert res.status_code == 200
    fonts = res.json()
    # Der Ordner wächst laufend; daher nur Vollständigkeit prüfen, keine feste Liste.
    font_files = sorted(
        (p for p in (STATIC_DIR / "fonts").iterdir() if p.suffix.lower() in {".woff2", ".woff", ".ttf", ".otf"}),
        key=lambda p: p.name.lower(),
    )
    assert len(fonts) == len(font_files) > 0
    assert {"Supreme Bold", "Supreme Medium", "Supreme Regular"} <= {f["label"] for f in fonts}
    for font in fonts[:3] + fonts[-3:]:
        assert font["format"] in {"woff2", "woff", "truetype", "opentype"}
        assert client.get("/" + font["url"]).status_code == 200


def test_fonts_new_files_appear_without_restart(monkeypatch, tmp_path):
    import main

    monkeypatch.setattr(main, "FONT_DIR", tmp_path)
    assert client.get("/fonts").json() == []
    for name in ("My Font_Light.ttf", "Zeta-Black.OTF", "a.woff", ".hidden.woff2", "readme.txt"):
        (tmp_path / name).write_bytes(b"x")
    (tmp_path / "sub.woff2").mkdir()
    fonts = client.get("/fonts").json()
    assert fonts == [
        {"label": "a", "url": "static/fonts/a.woff", "format": "woff"},
        {"label": "My Font Light", "url": "static/fonts/My%20Font_Light.ttf", "format": "truetype"},
        {"label": "Zeta Black", "url": "static/fonts/Zeta-Black.OTF", "format": "opentype"},
    ]


def test_fonts_missing_directory(monkeypatch, tmp_path):
    import main

    monkeypatch.setattr(main, "FONT_DIR", tmp_path / "fehlt")
    assert client.get("/fonts").json() == []


def test_index_has_font_picker():
    js = index_asset("js")
    # Eigene Listbox statt <select>, damit jeder Eintrag in seiner Schrift erscheint
    assert "textFontBtn" in js and "textFontList" in js and "listbox" in js
    assert "new FontFace(" in js


def test_app_button_styles_do_not_leak_into_partials():
    # Footer/Cookie-Banner (SSI, außerhalb von #app) nutzen <button> als Link;
    # die App-Button-Stile dürfen dort nicht greifen.
    css = index_asset("css")
    # kein Selektor, der mit "button" beginnt (minifiziert: nach "}", "{" oder ",")
    assert not re.search(r"(^|[{},])\s*button[\s{:.,\[]", css)
    assert ":where(#app) button" in css
    assert "button.footer-link:not([class*=cookie])" in css.replace("'", "").replace('"', "")
