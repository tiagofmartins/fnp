#!/usr/bin/env python3
"""Take a photo from every available camera, on macOS, via imagesnap.

Requires:  brew install imagesnap
"""

import re
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

from PIL import Image


def list_cameras():
    """Names of every camera imagesnap can see."""
    output = subprocess.run(["imagesnap", "-l"], capture_output=True, text=True, check=True).stdout
    return re.findall(r"^=> (.+)$", output, re.MULTILINE)


def capture_photo(camera_name):
    """Take one photo with the named camera, as a PIL Image. 1 second
    warmup, since a camera's first frame is often stale/black right after
    opening. imagesnap can only write to a real file, so one is used
    internally and discarded."""
    with tempfile.NamedTemporaryFile(suffix=".jpg") as tmp:
        subprocess.run(["imagesnap", "-d", camera_name, "-w", "1", "-q", tmp.name], check=True)
        image = Image.open(tmp.name)
        image.load()
    return image


def capture_photos():
    """Take a photo with every available camera. A camera that fails (e.g.
    the built-in one, while the lid is closed) is skipped rather than
    aborting the rest. Returns an empty dict if none succeed."""
    photos = {}
    for camera_name in list_cameras():
        try:
            photos[camera_name] = capture_photo(camera_name)
        except (subprocess.CalledProcessError, OSError):
            continue
    return photos


if __name__ == "__main__":
    output_dir = Path(__file__).parent / "camera_photos"
    output_dir.mkdir(exist_ok=True)
    timestamp = f"{datetime.now():%Y-%m-%d %H.%M.%S}"
    for camera_name, image in capture_photos().items():
        path = output_dir / f"{timestamp} {camera_name}.jpg"
        image.save(path)
        print(path)