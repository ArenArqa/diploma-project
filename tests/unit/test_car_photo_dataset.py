import csv
import hashlib
import json
from collections import Counter

from scripts.fetch_car_images import DESTINATION, ROOT, local_name, source_records, validate_photo
from scripts.update_car_images import model_photo_urls


def test_every_supported_model_has_three_unique_real_photos():
    records = source_records()
    with (ROOT / "data/demo_baselines.csv").open() as source:
        expected = {(row["brand_slug"], row["model_slug"]) for row in csv.DictReader(source)}
    counts = Counter((row["brand_slug"], row["model_slug"]) for row, _, _ in records)
    assert set(counts) == expected and len(expected) == 12
    assert all(3 <= count <= 5 for count in counts.values())
    digests = set()
    credits = json.loads((DESTINATION / "credits.json").read_text())
    for row, number, photo in records:
        name = local_name(row, number)
        digest = validate_photo(DESTINATION / name)
        assert digest not in digests, f"Reused photo: {name}"
        digests.add(digest)
        assert credits[name]["sha256"] == digest
        assert credits[name]["author"] == photo["author"]
        assert credits[name]["commons_filename"] == photo["commons_filename"]
        assert credits[name]["source"].startswith("https://commons.wikimedia.org/wiki/File:")
        assert credits[name]["license_url"] == "https://creativecommons.org/licenses/by-sa/4.0/"
    assert len(digests) >= 36


def test_each_photo_url_belongs_to_its_exact_model():
    for (brand, model), urls in model_photo_urls().items():
        assert len(urls) == len(set(urls)) >= 3
        assert all(url.startswith(f"/uploads/cars/{brand}/{model}_") and url.endswith(".jpg") for url in urls)


def test_source_files_are_distinct_across_models():
    sources = [
        hashlib.sha256(photo["commons_filename"].encode()).hexdigest() for _, _, photo in source_records()
    ]
    assert len(sources) == len(set(sources))
