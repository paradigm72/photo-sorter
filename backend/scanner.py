# backend/scanner.py
import os
import logging
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
from PIL import Image

# Optional HEIC support; non-fatal if not installed
try:
    import pillow_heif  # type: ignore
    pillow_heif.register_heif_opener()
    _HEIF_AVAILABLE = True
except Exception:
    _HEIF_AVAILABLE = False

import face_recognition

from db import get_conn
from PIL.ExifTags import TAGS
from datetime import datetime

# --- Added / restored logging and face-detection helpers ---
logger = logging.getLogger("photo-sorter.scanner")
if not logger.handlers:
    handler = logging.StreamHandler()
    fmt = "%(asctime)s %(levelname)s %(name)s: %(message)s"
    handler.setFormatter(logging.Formatter(fmt))
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

SUPPORTED_EXT = {".jpg", ".jpeg", ".png", ".heic"}

def _load_image_for_face_detection(path: Path) -> Optional[np.ndarray]:
    """
    Try face_recognition.load_image_file first (fast/C-optimized).
    Fall back to Pillow -> numpy if that fails (useful for HEIC or unusual formats).
    Raise exception on total failure.
    """
    try:
        # prefer face_recognition's loader
        return face_recognition.load_image_file(str(path))
    except Exception as e:
        logger.debug("face_recognition.load_image_file failed for %s: %s", path, e)
        # If this is a HEIC and we don't have a HEIF decoder available,
        # skip attempting to open with Pillow (avoid noisy exceptions).
        if path.suffix.lower() == ".heic" and not _HEIF_AVAILABLE:
            logger.info("HEIC support not available in this environment; skipping face detection for %s", path)
            return None
        try:
            with Image.open(path) as im:
                im_rgb = im.convert("RGB")
                arr = np.array(im_rgb)
                return arr
        except Exception as e2:
            # Don't raise here; return None to let caller skip detection gracefully.
            logger.debug("Pillow failed to open image %s: %s", path, e2)
            return None

def _detect_faces_in_file(path: Path) -> int:
    """
    Load image robustly and return number of face locations detected.
    """
    # Run detection in a separate process to isolate native crashes
    try:
        import subprocess, sys
        worker = Path(__file__).parent / "face_worker.py"
        proc = subprocess.run([sys.executable, str(worker), str(path)], capture_output=True, text=True, timeout=60)
        if proc.returncode == 0:
            out = proc.stdout.strip()
            try:
                count = int(out.splitlines()[-1]) if out else 0
            except Exception:
                count = 0
            logger.info("Detected %d face(s) in %s (via worker)", count, path)
            return count
        else:
            logger.info("Face worker failed for %s (code=%s): %s", path, proc.returncode, proc.stderr.strip())
            return 0
    except subprocess.TimeoutExpired:
        logger.warning("Face worker timed out for %s", path)
        return 0
    except Exception:
        logger.exception("Error running face worker for %s", path)
        return 0

def infer_year_month_from_path(path: str) -> Tuple[Optional[int], Optional[int], Optional[int]]:
    """Best-effort inference of year/month/day from the file path.

    Recognizes patterns like:
      - '/.../06_June/IMG.jpg' -> month=6
      - '/.../2025-06/IMG.jpg' -> year=2025, month=6
      - '/.../25-06/IMG.jpg' -> year=2025, month=6
      - '/.../25/IMG.jpg' -> year=2025
    Returns (year, month, day) where any value may be None.
    """
    try:
        parts = [p for p in Path(path).parts if p and p != os.sep]
        if not parts:
            return None, None, None

        year = None
        month = None
        day = None

        # scan for explicit year segments (4-digit or 2-digit)
        for seg in parts:
            if seg.isdigit() and len(seg) == 4 and (seg.startswith('19') or seg.startswith('20')):
                year = int(seg)
                break
            if seg.isdigit() and len(seg) == 2:
                year = 2000 + int(seg)
                break
            # patterns like 2025-06 or 25-06
            import re
            m = re.match(r'^(?:(19|20)\d{2}|\d{2})[-_](\d{1,2})$', seg)
            if m:
                yseg = seg.split('-')[0].split('_')[0]
                try:
                    yv = int(yseg)
                    if yv < 100:
                        yv += 2000
                    year = yv
                except Exception:
                    pass
                mm = int(m.group(2))
                if 1 <= mm <= 12:
                    month = mm
                break

        # immediate parent directory may contain month info
        # prefer the explicit parent directory name (more robust than parts index)
        parent = Path(path).parent.name if Path(path).parent.name else (parts[-2] if len(parts) >= 2 else '')
        if parent:
            lead = None
            try:
                import re
                lead = re.match(r'^(\d{1,2})', parent)
            except Exception:
                lead = None
            if lead and not month:
                mm = int(lead.group(1))
                if 1 <= mm <= 12:
                    month = mm

            if not month:
                name = parent.lower()
                months = {
                    'january':1,'february':2,'march':3,'april':4,'may':5,'june':6,
                    'july':7,'august':8,'september':9,'october':10,'november':11,'december':12,
                    'jan':1,'feb':2,'mar':3,'apr':4,'jun':6,'jul':7,'aug':8,'sep':9,'oct':10,'nov':11,'dec':12
                }
                for k,v in months.items():
                    if k in name:
                        month = v
                        break

        return year, month, day
    except Exception:
        return None, None, None

def scan_photos():
    """
    Walk PHOTOS_ROOT and process supported files.
    This function logs each file discovered and calls existing processing logic
    (thumbnailing / DB writes) present elsewhere in this module.
    """
    photos_root = Path(os.environ.get("PHOTOS_ROOT", "/photos"))
    logger.info("Starting scan in %s", photos_root)

    inserted = 0
    skipped = 0
    processed = 0

    with get_conn() as conn:
        cur = conn.cursor()

        for root, dirs, files in os.walk(photos_root):
            for fname in files:
                processed += 1
                p = Path(root) / fname
                if p.suffix.lower() not in SUPPORTED_EXT:
                    logger.debug("Skipping unsupported file: %s", p)
                    continue

                full_path = str(p)
                logger.info("Found file: %s", full_path)

                cur.execute("SELECT id FROM photos WHERE path = ?", (full_path,))
                if cur.fetchone():
                    logger.info("Already indexed, skipping: %s", full_path)
                    skipped += 1
                    continue

                # extract EXIF datetime if available
                taken_at = None
                try:
                    with Image.open(full_path) as img:
                        exif = getattr(img, '_getexif', lambda: None)() or {}
                        if exif:
                            raw_dt = None
                            for tag_id, val in exif.items():
                                tag = TAGS.get(tag_id, tag_id)
                                if tag == 'DateTimeOriginal' or tag == 'DateTime':
                                    raw_dt = val
                                    break
                            if raw_dt:
                                try:
                                    taken_at = datetime.strptime(raw_dt, "%Y:%m:%d %H:%M:%S")
                                except Exception:
                                    taken_at = None
                except Exception:
                    # non-fatal; some images (HEIC) may not be openable here
                    taken_at = None

                # infer year/month/day from path if EXIF missing
                year = month = day = None
                if taken_at:
                    year, month, day = taken_at.year, taken_at.month, taken_at.day
                else:
                    iy, im, iday = infer_year_month_from_path(full_path)
                    logger.debug("Path inference for %s -> year=%s month=%s day=%s", full_path, iy, im, iday)
                    if iy is not None:
                        year = iy
                    if im is not None:
                        month = im
                    if iday is not None:
                        day = iday

                # If we still don't have a year/month/day, fall back to file mtime
                # (this mirrors the backfill script behavior so files without EXIF
                # or path-based hints still get a reasonable date).
                if not taken_at or year is None or month is None or day is None:
                    try:
                        mtime = p.stat().st_mtime
                        dt_mtime = datetime.fromtimestamp(mtime)
                        # only fill missing values, don't overwrite existing ones
                        if not taken_at:
                            taken_at = dt_mtime
                        if year is None:
                            year = dt_mtime.year
                        if month is None:
                            month = dt_mtime.month
                        if day is None:
                            day = dt_mtime.day
                        logger.debug("Mtime fallback for %s -> year=%s month=%s day=%s", full_path, year, month, day)
                    except Exception as e:
                        logger.debug("Failed to stat/mtime for %s: %s", full_path, e)

                    # Temporary shim: if year still isn't determined (host path
                    # components not preserved in container), assume 2025.
                    if year is None:
                        year = 2025
                        logger.info("Year not determined for %s — applying temporary shim year=2025", full_path)

                # face detection (worker handles HEIC/no-decoder cases)
                face_count = _detect_faces_in_file(p)
                has_faces = 1 if face_count and face_count > 0 else 0

                # placeholder place_label (could be improved)
                place_label = None

                # insert into DB
                cur.execute(
                    """
                    INSERT INTO photos
                        (path, taken_at, year, month, day, gps_lat, gps_lon, place_label, has_faces, face_count)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        full_path,
                        taken_at.isoformat() if taken_at else None,
                        year,
                        month,
                        day,
                        None,
                        None,
                        place_label,
                        has_faces,
                        face_count,
                    ),
                )
                rowid = cur.lastrowid
                conn.commit()
                inserted += 1
                logger.info("Inserted photo id=%s path=%s faces=%s year=%s month=%s", rowid, full_path, face_count, year, month)

    logger.info("Scan complete: processed=%s inserted=%s skipped=%s", processed, inserted, skipped)
