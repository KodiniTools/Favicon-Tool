from enum import Enum
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles

from favicon_core import (
    MAX_UPLOAD_BYTES,
    FitMode,
    ImageValidationError,
    UnsupportedFormatError,
    build_ico,
    build_package,
    load_image,
    normalize_app_name,
    parse_sizes,
)

app = FastAPI(title="Favicon Generator")

STATIC_DIR = Path(__file__).parent / "static"
HTML_CONTENT = (STATIC_DIR / "index.html").read_text(encoding="utf-8")

# Design-Tokens und Schriften (relativ aus index.html referenziert, damit der Subpath passt)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class Lang(str, Enum):
    """Sprache der Fehlermeldungen (Umschalter DE/EN der Navigation)."""

    DE = "de"
    EN = "en"


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
def index():
    return HTML_CONTENT


@app.post("/convert")
async def convert(
    file: UploadFile = File(...),
    sizes: str | None = Form(None),
    fit: FitMode = Form(FitMode.PAD),
    lang: Lang = Form(Lang.DE),
):
    data = await read_limited(file, lang)
    try:
        size_list = parse_sizes(sizes)
        img = await run_in_threadpool(load_image, data)
        ico = await run_in_threadpool(build_ico, img, size_list, fit)
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
    lang: Lang = Form(Lang.DE),
):
    data = await read_limited(file, lang)
    try:
        name = normalize_app_name(app_name)
        img = await run_in_threadpool(load_image, data)
        archive = await run_in_threadpool(build_package, img, fit, name)
    except ImageValidationError as e:
        raise to_http_error(e, lang) from None

    return Response(
        content=archive,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=favicon-package.zip"},
    )
