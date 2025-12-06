#!/usr/bin/env python3
"""Backfill missing taken_at / year / month / day in the photos DB.

Strategy (per-row):
- try EXIF DateTimeOriginal via scanner._extract_exif
- if missing, try to infer year/month from parent path segments
- if still missing, fall back to filesystem mtime

Run inside the backend container (project root):
  docker compose exec backend python3 /app/backend/backfill_dates.py

"""
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

from scanner import _extract_exif
from db import get_conn


def infer_year_month_from_path(path: str) -> Tuple[Optional[int], Optional[int], Optional[int]]:
    """Infer year, month, day from path components (best-effort).

    Examples supported:
      /photos/06_June/IMG.jpg -> month 6
      /photos/2025-06/IMG.jpg -> year 2025, month 6
      /photos/25-06/IMG.jpg -> year 2025, month 6
      /photos/25/IMG.jpg -> year 2025
    """
    try:
        parts = [p for p in Path(path).parts if p and p != os.sep]
        if not parts:
            return None, None, None

        year = None
        month = None
        day = None

        # scan for 4-digit year, 2-digit year, or year-week style
        for seg in parts:
            if seg.isdigit() and len(seg) == 4 and (seg.startswith('19') or seg.startswith('20')):
                year = int(seg)
                break
            if seg.isdigit() and len(seg) == 2:
                year = 2000 + int(seg)
                break
            m = None
            # patterns like 2025-06 or 25-06
            import re
            m = re.match(r'^(?:(19|20)\d{2}|\d{2})[-_](\d{1,2})$', seg)
            if m:
                yseg = m.group(1)
                if yseg and len(yseg) == 2:
                    year = 2000 + int(yseg)
                elif yseg:
                    year = int(yseg)
                else:
                    # fallback if group capture differs
                    try:
                        year = int(seg.split('-')[0])
                        if year < 100:
                            year += 2000
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
            # leading numeric month (06_June, 6-June)
            import re
            lead = re.match(r'^(\d{1,2})', parent)
            if lead and not month:
                mm = int(lead.group(1))
                if 1 <= mm <= 12:
                    month = mm

            # month names
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


def main():
    rows_processed = 0
    rows_updated = 0
    missing_files = 0

    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, path, year, month, day FROM photos WHERE year IS NULL OR month IS NULL")
        rows = cur.fetchall()

        print(f"Found {len(rows)} rows with missing year/month to process")

        for r in rows:
            rows_processed += 1
            pid, path, year, month, day = r
            if not path:
                continue
            if not os.path.exists(path):
                print(f"File not found on disk, skipping: {path}")
                missing_files += 1
                continue

            taken_at = None
            try:
                dt, _gps = _extract_exif(path)
                if dt:
                    taken_at = dt.isoformat()
                    ny, nm, nd = dt.year, dt.month, dt.day
                    year = ny
                    month = nm
                    day = nd
                else:
                    iy, im, iday = infer_year_month_from_path(path)
                    if iy and im:
                        year = iy
                        month = im
                        day = iday
                    else:
                        # fallback to mtime
                        try:
                            mtime = os.path.getmtime(path)
                            d2 = datetime.fromtimestamp(mtime)
                            taken_at = d2.isoformat()
                            year = d2.year
                            month = d2.month
                            day = d2.day
                        except Exception:
                            pass
            except Exception as e:
                print(f"Error processing {path}: {e}")

            # update row if we found anything useful
            # Temporary shim: if year still isn't determined, assume 2025.
            if not year:
                year = 2025
                print(f"Year not determined for {path} — applying temporary shim year=2025")

            if year or month or taken_at:
                cur.execute(
                    "UPDATE photos SET taken_at = ?, year = ?, month = ?, day = ? WHERE id = ?",
                    (taken_at, year, month, day, pid),
                )
                rows_updated += 1

        conn.commit()

    print(f"Processed: {rows_processed}, Updated: {rows_updated}, Missing files: {missing_files}")


if __name__ == '__main__':
    main()
