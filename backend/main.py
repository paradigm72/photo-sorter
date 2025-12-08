# backend/main.py
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from io import BytesIO
from PIL import Image
from pathlib import Path
import os, mimetypes
from fastapi.middleware.cors import CORSMiddleware
from threading import Thread
import threading
import time

from db import init_db, get_conn
from scanner import scan_photos
import logging

app = FastAPI(title="Photo Sorter API")
init_db()

# thumbnail / general HTTP logging
logger = logging.getLogger("photo-sorter.thumbnail")
if not logger.handlers:
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logger.addHandler(h)
logger.setLevel(logging.INFO)

# Scan thread state
_scan_lock = threading.Lock()
_scan_thread: Thread | None = None
_scan_running = False
_scan_running_type: str | None = None  # 'incremental' or 'full'

# Where photos are mounted inside the container
PHOTOS_ROOT = Path(os.environ.get("PHOTOS_ROOT", "/photos")).resolve()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def _start_background_scan(full: bool = False):
    """Start a background scan. If `full` is True, clear the DB first."""
    global _scan_thread, _scan_running, _scan_running_type

    with _scan_lock:
        if _scan_running:
            return False

        def _run_scan():
            global _scan_running, _scan_running_type
            try:
                _scan_running = True
                _scan_running_type = "full" if full else "incremental"
                if full:
                    # clear existing rows then rescan
                    with get_conn() as conn:
                        cur = conn.cursor()
                        cur.execute("DELETE FROM photos")
                        conn.commit()
                scan_photos()
            finally:
                _scan_running = False
                _scan_running_type = None

        _scan_thread = Thread(target=_run_scan, daemon=True)
        _scan_thread.start()
        return True


@app.post("/scan")
def api_scan():
    started = _start_background_scan(full=False)
    return {"status": "started" if started else "already_running"}


@app.post("/scan/full")
def api_scan_full():
    started = _start_background_scan(full=True)
    return {"status": "started" if started else "already_running"}


@app.get("/scan/status")
def scan_status():
    """Return whether a background scan is running and basic stats, plus the scan type."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM photos")
        total = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM photos WHERE has_faces = 1")
        with_faces = cur.fetchone()[0]
    return {"running": bool(_scan_running), "type": _scan_running_type, "total": total, "with_faces": with_faces}

@app.get("/stats")
def stats():
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM photos")
        total = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM photos WHERE has_faces = 1")
        with_faces = cur.fetchone()[0]
    return {"total": total, "with_faces": with_faces}

@app.get("/people")
def people():
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, path, face_count
            FROM photos
            WHERE has_faces = 1
            ORDER BY face_count DESC
        """)
        rows = cur.fetchall()
    return [
        {"id": r[0], "path": r[1], "face_count": r[2]}
        for r in rows
    ]

@app.get("/places")
def places():
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT place_label, COUNT(*) as cnt
            FROM photos
            WHERE place_label IS NOT NULL
            GROUP BY place_label
            ORDER BY cnt DESC
        """)
        rows = cur.fetchall()
    return [{"place": r[0], "count": r[1]} for r in rows]


@app.get("/photos")
def list_photos(limit: int | None = None, year: int | None = None, month: int | None = None):
    """Return a list of photos with basic metadata.

    Optional `year` and `month` can filter results. If `limit` is omitted, all
    matching rows are returned (use with care for very large collections).
    """
    q = "SELECT id, path, year, month, has_faces, face_count FROM photos"
    params = []
    conds = []
    if year is not None:
        conds.append("year = ?")
        params.append(year)
    if month is not None:
        conds.append("month = ?")
        params.append(month)
    if conds:
        q += " WHERE " + " AND ".join(conds)
    q += " ORDER BY id DESC"
    if limit is not None:
        q += " LIMIT ?"
        params.append(limit)
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(q, tuple(params))
        rows = cur.fetchall()
    return [
        {"id": r[0], "path": r[1], "year": r[2], "month": r[3], "has_faces": r[4], "face_count": r[5]}
        for r in rows
    ]

@app.get("/times")
def times():
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT year, month, COUNT(*) as cnt
            FROM photos
            WHERE year IS NOT NULL
            GROUP BY year, month
            ORDER BY year DESC, month DESC
        """)
        rows = cur.fetchall()
    return [{"year": r[0], "month": r[1], "count": r[2]} for r in rows]


@app.get("/photo/{photo_id}/image")
def photo_image(photo_id: int):
    """Serve the original image file for a photo id.

    This looks up the path stored in the DB, ensures it is under the
    mounted `PHOTOS_ROOT`, and returns a FileResponse. This is the
    quick-serve option (no thumbnails).
    """
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT path FROM photos WHERE id = ?", (photo_id,))
        row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Photo not found")

    photo_path = Path(row[0])
    try:
        photo_path = photo_path.resolve()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid path")

    try:
        # ensure the resolved path is within the photos root
        if not photo_path.is_relative_to(PHOTOS_ROOT):
            raise HTTPException(status_code=403, detail="Access denied")
    except AttributeError:
        # Python <3.9 fallback (shouldn't be needed on 3.11)
        if str(PHOTOS_ROOT) not in str(photo_path):
            raise HTTPException(status_code=403, detail="Access denied")

    if not photo_path.exists():
        raise HTTPException(status_code=404, detail="File not found on disk")

    mime = mimetypes.guess_type(str(photo_path))[0] or "application/octet-stream"
    return FileResponse(str(photo_path), media_type=mime, headers={"Cache-Control": "public, max-age=3600"})


@app.get("/photo/{photo_id}/thumbnail")
def photo_thumbnail(photo_id: int, max_w: int = 480, max_h: int = 360):
    """Return a browser-friendly JPEG thumbnail for the photo.

    This attempts to open the original file with Pillow and convert to an
    RGB JPEG thumbnail. If Pillow cannot open the file (e.g. HEIC without
    `pillow-heif` installed), the endpoint will return a 415 with a helpful
    message. You can install `pillow-heif` in the backend image to add HEIC
    support.
    """
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT path FROM photos WHERE id = ?", (photo_id,))
        row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Photo not found")

    photo_path = Path(row[0])
    try:
        photo_path = photo_path.resolve()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid path")

    try:
        if not photo_path.is_file():
            raise HTTPException(status_code=404, detail="File not found on disk")
    except AttributeError:
        if not photo_path.exists():
            raise HTTPException(status_code=404, detail="File not found on disk")

    try:
        logger.info("Attempting thumbnail generation for %s (max %dx%d)", photo_path, max_w, max_h)
        with Image.open(photo_path) as im:
            orig_size = im.size
            im_rgb = im.convert("RGB")
            im_rgb.thumbnail((max_w, max_h))
            thumb_size = im_rgb.size
            buf = BytesIO()
            im_rgb.save(buf, format="JPEG", quality=85)
            data_len = buf.tell()
            buf.seek(0)
            logger.info("Thumbnail generated for %s: orig=%s thumb=%s bytes=%d", photo_path, orig_size, thumb_size, data_len)
            return StreamingResponse(buf, media_type="image/jpeg", headers={"Cache-Control": "public, max-age=3600"})
    except Exception as e:
        # Pillow couldn't open/convert the image (common for HEIC when
        # pillow-heif isn't installed). Return a 415 with guidance.
        logger.exception("Failed to create thumbnail for %s: %s", photo_path, e)
        raise HTTPException(
            status_code=415,
            detail=(
                "Unable to generate thumbnail for this image in the current environment. "
                "Install `pillow-heif` (and its native dependencies) in the backend image to add HEIC support, "
                "or fallback to converting images to JPEGs before mounting."
            ),
        )
