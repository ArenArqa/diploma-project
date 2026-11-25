"""Install and verify the exact-model photo dataset in a persistent uploads volume."""

import json
import shutil
from pathlib import Path

from scripts.fetch_car_images import local_name, source_records, validate_photo

ROOT = Path(__file__).resolve().parents[1]
UPLOADS = ROOT / "frontend/uploads/cars"


def install_photos():
    source = ROOT / "bundled-car-photos"
    if source.is_dir():
        for row, number, _ in source_records():
            name = local_name(row, number)
            target = UPLOADS / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source / name, target)
        shutil.copyfile(source / "credits.json", UPLOADS / "credits.json")
    credits = json.loads((UPLOADS / "credits.json").read_text())
    hashes = set()
    for row, number, _ in source_records():
        name = local_name(row, number)
        digest = validate_photo(UPLOADS / name)
        if digest != credits[name]["sha256"] or digest in hashes:
            raise ValueError(f"Photo dataset integrity failed: {name}")
        hashes.add(digest)
    if len(hashes) < 36:
        raise ValueError("At least 36 unique exact-model car photos required")


if __name__ == "__main__":
    install_photos()
