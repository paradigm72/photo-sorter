# backend/db.py
import sqlite3
from contextlib import contextmanager
import os

DB_PATH = os.environ.get("DB_PATH", "/data/photos.db")

@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    with get_conn() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS photos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT UNIQUE,
            taken_at TEXT,
            year INTEGER,
            month INTEGER,
            day INTEGER,
            gps_lat REAL,
            gps_lon REAL,
            place_label TEXT,
            has_faces INTEGER,
            face_count INTEGER
        )
        """)
        conn.commit()
