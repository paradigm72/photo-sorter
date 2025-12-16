# Photo Sorter

> A small self-hosted tool to scan a folder of photos, extract metadata (EXIF, GPS, dates), detect faces, and browse/sort them via a web UI.

This repo contains a backend API (Python + FastAPI) and a Next.js frontend. The app is designed to run in Docker Compose with a host-mounted photo directory and a SQLite database stored in a data volume.

---

## Highlights

- Scans a photos directory for supported image files and inserts metadata into a SQLite database.
- Extracts EXIF date/time and GPS when available, otherwise infers dates from file mtime or path.
- Optional HEIC/HEIF decoding via `pillow-heif` (native deps required in the container).
- Face detection using `face_recognition` (dlib) — run isolated in a subprocess to protect the main server from native crashes.
- Background incremental scans and full rescans with a scan status endpoint and frontend controls.
- Server-side thumbnailing endpoint to convert images to browser-friendly JPEG thumbnails.

---

## Repository Layout

- `backend/` — FastAPI app and scanner code
  - `main.py` — API endpoints (scan, scan/status, photos, times, people, thumbnail, image)
  - `scanner.py` — file discovery, EXIF extraction, inference, face detection orchestration
  - `face_worker.py` — subprocess worker that runs face detection for a single image
  - `db.py` — SQLite helpers and schema initialization
  - `backfill_dates.py` — one-shot script to backfill missing date fields
  - `requirements.txt`, `Dockerfile`
- `frontend/` — Next.js app (TypeScript), pages and components
  - `app/` — Next 14 app dir pages (Dashboard, Times, People, Places)
  - `components/RescanControls.tsx` — UI to start scans and poll status

---

## Running (Docker Compose)

1. Mount a directory with your photos into the backend container. By default the backend expects the photos at `/photos` inside the container. Example `docker-compose.yml` sets up this mount.

2. Build and run both services:

```bash
docker compose up -d --build backend frontend
```

3. Watch logs (backend does scanning and thumbnail generation):

```bash
docker compose logs -f backend
```

4. Use the web UI (Next.js frontend) to view Times/People/Places and trigger scans.

API endpoints (examples):
- `POST /scan` — start an incremental background scan
- `POST /scan/full` — clear DB and do a full rescan
- `GET /scan/status` — check scan progress and counts
- `GET /photo/{id}/image` — return original file (no conversion)
- `GET /photo/{id}/thumbnail` — return a JPEG thumbnail (server-side conversion)

---

## Important Implementation Notes

- HEIC/HEIF support: the project can decode HEIC images via `pillow-heif`. To enable this in the backend container we install `pillow-heif` and native dependencies (`libheif-dev`, `libde265-dev`, `pkg-config`) in the Dockerfile. Rebuilding the backend image will compile the extension; builds can take extra time.

- Face detection: we use `face_recognition` (dlib). Building dlib in the container is slow and occasionally fragile on some hosts. To avoid bringing down the server when native code crashes, face detection is executed inside a short-lived subprocess (`face_worker.py`) with a timeout. For faster builds in dev you can remove `face_recognition` from `backend/requirements.txt` and run face detection on your host or a dedicated worker container.

- Database: SQLite stored at `/data/photos.db`. `db.py` opens connections with WAL mode and a longer timeout to reduce locking issues during concurrent operations.

- Date inference: the scanner attempts to read EXIF `DateTimeOriginal` first. If missing, it can infer month/year from parent directory names, then fall back to file mtime. There is currently a temporary shim that sets missing years to `2025` when the host path segments are not visible inside the container — this is deliberate for short-term convenience and can be removed.

- Thumbnailing: Browsers often can't render HEIC; the `/photo/{id}/thumbnail` endpoint converts images to JPEG thumbnails server-side so the frontend can reliably display previews. If Pillow can't open a file (HEIC without pillow-heif), the endpoint returns a 415 with guidance in the response.

---

## Developer Tips

- Rebuild backend image after dependency/Dockerfile changes:
```bash
docker compose up -d --build backend
```

- Run backfill script inside the backend container to populate missing dates:
```bash
docker compose exec backend python3 /app/backend/backfill_dates.py
```

- Trigger scans from the host:
```bash
curl -X POST http://localhost:8000/scan
curl -X POST http://localhost:8000/scan/full
```

- If you run into DB locking errors, ensure the backend uses WAL (it does by default in `db.py`) and check for long-running transactions. Restarting the backend and retrying a scan often clears transient locks.

- If you need to remove large files from git history (e.g., a tracked DB or node_modules), create a mirror and use history-rewrite tools — be careful: rewriting public history requires force pushes and coordination.

---

## Roadmap / Ideas

- Move face detection into a dedicated worker service (separate container with conda or prebuilt dlib wheels) to avoid long backend builds and improve reliability.
- Add pagination / lazy-loading to the frontend for very large collections.
- Add unit-tests for scanner inference logic and the face worker.
- Improve place inference (reverse geocoding or facial metadata grouping).

---

If you'd like, I can also add a short CONTRIBUTING.md with local dev steps, or patch CI to run linting and a small test suite. Want me to add that too?
