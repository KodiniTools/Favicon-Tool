"""Bildverarbeitung für den Favicon-Generator (ohne Web-Abhängigkeiten, gut testbar)."""

import io
import json
import re
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass
from enum import Enum

from PIL import Image, ImageChops, ImageDraw, ImageOps, UnidentifiedImageError

MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB
MAX_PIXELS = 40_000_000  # z. B. 8000 x 5000
ALLOWED_FORMATS = frozenset({"PNG", "JPEG", "WEBP", "GIF", "BMP"})

ICO_ALLOWED_SIZES = (16, 24, 32, 48, 64, 128, 256)
ICO_DEFAULT_SIZES = (16, 32, 48, 64)
PACKAGE_ICO_SIZES = (16, 32, 48)
APP_NAME_MAX_LEN = 60
PADDING_MAX = 40  # Prozent je Seite
RADIUS_MAX = 50  # Prozent der halben Kantenlänge; 50 = Kreis
DEFAULT_MANIFEST_COLOR = "#ffffff"
# Maskierbare Icons: sichtbar ist garantiert nur ein Kreis mit 40 % Radius (W3C "safe zone").
# Ein Quadrat passt hinein, wenn seine Kante 0,8 / sqrt(2) der Icon-Kante beträgt.
MASKABLE_CONTENT_RATIO = 0.8 / 2**0.5
_HEX_COLOR = re.compile(r"#[0-9a-fA-F]{6}")
SVG_MAX_BYTES = 512 * 1024
SVG_NS = "http://www.w3.org/2000/svg"
# Elemente, die Skripte, fremde Dokumente oder externe Inhalte einbinden können
_SVG_FORBIDDEN_TAGS = frozenset({"script", "foreignobject", "iframe", "embed", "object", "audio", "video", "image"})


class FitMode(str, Enum):
    PAD = "pad"  # transparent auf Quadrat auffüllen
    CROP = "crop"  # mittig quadratisch zuschneiden


class OutputFormat(str, Enum):
    ICO = "ico"
    PNG = "png"
    WEBP = "webp"


# Pillow-Formatname und Media-Type je Ausgabeformat (ohne ICO, das build_ico erzeugt)
_RASTER_OUTPUT = {OutputFormat.PNG: ("PNG", "image/png"), OutputFormat.WEBP: ("WEBP", "image/webp")}


class ImageValidationError(ValueError):
    """Ungültige Eingabe; Nachricht ist für Endnutzer gedacht (deutsch, ``en`` = englische Fassung)."""

    def __init__(self, message: str, en: str | None = None):
        super().__init__(message)
        self.en = en or message

    def localized(self, lang: str) -> str:
        return self.en if lang == "en" else str(self)


class UnsupportedFormatError(ImageValidationError):
    pass


@dataclass(frozen=True)
class IconStyle:
    """Gestaltung des Icons. Standardwerte lassen das Bild unverändert."""

    background: str | None = None  # "#rrggbb" oder None = transparent
    padding: int = 0  # Innenabstand je Seite in Prozent (0–PADDING_MAX)
    radius: int = 0  # Eckenradius in Prozent (0–RADIUS_MAX)


def parse_color(raw: str | None, field: str = "Farbe", field_en: str = "Color") -> str | None:
    """Validiert eine Farbe im Format #rrggbb. Leer -> None."""
    if raw is None or not raw.strip():
        return None
    value = raw.strip()
    if not _HEX_COLOR.fullmatch(value):
        raise ImageValidationError(
            f"{field} ungültig: '{value}' (erwartet #rrggbb)", f"{field_en} invalid: '{value}' (expected #rrggbb)"
        )
    return value.lower()


def parse_percent(raw: str | None, maximum: int, field: str, field_en: str) -> int:
    """Validiert eine ganze Prozentzahl 0..maximum. Leer -> 0."""
    if raw is None or not raw.strip():
        return 0
    try:
        value = int(raw.strip())
    except ValueError:
        value = -1
    if not 0 <= value <= maximum:
        raise ImageValidationError(
            f"{field} muss zwischen 0 und {maximum} liegen", f"{field_en} must be between 0 and {maximum}"
        )
    return value


def parse_style(background: str | None, padding: str | None, radius: str | None) -> IconStyle:
    return IconStyle(
        background=parse_color(background, "Hintergrundfarbe", "Background color"),
        padding=parse_percent(padding, PADDING_MAX, "Innenabstand", "Padding"),
        radius=parse_percent(radius, RADIUS_MAX, "Eckenradius", "Corner radius"),
    )


def _rgb(color: str) -> tuple[int, int, int]:
    return int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)


def apply_style(square: Image.Image, style: IconStyle) -> Image.Image:
    """Wendet Innenabstand, Hintergrund und Eckenradius auf ein quadratisches RGBA-Bild an (Größe bleibt)."""
    if style == IconStyle():
        return square
    side = square.width
    inner = max(1, round(side * (100 - 2 * style.padding) / 100))
    content = square if inner == side else square.resize((inner, inner), Image.Resampling.LANCZOS)
    fill = (*_rgb(style.background), 255) if style.background else (0, 0, 0, 0)
    canvas = Image.new("RGBA", (side, side), fill)
    offset = (side - inner) // 2
    canvas.alpha_composite(content, (offset, offset))
    if style.radius:
        # 4-fach überabgetastete Maske für glatte Kanten
        scale = 4
        mask = Image.new("L", (side * scale, side * scale), 0)
        radius = round(side * scale / 2 * style.radius / 100)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, side * scale - 1, side * scale - 1), radius=radius, fill=255)
        mask = mask.resize((side, side), Image.Resampling.LANCZOS)
        canvas.putalpha(ImageChops.multiply(canvas.getchannel("A"), mask))
    return canvas


def parse_sizes(raw: str | None) -> tuple[int, ...]:
    """Parst eine kommagetrennte Größenliste (z. B. "16,32,48"). Leer -> Standardgrößen."""
    if raw is None or not raw.strip():
        return ICO_DEFAULT_SIZES
    sizes: set[int] = set()
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            value = int(part)
        except ValueError:
            raise ImageValidationError(f"Ungültige Größe: '{part}'", f"Invalid size: '{part}'") from None
        if value not in ICO_ALLOWED_SIZES:
            allowed = ", ".join(map(str, ICO_ALLOWED_SIZES))
            raise ImageValidationError(
                f"Größe {value} nicht erlaubt (erlaubt: {allowed})", f"Size {value} not allowed (allowed: {allowed})"
            )
        sizes.add(value)
    if not sizes:
        raise ImageValidationError("Mindestens eine Größe auswählen", "Select at least one size")
    return tuple(sorted(sizes))


def load_image(data: bytes) -> Image.Image:
    """Validiert die Bytes und liefert das (erste) Bild als RGBA mit korrigierter EXIF-Ausrichtung."""
    if not data:
        raise ImageValidationError("Leere Datei", "Empty file")
    if len(data) > MAX_UPLOAD_BYTES:
        raise ImageValidationError("Datei zu groß", "File too large")
    try:
        img = Image.open(io.BytesIO(data))  # liest nur den Header
        if img.format not in ALLOWED_FORMATS:
            raise UnsupportedFormatError(
                f"Format nicht unterstützt: {img.format or 'unbekannt'} (erlaubt: PNG, JPG, WebP, GIF, BMP)",
                f"Unsupported format: {img.format or 'unknown'} (allowed: PNG, JPG, WebP, GIF, BMP)",
            )
        width, height = img.size
        if width < 1 or height < 1 or width * height > MAX_PIXELS:
            raise ImageValidationError("Bildabmessungen zu groß", "Image dimensions too large")
        img.load()
    except ImageValidationError:
        raise
    except (UnidentifiedImageError, Image.DecompressionBombError):
        raise UnsupportedFormatError("Datei ist kein gültiges Bild", "File is not a valid image") from None
    except (OSError, SyntaxError, ValueError):
        raise ImageValidationError(
            "Bild ist beschädigt oder konnte nicht gelesen werden", "Image is corrupted or could not be read"
        ) from None

    img = ImageOps.exif_transpose(img)
    return img.convert("RGBA")


def make_square(img: Image.Image, fit: FitMode, min_side: int) -> Image.Image:
    """Bringt das Bild auf ein Quadrat (pad/crop) mit Kantenlänge >= min_side."""
    width, height = img.size
    if fit is FitMode.CROP:
        side = min(width, height)
        left = (width - side) // 2
        top = (height - side) // 2
        square = img.crop((left, top, left + side, top + side))
    elif fit is FitMode.PAD:
        side = max(width, height)
        square = Image.new("RGBA", (side, side), (0, 0, 0, 0))
        square.paste(img, ((side - width) // 2, (side - height) // 2))
    else:  # pragma: no cover - Enum ist abgeschlossen
        raise ValueError(f"Unbekannter Modus: {fit}")

    # Pillow schreibt nur ICO-Größen <= Quellgröße, daher kleine Bilder hochskalieren.
    if square.width < min_side:
        square = square.resize((min_side, min_side), Image.Resampling.LANCZOS)
    return square


def build_ico(img: Image.Image, sizes: tuple[int, ...], fit: FitMode, style: IconStyle | None = None) -> bytes:
    master = apply_style(make_square(img, fit, max(sizes)), style or IconStyle())
    buf = io.BytesIO()
    master.save(buf, format="ICO", sizes=[(s, s) for s in sizes])
    return buf.getvalue()


def build_icons(
    img: Image.Image,
    sizes: tuple[int, ...],
    fit: FitMode,
    style: IconStyle | None = None,
    fmt: OutputFormat = OutputFormat.ICO,
) -> tuple[bytes, str, str]:
    """Icons im gewünschten Format: (Inhalt, Media-Type, Dateiname).

    ICO enthält alle Größen in einer Datei. PNG/WebP liefern bei einer Größe die Datei direkt,
    bei mehreren ein ZIP mit favicon-<n>x<n>.<ext> je Größe.
    """
    if fmt is OutputFormat.ICO:
        return build_ico(img, sizes, fit, style), "image/x-icon", "favicon.ico"
    pil_format, media_type = _RASTER_OUTPUT[fmt]
    master = apply_style(make_square(img, fit, max(sizes)), style or IconStyle())
    files = {}
    for size in sizes:
        buf = io.BytesIO()
        frame = master.resize((size, size), Image.Resampling.LANCZOS)
        if pil_format == "WEBP":
            frame.save(buf, format="WEBP", lossless=True)
        else:
            frame.save(buf, format="PNG", optimize=True)
        files[f"favicon-{size}x{size}.{fmt.value}"] = buf.getvalue()
    if len(files) == 1:
        (name, content), *_ = files.items()
        return content, media_type, name
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    return buf.getvalue(), "application/zip", f"favicon-{fmt.value}.zip"


def _png(master: Image.Image, size: int, background: tuple[int, int, int] | None = None) -> bytes:
    frame = master.resize((size, size), Image.Resampling.LANCZOS)
    if background is not None:
        canvas = Image.new("RGBA", frame.size, (*background, 255))
        canvas.alpha_composite(frame)
        frame = canvas.convert("RGB")
    buf = io.BytesIO()
    frame.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def validate_svg(raw: str | None) -> str | None:
    """Prüft ein SVG für favicon.svg streng (kein Skript, keine externen Verweise). Leer -> None.

    Das Rastern übernimmt der Browser; der Server übernimmt die Datei nur unverändert ins Paket.
    """
    if raw is None or not raw.strip():
        return None
    if len(raw.encode("utf-8")) > SVG_MAX_BYTES:
        raise ImageValidationError("SVG zu groß (max. 512 KB)", "SVG too large (max. 512 KB)")
    invalid = ImageValidationError(
        "SVG enthält nicht erlaubte Inhalte (Skripte, externe Verweise oder DTD)",
        "SVG contains disallowed content (scripts, external references or DTD)",
    )
    # DTDs/Entitäten gar nicht erst parsen (XXE, Entity-Expansion)
    if re.search(r"<!(DOCTYPE|ENTITY)", raw, re.IGNORECASE):
        raise invalid
    try:
        root = ET.fromstring(raw)
    except ET.ParseError:
        raise ImageValidationError("SVG ist kein gültiges XML", "SVG is not valid XML") from None
    if root.tag not in (f"{{{SVG_NS}}}svg", "svg"):
        raise ImageValidationError("Datei ist kein SVG", "File is not an SVG")
    for el in root.iter():
        tag = el.tag.rsplit("}", 1)[-1].lower() if isinstance(el.tag, str) else ""
        if tag in _SVG_FORBIDDEN_TAGS:
            raise invalid
        if tag == "style" and re.search(r"@import|url\(\s*['\"]?(?!#)", el.text or "", re.IGNORECASE):
            raise invalid
        for name, value in el.attrib.items():
            local = name.rsplit("}", 1)[-1].lower()
            if local.startswith("on"):
                raise invalid
            if local == "href" and not value.strip().startswith("#"):
                raise invalid
            if re.search(r"url\(\s*['\"]?(?!#)|javascript:", value, re.IGNORECASE):
                raise invalid
    return raw


def _maskable(square: Image.Image, size: int, background: str) -> bytes:
    """Icon mit voller, deckender Fläche; Motiv innerhalb der Safe Zone (für purpose "maskable")."""
    inner = round(size * MASKABLE_CONTENT_RATIO)
    content = square.resize((inner, inner), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (size, size), (*_rgb(background), 255))
    offset = (size - inner) // 2
    canvas.alpha_composite(content, (offset, offset))
    buf = io.BytesIO()
    canvas.convert("RGB").save(buf, format="PNG", optimize=True)
    return buf.getvalue()


SNIPPET_HTML = """<link rel="icon" href="/favicon.ico" sizes="any">
<link rel="icon" type="image/png" sizes="32x32" href="/favicon-32x32.png">
<link rel="icon" type="image/png" sizes="16x16" href="/favicon-16x16.png">
<link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png">
<link rel="manifest" href="/site.webmanifest">
"""


SNIPPET_SVG = '<link rel="icon" type="image/svg+xml" href="/favicon.svg">\n'


def build_snippet(theme_color: str | None = None, svg: bool = False) -> str:
    """HTML für den <head>; optional mit SVG-Icon und theme-color."""
    snippet = SNIPPET_HTML
    if svg:
        # Chrome bevorzugt ein ICO mit sizes="any" vor dem SVG -> ICO auf 32x32 festlegen
        first, rest = snippet.split("\n", 1)
        first = first.replace('sizes="any"', 'sizes="32x32"')
        snippet = f"{first}\n{SNIPPET_SVG}{rest}"
    if theme_color:
        snippet += f'<meta name="theme-color" content="{theme_color}">\n'
    return snippet


def build_manifest(app_name: str, theme_color: str | None = None, background_color: str | None = None) -> str:
    manifest = {
        "name": app_name,
        "short_name": app_name,
        "icons": [
            {"src": "/android-chrome-192x192.png", "sizes": "192x192", "type": "image/png"},
            {"src": "/android-chrome-512x512.png", "sizes": "512x512", "type": "image/png"},
            {
                "src": "/android-chrome-maskable-192x192.png",
                "sizes": "192x192",
                "type": "image/png",
                "purpose": "maskable",
            },
            {
                "src": "/android-chrome-maskable-512x512.png",
                "sizes": "512x512",
                "type": "image/png",
                "purpose": "maskable",
            },
        ],
        "theme_color": theme_color or DEFAULT_MANIFEST_COLOR,
        "background_color": background_color or DEFAULT_MANIFEST_COLOR,
        "display": "standalone",
    }
    return json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"


def normalize_app_name(raw: str | None) -> str:
    name = (raw or "").strip()
    if len(name) > APP_NAME_MAX_LEN:
        raise ImageValidationError(
            f"App-Name zu lang (max. {APP_NAME_MAX_LEN} Zeichen)",
            f"App name too long (max. {APP_NAME_MAX_LEN} characters)",
        )
    return name


def build_package(
    img: Image.Image,
    fit: FitMode,
    app_name: str = "",
    style: IconStyle | None = None,
    theme_color: str | None = None,
    svg: str | None = None,
) -> bytes:
    """Erzeugt ein ZIP mit ICO, PNGs (Browser, Apple, Android inkl. maskable), Manifest und HTML-Snippet."""
    style = style or IconStyle()
    square = make_square(img, fit, 512)
    master = apply_style(square, style)
    # Deckende Fläche für Apple- und maskable Icons: gewählter Hintergrund, sonst Weiß
    solid = style.background or DEFAULT_MANIFEST_COLOR
    files: dict[str, bytes] = {
        "favicon.ico": build_ico(master, PACKAGE_ICO_SIZES, fit),
        "favicon-16x16.png": _png(master, 16),
        "favicon-32x32.png": _png(master, 32),
        # iOS stellt Transparenz schwarz dar und rundet selbst ab -> ohne Eckenradius, deckend
        "apple-touch-icon.png": _png(
            apply_style(square, IconStyle(padding=style.padding)), 180, background=_rgb(solid)
        ),
        "android-chrome-192x192.png": _png(master, 192),
        "android-chrome-512x512.png": _png(master, 512),
        "android-chrome-maskable-192x192.png": _maskable(square, 192, solid),
        "android-chrome-maskable-512x512.png": _maskable(square, 512, solid),
        "site.webmanifest": build_manifest(app_name, theme_color, style.background).encode("utf-8"),
        "favicon-snippet.html": build_snippet(theme_color, svg=svg is not None).encode("utf-8"),
    }
    if svg is not None:
        files["favicon.svg"] = svg.encode("utf-8")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    return buf.getvalue()
