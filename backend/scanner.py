# backend/scanner.py
import os
from datetime import datetime
from typing import Optional, Tuple

from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
import face_recognition

from db import get_conn

PHOTOS_ROOT = os.environ.get("PHOTOS_ROOT", "/photos")
SUPPORTED_EXT = (".jpg", ".jpeg", ".png")

def _extract_exif(path: str):
    try:
        img = Image.open(path)
        exif_data = img._getexif() or {}
    except Exception:
        return None, None

    exif = {}
    for tag_id, value in exif_data.items():
        tag = TAGS.get(tag_id, tag_id)
        exif[tag] = value

    dt = None
    gps = None

    if "DateTimeOriginal" in exif:
        raw = exif["DateTimeOriginal"]
        try:
            dt = datetime.strptime(raw, "%Y:%m:%d %H:%M:%S")
        except Exception:
            pass

    if "GPSInfo" in exif:
        gps_info = exif["GPSInfo"]
        gps_data = {}
        for key in gps_info.keys():
            name = GPSTAGS.get(key, key)
            gps_data[name] = gps_info[key]
        gps = _convert_gps(gps_data)

    return dt, gps

def _convert_gps(gps_data) -> Optional[Tuple[float, float]]:
    def _to_deg(value):
        d, m, s = value
        return float(d[0]/d[1] + m[0]/m[1]/60 + s[0]/s[1]/3600)

    try:
        lat = _to_deg(gps_data["GPSLatitude"])
        if gps_data.get("GPSLatitudeRef") == "S":
            lat = -lat
        lon = _to_deg(gps_data["GPSLongitude"])
        if gps_data.get("GPSLongitudeRef") == "W":
            lon = -lon
        return lat, lon
    except Exception:
        return None

def _detect_faces(path: str):
    try:
        img = face_recognition.load_image_file(path)
        locations = face_recognition.face_locations(img, model="hog")
        return len(locations) > 0, len(locations)
    except Exception:
        return False, 0

def _infer_place_label(gps_lat, gps_lon):
    if gps_lat is None or gps_lon is None:
        return None
    if gps_lat > 45:
        return "far north"
    elif gps_lat < -30:
        return "southern hemisphere"
    else:
        return "mid-latitude"

def scan_photos():
    with get_conn() as conn:
        cur = conn.cursor()

        for root, _, files in os.walk(PHOTOS_ROOT):
            for name in files:
                if not name.lower().endswith(SUPPORTED_EXT):
                    continue
                full_path = os.path.join(root, name)

                cur.execute("SELECT id FROM photos WHERE path = ?", (full_path,))
                if cur.fetchone():
                    continue

                taken_at, gps = _extract_exif(full_path)
                gps_lat, gps_lon = gps or (None, None)
                has_faces, face_count = _detect_faces(full_path)
                place_label = _infer_place_label(gps_lat, gps_lon)

                year = month = day = None
                if taken_at:
                    year, month, day = taken_at.year, taken_at.month, taken_at.day

                cur.execute("""
                INSERT INTO photos
                    (path, taken_at, year, month, day, gps_lat, gps_lon, place_label, has_faces, face_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    full_path,
                    taken_at.isoformat() if taken_at else None,
                    year,
                    month,
                    day,
                    gps_lat,
                    gps_lon,
                    place_label,
                    int(has_faces),
                    face_count,
                ))
        conn.commit()
