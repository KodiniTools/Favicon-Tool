"""Bildverarbeitung für den Favicon-Generator (ohne Web-Abhängigkeiten, gut testbar)."""

import io
import json
import zipfile
from enum import Enum

from PIL import Image, ImageOps, UnidentifiedImageError

MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB
MAX_PIXELS = 40_000_000  # z. B. 8000 x 5000
ALLOWED_FORMATS = frozenset({"PNG", "JPEG", "WEBP", "GIF", "BMP"})

ICO_ALLOWED_SIZES = (16, 24, 32, 48, 64, 128, 256)
ICO_DEFAULT_SIZES = (16, 32, 48, 64)
PACKAGE_ICO_SIZES = (16, 32, 48)
APP_NAME_MAX_LEN = 60


class FitMode(str, Enum):
    PAD = "pad"  # transparent auf Quadrat auffüllen
    CROP = "crop"  # mittig quadratisch zuschneiden


class ImageValidationError(ValueError):
    """Ungültige Eingabe; Nachricht ist für Endnutzer gedacht (deutsch, ``en`` = englische Fassung)."""

    def __init__(self, message: str, en: str | None = None):
        super().__init__(message)
        self.en = en or message

    def localized(self, lang: str) -> str:
        return self.en if lang == "en" else str(self)


class UnsupportedFormatError(ImageValidationError):
    pass


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


def build_ico(img: Image.Image, sizes: tuple[int, ...], fit: FitMode) -> bytes:
    master = make_square(img, fit, max(sizes))
    buf = io.BytesIO()
    master.save(buf, format="ICO", sizes=[(s, s) for s in sizes])
    return buf.getvalue()


def _png(master: Image.Image, size: int, background: tuple[int, int, int] | None = None) -> bytes:
    frame = master.resize((size, size), Image.Resampling.LANCZOS)
    if background is not None:
        canvas = Image.new("RGBA", frame.size, (*background, 255))
        canvas.alpha_composite(frame)
        frame = canvas.convert("RGB")
    buf = io.BytesIO()
    frame.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


SNIPPET_HTML = """<link rel="icon" href="/favicon.ico" sizes="any">
<link rel="icon" type="image/png" sizes="32x32" href="/favicon-32x32.png">
<link rel="icon" type="image/png" sizes="16x16" href="/favicon-16x16.png">
<link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png">
<link rel="manifest" href="/site.webmanifest">
"""


def build_manifest(app_name: str) -> str:
    manifest = {
        "name": app_name,
        "short_name": app_name,
        "icons": [
            {"src": "/android-chrome-192x192.png", "sizes": "192x192", "type": "image/png"},
            {"src": "/android-chrome-512x512.png", "sizes": "512x512", "type": "image/png"},
        ],
        "theme_color": "#ffffff",
        "background_color": "#ffffff",
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


def build_package(img: Image.Image, fit: FitMode, app_name: str = "") -> bytes:
    """Erzeugt ein ZIP mit ICO, PNGs (Browser, Apple, Android), Manifest und HTML-Snippet."""
    master = make_square(img, fit, 512)
    files: dict[str, bytes] = {
        "favicon.ico": build_ico(master, PACKAGE_ICO_SIZES, fit),
        "favicon-16x16.png": _png(master, 16),
        "favicon-32x32.png": _png(master, 32),
        # iOS stellt Transparenz schwarz dar -> auf Weiß reduzieren
        "apple-touch-icon.png": _png(master, 180, background=(255, 255, 255)),
        "android-chrome-192x192.png": _png(master, 192),
        "android-chrome-512x512.png": _png(master, 512),
        "site.webmanifest": build_manifest(app_name).encode("utf-8"),
        "favicon-snippet.html": SNIPPET_HTML.encode("utf-8"),
    }
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    return buf.getvalue()
