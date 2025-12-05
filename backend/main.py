# backend/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from db import init_db, get_conn
from scanner import scan_photos

app = FastAPI(title="Photo Sorter API")
init_db()

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
