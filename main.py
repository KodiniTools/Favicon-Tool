import html
import json
import os
from enum import Enum
from pathlib import Path
from urllib.parse import quote

from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import HTMLResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles

from favicon_core import (
    MAX_UPLOAD_BYTES,
    FitMode,
    ImageValidationError,
    UnsupportedFormatError,
    build_ico,
    build_package,
    build_snippet,
    load_image,
    normalize_app_name,
    parse_color,
    parse_sizes,
    parse_style,
    validate_svg,
)

app = FastAPI(title="Favicon Generator")

ROOT_DIR = Path(__file__).parent
STATIC_DIR = ROOT_DIR / "static"
# Gebautes Vue-Frontend (npm run build); deploy.sh testet einen neuen Build über FRONTEND_DIST, bevor er live geht
DIST_DIR = Path(os.environ.get("FRONTEND_DIST") or ROOT_DIR / "dist")


def read_index_template(dist_dir: Path) -> str:
    index = dist_dir / "index.html"
    if not index.is_file():
        raise RuntimeError(f"Frontend fehlt ({index}): zuerst `npm ci && npm run build` ausführen.")
    return index.read_text(encoding="utf-8")


HTML_CONTENT = read_index_template(DIST_DIR)

# JS/CSS des Frontends (Dateinamen mit Hash) sowie Design-Tokens und Schriften; alle Verweise sind
# relativ, damit der Subpath (/favicon-tool/) passt
app.mount("/assets", StaticFiles(directory=DIST_DIR / "assets"), name="assets")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class Lang(str, Enum):
    """Sprache der Fehlermeldungen (Umschalter DE/EN der Navigation)."""

    DE = "de"
    EN = "en"


# Öffentliche URL der Seite (für canonical, hreflang, Open Graph)
SITE_URL = os.environ.get("SITE_URL", "https://kodinitools.com/favicon-tool/")

SEO = {
    Lang.DE: {
        "title": "Favicon Generator – favicon.ico & Favicon-Paket erstellen | KodiniTools",
        "description": (
            "Kostenloser Favicon Generator: Erstelle aus PNG, JPG, WebP, GIF oder BMP ein favicon.ico "
            "oder ein komplettes Favicon-Paket mit Apple-Touch-Icon, Android-Icons und site.webmanifest."
        ),
        "og_locale": "de_DE",
    },
    Lang.EN: {
        "title": "Favicon Generator – Create favicon.ico & favicon package | KodiniTools",
        "description": (
            "Free favicon generator: turn a PNG, JPG, WebP, GIF or BMP into a favicon.ico or a complete "
            "favicon package with Apple touch icon, Android icons and site.webmanifest."
        ),
        "og_locale": "en_US",
    },
}


def page_url(lang: Lang) -> str:
    return SITE_URL if lang is Lang.DE else f"{SITE_URL}?lang=en"


def render_index(template: str, lang: Lang) -> str:
    """Setzt Sprache, Titel und SEO-Metadaten (canonical, hreflang, Open Graph, JSON-LD) in den Head."""
    seo = SEO[lang]
    other = Lang.EN if lang is Lang.DE else Lang.DE
    e = html.escape
    json_ld = json.dumps(
        {
            "@context": "https://schema.org",
            "@type": "WebApplication",
            "name": "Favicon Generator",
            "url": page_url(lang),
            "description": seo["description"],
            "inLanguage": lang.value,
            "applicationCategory": "DesignApplication",
            "operatingSystem": "Any",
            "offers": {"@type": "Offer", "price": "0", "priceCurrency": "EUR"},
            "publisher": {"@type": "Organization", "name": "KodiniTools", "url": "https://kodinitools.com/"},
        },
        ensure_ascii=False,
    ).replace("</", "<\\/")
    head = "\n    ".join(
        [
            f'<meta name="description" content="{e(seo["description"])}">',
            f'<link rel="canonical" href="{e(page_url(lang))}">',
            f'<link rel="alternate" hreflang="de" href="{e(page_url(Lang.DE))}">',
            f'<link rel="alternate" hreflang="en" href="{e(page_url(Lang.EN))}">',
            f'<link rel="alternate" hreflang="x-default" href="{e(page_url(Lang.DE))}">',
            '<meta property="og:type" content="website">',
            '<meta property="og:site_name" content="KodiniTools">',
            f'<meta property="og:title" content="{e(seo["title"])}">',
            f'<meta property="og:description" content="{e(seo["description"])}">',
            f'<meta property="og:url" content="{e(page_url(lang))}">',
            f'<meta property="og:locale" content="{seo["og_locale"]}">',
            f'<meta property="og:locale:alternate" content="{SEO[other]["og_locale"]}">',
            '<meta name="twitter:card" content="summary">',
            f'<script type="application/ld+json">{json_ld}</script>',
        ]
    )
    title_de = f"<title>{e(SEO[Lang.DE]['title'], quote=False)}</title>"
    for marker in ('<html lang="de">', title_de, "<!--SEO-->"):
        if template.count(marker) != 1:
            raise RuntimeError(f"index.html: Platzhalter fehlt oder doppelt: {marker}")
    return (
        template.replace('<html lang="de">', f'<html lang="{lang.value}">')
        .replace(title_de, f"<title>{e(seo['title'], quote=False)}</title>")
        .replace("<!--SEO-->", head)
    )


HTML_PAGES = {lang: render_index(HTML_CONTENT, lang) for lang in Lang}


async def read_limited(file: UploadFile, lang: Lang = Lang.DE) -> bytes:
    data = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        detail = "File too large (max. 10 MB)" if lang is Lang.EN else "Datei zu groß (max. 10 MB)"
        raise HTTPException(status_code=413, detail=detail)
    return data


def to_http_error(err: ImageValidationError, lang: Lang = Lang.DE) -> HTTPException:
    status = 415 if isinstance(err, UnsupportedFormatError) else 400
    prefix = "Error" if lang is Lang.EN else "Fehler"
    return HTTPException(status_code=status, detail=f"{prefix}: {err.localized(lang.value)}")


@app.get("/", response_class=HTMLResponse)
def index(lang: str | None = Query(None)):
    # Unbekannte Werte führen bewusst nicht zu einem Fehler, sondern zur deutschen Seite
    return HTML_PAGES[Lang.EN if lang == "en" else Lang.DE]


@app.get("/health")
def health():
    return {"status": "ok"}


FONT_DIR = STATIC_DIR / "fonts"
FONT_FORMATS = {".woff2": "woff2", ".woff": "woff", ".ttf": "truetype", ".otf": "opentype"}


def list_fonts() -> list[dict[str, str]]:
    """Schriftdateien in static/fonts, bei jedem Aufruf neu gelesen (neue Dateien erscheinen ohne Neustart).

    Anzeigename aus dem Dateinamen: "Supreme-Bold.woff2" -> "Supreme Bold".
    """
    fonts = []
    for path in sorted(FONT_DIR.iterdir(), key=lambda p: p.name.lower()) if FONT_DIR.is_dir() else []:
        fmt = FONT_FORMATS.get(path.suffix.lower())
        if fmt is None or path.name.startswith(".") or not path.is_file():
            continue
        label = " ".join(path.stem.replace("_", "-").split("-")).strip() or path.stem
        fonts.append({"label": label, "url": f"static/fonts/{quote(path.name)}", "format": fmt})
    return fonts


@app.get("/fonts")
def fonts():
    return list_fonts()


@app.post("/convert")
async def convert(
    file: UploadFile = File(...),
    sizes: str | None = Form(None),
    fit: FitMode = Form(FitMode.PAD),
    background: str | None = Form(None),
    padding: str | None = Form(None),
    radius: str | None = Form(None),
    lang: Lang = Form(Lang.DE),
):
    data = await read_limited(file, lang)
    try:
        size_list = parse_sizes(sizes)
        style = parse_style(background, padding, radius)
        img = await run_in_threadpool(load_image, data)
        ico = await run_in_threadpool(build_ico, img, size_list, fit, style)
    except ImageValidationError as e:
        raise to_http_error(e, lang) from None

    return Response(
        content=ico,
        media_type="image/x-icon",
        headers={"Content-Disposition": "attachment; filename=favicon.ico"},
    )


@app.post("/package")
async def package(
    file: UploadFile = File(...),
    fit: FitMode = Form(FitMode.PAD),
    app_name: str | None = Form(None),
    background: str | None = Form(None),
    padding: str | None = Form(None),
    radius: str | None = Form(None),
    theme_color: str | None = Form(None),
    svg: str | None = Form(None),
    lang: Lang = Form(Lang.DE),
):
    data = await read_limited(file, lang)
    try:
        name = normalize_app_name(app_name)
        style = parse_style(background, padding, radius)
        theme = parse_color(theme_color, "Theme-Farbe", "Theme color")
        svg_source = validate_svg(svg)
        img = await run_in_threadpool(load_image, data)
        archive = await run_in_threadpool(build_package, img, fit, name, style, theme, svg_source)
    except ImageValidationError as e:
        raise to_http_error(e, lang) from None

    return Response(
        content=archive,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=favicon-package.zip"},
    )


@app.get("/snippet", response_class=PlainTextResponse)
def snippet(theme_color: str | None = Query(None), svg: bool = Query(False), lang: Lang = Query(Lang.DE)):
    """HTML-Snippet für den <head>, wie es im Paket als favicon-snippet.html liegt."""
    try:
        return build_snippet(parse_color(theme_color, "Theme-Farbe", "Theme color"), svg=svg)
    except ImageValidationError as e:
        raise to_http_error(e, lang) from None
