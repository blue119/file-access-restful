from __future__ import annotations

import logging
import os
import secrets
from pathlib import Path
from threading import Lock
from urllib.parse import quote

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, HTMLResponse, Response

from src.services.file_catalog import (
    DirectoryAccessError,
    build_listing,
    resolve_download,
    resolve_upload_target,
)

ROOT_DIR = Path(__file__).resolve().parents[2]
DOWNLOAD_ROOT = ROOT_DIR / "storage" / "files"
DOWNLOAD_ROOT.mkdir(parents=True, exist_ok=True)

STATIC_DIR = ROOT_DIR / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)
FAVICON_PATH = STATIC_DIR / "favicon.ico"

UPLOAD_TOKEN_ENV = "FILE_ACCESS_UPLOAD_TOKEN"
SUPER_TOKEN_ENV = "FILE_ACCESS_SUPER_TOKEN"
TOKEN_LENGTH = 16
SUPER_TOKEN_LENGTH = 32
TOKEN_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"


def _generate_token(length: int, *, exclude: str | None = None) -> str:
    while True:
        candidate = "".join(secrets.choice(TOKEN_ALPHABET) for _ in range(length))
        if exclude is None or candidate != exclude:
            return candidate


def _normalize_token(raw: str | None, length: int) -> str:
    if not raw:
        return _generate_token(length)
    trimmed = raw.strip()
    if not trimmed:
        return _generate_token(length)
    if len(trimmed) >= length:
        return trimmed[:length]
    padding = _generate_token(length - len(trimmed))
    return (trimmed + padding)[:length]


UPLOAD_TOKEN = _normalize_token(os.environ.get(UPLOAD_TOKEN_ENV), TOKEN_LENGTH)
SUPER_TOKEN = _normalize_token(os.environ.get(SUPER_TOKEN_ENV), SUPER_TOKEN_LENGTH)

_upload_token_lock = Lock()


def _get_upload_token() -> str:
    with _upload_token_lock:
        return UPLOAD_TOKEN


def _set_upload_token(value: str) -> str:
    global UPLOAD_TOKEN
    with _upload_token_lock:
        UPLOAD_TOKEN = value
        return UPLOAD_TOKEN


logger = logging.getLogger("file_access.upload")
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(levelname)s %(name)s - %(message)s"))
    logger.addHandler(handler)

logger.info("Upload token initialised. Include it in path: /upload/%s/<file>", _get_upload_token())
logger.info("Super token initialised. Admin override path: /upload/%s/<file>", SUPER_TOKEN)

app = FastAPI(
    title="File Access Service",
    description="Lightweight directory browser and downloader built with FastAPI.",
    version="0.1.0",
)


@app.middleware("http")
async def add_csp_header(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault(
        "Content-Security-Policy",
        "default-src 'self'; style-src 'self' 'unsafe-inline';",
    )
    return response


def _build_breadcrumbs(current_path: str) -> list[tuple[str, str]]:
    crumbs = [("Home", "/")]  # (label, href)
    if not current_path:
        return crumbs

    parts = current_path.split("/")
    running = []
    for part in parts:
        if not part:
            continue
        running.append(part)
        href = "/?path=" + quote("/".join(running))
        crumbs.append((part, href))
    return crumbs


@app.get("/", response_class=HTMLResponse)
async def browse(path: str = Query(default="", description="Relative path to browse")):
    try:
        entries = build_listing(DOWNLOAD_ROOT, path)
    except (FileNotFoundError, DirectoryAccessError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    breadcrumbs = _build_breadcrumbs(path)
    parent_path: str | None = None
    if path:
        parent_parts = path.split("/")[:-1]
        parent_path = "/?path=" + quote("/".join(parent_parts)) if parent_parts else "/"

    rows = []
    for entry in entries:
        if entry.is_dir:
            href = "/?path=" + quote(entry.relative_path)
            display_name = f"{entry.name}/"
            size_display = "--"
        else:
            href = f"/download/{quote(entry.relative_path)}"
            display_name = entry.name
            size_display = f"{entry.size:,} bytes" if entry.size is not None else "--"
        rows.append(f"<tr><td><a href='{href}'>{display_name}</a></td><td>{size_display}</td></tr>")

    rows_html = "".join(rows) or "<tr><td colspan='2'>Directory is empty.</td></tr>"

    breadcrumbs_html = " / ".join(f"<a href='{href}'>{label}</a>" for label, href in breadcrumbs)

    parent_link_html = f"<a href='{parent_path}'>&larr; Up one level</a>" if parent_path else ""

    upload_hint = ""
    current_token = _get_upload_token()
    if not path:
        upload_hint = (
            "<p>Upload with: curl -T myfile.txt "
            f"http://localhost:PORT/upload/{current_token}/myfile.txt</p>"
        )

    return HTMLResponse(
        content=f"""
        <!DOCTYPE html>
        <html lang='en'>
        <head>
            <meta charset='utf-8'>
            <title>File Access Service</title>
            <link rel='icon' href='/favicon.ico' type='image/x-icon'>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 2rem; }}
                h1 {{ margin-bottom: 0.5rem; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 1rem; }}
                th, td {{ text-align: left; padding: 0.5rem; border-bottom: 1px solid #ddd; }}
                a {{ color: #0a5ec2; text-decoration: none; }}
                a:hover {{ text-decoration: underline; }}
                .crumbs {{ font-size: 0.9rem; color: #555; }}
                .top-bar {{ display: flex; justify-content: space-between; align-items: center; }}
                .upload-hint {{ font-size: 0.9rem; color: #333; margin-top: 1rem; }}
            </style>
        </head>
        <body>
            <div class='top-bar'>
                <h1>File Access Service</h1>
                <div>{parent_link_html}</div>
            </div>
            <div class='crumbs'>{breadcrumbs_html}</div>
            <div class='upload-hint'>{upload_hint}</div>
            <table>
                <thead>
                    <tr><th>Name</th><th>Size</th></tr>
                </thead>
                <tbody>
                    {rows_html}
                </tbody>
            </table>
        </body>
        </html>
        """
    )


def _rotate_upload_token() -> str:
    current = _get_upload_token()
    new_token = _generate_token(TOKEN_LENGTH, exclude=current)
    _set_upload_token(new_token)
    logger.info("Upload token rotated after use. Include it in path: /upload/%s/<file>", new_token)
    return new_token


@app.put("/upload/{token}/{file_path:path}", status_code=201)
async def upload(file_path: str, token: str, request: Request):
    current_token = _get_upload_token()
    if token not in {current_token, SUPER_TOKEN}:
        raise HTTPException(status_code=401, detail="Invalid upload token")

    try:
        target_path = resolve_upload_target(DOWNLOAD_ROOT, file_path)
    except (FileNotFoundError, DirectoryAccessError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    content = await request.body()
    target_path.write_bytes(content)

    if token == current_token:
        _rotate_upload_token()

    return Response(status_code=201, headers={"Location": f"/download/{file_path}"})


@app.get("/download/{file_path:path}")
async def download(file_path: str):
    try:
        absolute = resolve_download(DOWNLOAD_ROOT, file_path)
    except (FileNotFoundError, DirectoryAccessError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return FileResponse(path=absolute, filename=absolute.name)


@app.get("/favicon.ico")
async def favicon():
    if not FAVICON_PATH.exists():
        raise HTTPException(status_code=404, detail="Favicon not found")
    return FileResponse(path=FAVICON_PATH, media_type="image/x-icon")
