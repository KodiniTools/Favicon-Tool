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
    OutputFormat,
    UnsupportedFormatError,
    build_icons,
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
            "Kostenloser Favicon Generator: Erstelle aus PNG, JPG, WebP, GIF, BMP oder SVG ein Favicon als ICO, "
            "PNG, WebP, GIF, BMP oder SVG oder ein komplettes Favicon-Paket mit Apple-Touch-Icon, Android-Icons "
            "und site.webmanifest."
        ),
        "og_locale": "de_DE",
        "image_alt": "Screenshot des Favicon Konverters von KodiniTools",
        # Serverseitiger Inhalt in #app (für Crawler ohne JavaScript), Texte wie in src/locales/de.ts
        "h1": "Favicon Konverter",
        "intro": (
            "Lade ein Bild hoch (PNG, JPG, WebP, GIF, BMP, SVG – max. 10 MB) oder gib Text/Emoji ein. Du erhältst "
            "ein Favicon als ICO, PNG, WebP, GIF, BMP oder SVG oder ein komplettes Favicon-Paket."
        ),
        "features_heading": "Funktionen",
        "features": [
            "favicon.ico mit mehreren Größen (16 bis 256 px) aus einem Bild oder aus Text/Emoji",
            "Einzelne Datei als ICO, PNG, WebP, GIF, BMP oder SVG",
            "Komplettes Favicon-Paket: favicon.ico, Apple-Touch-Icon, Android-Icons (auch maskable), "
            "site.webmanifest und HTML-Code",
            "Gestaltung mit Hintergrundfarbe, Innenabstand und Eckenradius, Vorschau im Browser-Tab und auf dem "
            "Homescreen",
        ],
        "noscript": "Bitte JavaScript aktivieren, um den Favicon Konverter zu nutzen.",
    },
    Lang.EN: {
        "title": "Favicon Generator – Create favicon.ico & favicon package | KodiniTools",
        "description": (
            "Free favicon generator: turn a PNG, JPG, WebP, GIF, BMP or SVG into a favicon as ICO, PNG, WebP, "
            "GIF, BMP or SVG, or a complete favicon package with Apple touch icon, Android icons and "
            "site.webmanifest."
        ),
        "og_locale": "en_US",
        "image_alt": "Screenshot of the KodiniTools favicon converter",
        # Texte wie in src/locales/en.ts
        "h1": "Favicon Converter",
        "intro": (
            "Upload an image (PNG, JPG, WebP, GIF, BMP, SVG – max. 10 MB) or enter text/emoji. You get a favicon as "
            "ICO, PNG, WebP, GIF, BMP or SVG, or a complete favicon package."
        ),
        "features_heading": "Features",
        "features": [
            "favicon.ico with multiple sizes (16 to 256 px) from an image or from text/emoji",
            "Single file as ICO, PNG, WebP, GIF, BMP or SVG",
            "Complete favicon package: favicon.ico, Apple touch icon, Android icons (including maskable), "
            "site.webmanifest and HTML code",
            "Styling with background colour, padding and corner radius, preview in a browser tab and on the "
            "home screen",
        ],
        "noscript": "Please enable JavaScript to use the favicon converter.",
    },
}


def page_url(lang: Lang) -> str:
    return SITE_URL if lang is Lang.DE else f"{SITE_URL}?lang=en"


def image_url(lang: Lang) -> str:
    """Vorschaubild für Open Graph/Twitter und JSON-LD (Screenshot der Seite, 1920 × 945 px)."""
    return f"{SITE_URL}static/favicon-landingpage-{lang.value}.webp"


def render_content(lang: Lang) -> str:
    """Crawlbarer Inhalt von #app je Sprache; die Vue-App ersetzt ihn beim Start."""
    seo = SEO[lang]
    e = html.escape
    features = "".join(f"<li>{e(item, quote=False)}</li>" for item in seo["features"])
    return (
        '<div class="card">'
        f"<h1>{e(seo['h1'], quote=False)}</h1>"
        f"<p>{e(seo['intro'], quote=False)}</p>"
        f"<h2>{e(seo['features_heading'], quote=False)}</h2>"
        f"<ul>{features}</ul>"
        f"<noscript><p>{e(seo['noscript'], quote=False)}</p></noscript>"
        "</div>"
    )


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
            "screenshot": image_url(lang),
            "offers": {"@type": "Offer", "price": "0", "priceCurrency": "EUR"},
            "publisher": {"@type": "Organization", "name": "KodiniTools", "url": "https://kodinitools.com/"},
        },
        ensure_ascii=False,
    ).replace("</", "<\\/")
    head = "\n    ".join(
        [
            f'<meta name="description" content="{e(seo["description"])}">',
            '<meta name="robots" content="index, follow, max-image-preview:large">',
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
            f'<meta property="og:image" content="{e(image_url(lang))}">',
            '<meta property="og:image:type" content="image/webp">',
            '<meta property="og:image:width" content="1920">',
            '<meta property="og:image:height" content="945">',
            f'<meta property="og:image:alt" content="{e(seo["image_alt"])}">',
            '<meta name="twitter:card" content="summary_large_image">',
            f'<meta name="twitter:title" content="{e(seo["title"])}">',
            f'<meta name="twitter:description" content="{e(seo["description"])}">',
            f'<meta name="twitter:image" content="{e(image_url(lang))}">',
            f'<meta name="twitter:image:alt" content="{e(seo["image_alt"])}">',
            f'<script type="application/ld+json">{json_ld}</script>',
        ]
    )
    title_de = f"<title>{e(SEO[Lang.DE]['title'], quote=False)}</title>"
    for marker in ('<html lang="de">', title_de, "<!--SEO-->", "<!--CONTENT-->"):
        if template.count(marker) != 1:
            raise RuntimeError(f"index.html: Platzhalter fehlt oder doppelt: {marker}")
    return (
        template.replace('<html lang="de">', f'<html lang="{lang.value}">')
        .replace(title_de, f"<title>{e(seo['title'], quote=False)}</title>")
        .replace("<!--SEO-->", head)
        .replace("<!--CONTENT-->", render_content(lang))
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


def render_sitemap() -> str:
    """Sitemap der Seite (DE und EN mit hreflang); im robots.txt der Domain einzutragen."""
    alternates = "".join(
        f'<xhtml:link rel="alternate" hreflang="{code}" href="{html.escape(page_url(lang))}"/>'
        for code, lang in (("de", Lang.DE), ("en", Lang.EN), ("x-default", Lang.DE))
    )
    urls = "".join(f"<url><loc>{html.escape(page_url(lang))}</loc>{alternates}</url>" for lang in Lang)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">'
        f"{urls}</urlset>\n"
    )


SITEMAP_XML = render_sitemap()


@app.get("/sitemap.xml")
def sitemap():
    return Response(SITEMAP_XML, media_type="application/xml")


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
    format: OutputFormat = Form(OutputFormat.ICO),
    svg: str | None = Form(None),
    lang: Lang = Form(Lang.DE),
):
    data = await read_limited(file, lang)
    try:
        size_list = parse_sizes(sizes)
        style = parse_style(background, padding, radius)
        svg_source = validate_svg(svg)
        img = await run_in_threadpool(load_image, data)
        content, media_type, filename = await run_in_threadpool(
            build_icons, img, size_list, fit, style, format, svg_source
        )
    except ImageValidationError as e:
        raise to_http_error(e, lang) from None

    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
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
