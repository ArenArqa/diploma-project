import io

import pytest
from PIL import Image

from app.main import app
from app.services import images

pytestmark = pytest.mark.integration


@pytest.fixture
def image_store(tmp_path, monkeypatch):
    monkeypatch.setattr(images, "UPLOAD_DIRECTORY", tmp_path)
    mount = next(route for route in app.routes if getattr(route, "name", None) == "car-images")
    monkeypatch.setattr(mount.app, "directory", str(tmp_path))
    monkeypatch.setattr(mount.app, "all_directories", [str(tmp_path)])
    return tmp_path


def picture(format="PNG"):
    output = io.BytesIO()
    Image.new("RGB", (80, 60), "#789aaa").save(output, format=format)
    return output.getvalue()


@pytest.mark.parametrize(
    "extension,format,mime",
    [
        ("png", "PNG", "image/png"),
        ("jpg", "JPEG", "image/jpeg"),
        ("jpeg", "JPEG", "image/jpeg"),
        ("webp", "WEBP", "image/webp"),
    ],
)
async def test_upload_and_public_display(client, inventory, headers, image_store, extension, format, mime):
    # Warm the cache to verify image publication invalidates old listing payloads.
    await client.get("/api/v1/listings?listing_type=sale")
    payload = picture(format)
    response = await client.post(
        f"/api/v1/cars/{inventory.cars[2]}/image",
        headers=headers["user"],
        files={"file": (f"../../original.{extension}", payload, mime)},
    )
    assert response.status_code == 200, response.text
    url = response.json()["image_url"]
    assert url.startswith("/uploads/cars/") and "original" not in url
    filename = url.rsplit("/", 1)[1]
    assert (image_store / filename).read_bytes() == payload
    served = await client.get(url)
    assert served.status_code == 200 and served.content == payload
    listing = (await client.get(f"/api/v1/listings/{inventory.listings[2]}")).json()
    assert listing["car"]["image_url"] == url
    cached = (await client.get("/api/v1/listings?listing_type=sale")).json()
    assert cached["items"][0]["car"]["image_url"] == url
    replacement = await client.post(
        f"/api/v1/cars/{inventory.cars[2]}/image",
        headers=headers["user"],
        files={"file": (f"new.{extension}", payload, mime)},
    )
    assert replacement.json()["image_url"] != url


@pytest.mark.parametrize(
    "filename,payload,mime,status",
    [
        ("car.svg", b"<svg/>", "image/svg+xml", 415),
        ("car.png", b"not an image", "image/png", 422),
        ("car.jpg", picture(), "image/jpeg", 422),
        ("car.png", picture(), "application/octet-stream", 415),
        ("car.png", b"x" * (5 * 1024 * 1024 + 1), "image/png", 413),
    ],
)
async def test_invalid_upload(client, inventory, headers, image_store, filename, payload, mime, status):
    result = await client.post(
        f"/api/v1/cars/{inventory.cars[2]}/image",
        headers=headers["user"],
        files={"file": (filename, payload, mime)},
    )
    assert result.status_code == status, result.text
    assert not list(image_store.iterdir())


async def test_image_upload_authorization_and_rollback(client, inventory, headers, image_store, monkeypatch):
    path = f"/api/v1/cars/{inventory.cars[2]}/image"
    files = {"file": ("car.png", picture(), "image/png")}
    assert (await client.post(path, files=files)).status_code == 401
    assert (await client.post(path, headers=headers["outsider"], files=files)).status_code == 404
    assert not list(image_store.iterdir())

    def fail_response(*args, **kwargs):
        raise RuntimeError("Simulate transaction failure after saving the file")

    monkeypatch.setattr(images, "car_read", fail_response)
    with pytest.raises(RuntimeError):
        await client.post(path, headers=headers["user"], files=files)
    assert not list(image_store.iterdir())
    assert (await client.get(f"/api/v1/cars/{inventory.cars[2]}", headers=headers["user"])).json()[
        "image_url"
    ] is None
