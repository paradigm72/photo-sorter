#!/usr/bin/env python3
"""Small helper to run face detection in a separate process.

Usage: python3 face_worker.py /path/to/image
Outputs the integer count of faces to stdout on success, and exits
with non-zero on failure.
"""
import sys
from pathlib import Path
try:
    import face_recognition
    from PIL import Image
    import numpy as np
except Exception as e:
    print("error: missing deps", file=sys.stderr)
    sys.exit(2)


def load_image(path: Path):
    try:
        return face_recognition.load_image_file(str(path))
    except Exception:
        try:
            with Image.open(path) as im:
                return np.array(im.convert("RGB"))
        except Exception:
            return None


def main():
    if len(sys.argv) < 2:
        print("usage: face_worker.py <image>", file=sys.stderr)
        sys.exit(2)
    p = Path(sys.argv[1])
    img = load_image(p)
    if img is None:
        print("0")
        sys.exit(0)
    try:
        locs = face_recognition.face_locations(img, model="hog")
        print(len(locs))
        sys.exit(0)
    except Exception as e:
        print("0")
        sys.exit(1)


if __name__ == '__main__':
    main()
