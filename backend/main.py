# backend/main.py
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path
import os, mimetypes
from fastapi.middleware.cors import CORSMiddleware

from db import init_db, get_conn
from scanner import scan_photos

app = FastAPI(title="Photo Sorter API")
init_db()

# Where photos are mounted inside the container
PHOTOS_ROOT = Path(os.environ.get("PHOTOS_ROOT", "/photos")).resolve()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/scan")
def api_scan():
    scan_photos()
    return {"status": "ok"}

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
            LIMIT 200
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
def list_photos(limit: int = 500, year: int | None = None, month: int | None = None):
    """Return a list of photos with basic metadata.

    Optional `year` and `month` can filter results. Limit defaults to 500.
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
    q += " ORDER BY id DESC LIMIT ?"
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
