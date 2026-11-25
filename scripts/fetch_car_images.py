"""Fetch vetted exact-model Commons photographs; normal application use is offline.

The source manifest is deliberately curated: search results can include badges,
interiors, toy cars, collages, and different models. Original file names and
author/license records were checked against their Commons description pages.
Direct public upload.wikimedia.org URLs avoid depending on API availability.
"""

import argparse
import hashlib
import io
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]
DESTINATION = ROOT / "frontend/uploads/cars"
SOURCE_MANIFEST = ROOT / "data/car_image_sources.json"
MIN_BYTES = 15 * 1024


def source_records():
    rows = json.loads(SOURCE_MANIFEST.read_text())
    return [(row, number, photo) for row in rows for number, photo in enumerate(row["photos"], 1)]


def local_name(row, number):
    return f"{row['brand_slug']}/{row['model_slug']}_{number}.jpg"


def commons_url(filename):
    normalized = filename.replace(" ", "_")
    digest = hashlib.md5(normalized.encode(), usedforsecurity=False).hexdigest()
    quoted = urllib.parse.quote(normalized, safe="")
    # Wikimedia recommends cached standard thumbnail sizes over large originals.
    # 1280px is high resolution for the demo's 200px cards and detail views.
    return f"https://upload.wikimedia.org/wikipedia/commons/thumb/{digest[0]}/{digest[:2]}/{quoted}/1280px-{quoted}"


def validate_photo(path):
    if path.stat().st_size <= MIN_BYTES:
        raise ValueError(f"Image must exceed 15 KiB: {path}")
    with Image.open(path) as image:
        if image.format != "JPEG" or image.width < 1200 or image.height < 500:
            raise ValueError(f"Expected a high-resolution landscape JPEG: {path}")
        image.verify()
    with Image.open(path) as image:
        image.load()
    return hashlib.sha256(path.read_bytes()).hexdigest()


def download(url):
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "AutoMetricDiploma/1.0 (educational offline vehicle catalog)",
        },
    )
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                data = response.read(50 * 1024 * 1024 + 1)
                if len(data) > 50 * 1024 * 1024:
                    raise ValueError("Original image exceeds 50 MiB")
                return data
        except urllib.error.HTTPError as error:
            if error.code not in (429, 500, 502, 503, 504) or attempt == 2:
                raise
            delay = max(2**attempt, int(error.headers.get("Retry-After", "5")))
            if delay > 60:
                raise RuntimeError("Source rate-limited; retry the fetch command later") from error
            time.sleep(delay)
        except (TimeoutError, urllib.error.URLError):
            if attempt == 2:
                raise
            time.sleep(2**attempt)


def fetch_images(refresh=False):
    records = source_records()
    credits = {}
    previous = (
        json.loads((DESTINATION / "credits.json").read_text())
        if (DESTINATION / "credits.json").exists()
        else {}
    )
    hashes = set()
    failures = []
    for row, number, photo in records:
        name = local_name(row, number)
        target = DESTINATION / name
        url = commons_url(photo["commons_filename"])
        cached_source = previous.get(name, {}).get("commons_filename")
        if refresh or not target.exists() or cached_source not in (None, photo["commons_filename"]):
            try:
                try:
                    raw = download(url)
                except urllib.error.HTTPError as error:
                    if error.code not in (404, 429):
                        raise
                    # Some archived files have no cached thumbnail. Try the original
                    # only after honoring the thumbnail service's retry response.
                    raw = download(url.rsplit("/", 1)[0].replace("/commons/thumb/", "/commons/"))
            except (OSError, RuntimeError) as error:
                failures.append(f"{name}: {error}")
                print(f"Pending {name}: {error}", flush=True)
                continue
            with Image.open(io.BytesIO(raw)) as original:
                if original.format not in ("JPEG", "PNG", "MPO"):
                    raise ValueError(f"Source must be a real raster photograph, got {original.format}: {url}")
                image = ImageOps.exif_transpose(original).convert("RGB")
                image.thumbnail((1800, 1400), Image.Resampling.LANCZOS)
                target.parent.mkdir(parents=True, exist_ok=True)
                temporary = target.with_suffix(".part")
                try:
                    image.save(temporary, "JPEG", quality=93, optimize=True)
                    validate_photo(temporary)
                    temporary.replace(target)
                finally:
                    temporary.unlink(missing_ok=True)
            time.sleep(0.4)
        digest = validate_photo(target)
        if digest in hashes:
            raise ValueError(f"Duplicate photo content: {name}")
        hashes.add(digest)
        credits[name] = {
            **photo,
            "brand_slug": row["brand_slug"],
            "model_slug": row["model_slug"],
            "source": "https://commons.wikimedia.org/wiki/File:"
            + urllib.parse.quote(photo["commons_filename"].replace(" ", "_"), safe=""),
            "original_url": url.rsplit("/", 1)[0].replace("/commons/thumb/", "/commons/"),
            "download_url": url,
            "sha256": digest,
            "changes": "EXIF orientation applied, resized and converted to JPEG. No synthetic content. "
            "This derivative is distributed under the original CC BY-SA 4.0 license.",
        }
        print(f"Validated {name}: {target.stat().st_size:,} bytes", flush=True)
    if failures:
        raise RuntimeError(
            "Incomplete downloads; rerun to reuse verified local photos: " + "; ".join(failures)
        )
    if len(credits) < 36:
        raise ValueError("At least 36 unique exact-model photos required")
    (DESTINATION / "credits.json").write_text(json.dumps(credits, ensure_ascii=False, indent=2) + "\n")
    print(f"Complete: {len(credits)} unique real photographs; all credits saved locally.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--refresh", action="store_true", help="Download again instead of validating cached files"
    )
    fetch_images(parser.parse_args().refresh)
