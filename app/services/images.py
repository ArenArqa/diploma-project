import io
import logging
import warnings
from pathlib import Path
from uuid import uuid4

from fastapi.concurrency import run_in_threadpool
from PIL import Image, UnidentifiedImageError

from app.core.exceptions import DomainError
from app.repositories.inventory import get_car, require_owner
from app.services.cache import invalidate_catalog
from app.services.inventory import car_read
from app.services.transactions import transaction

UPLOAD_DIRECTORY = Path(__file__).resolve().parents[2] / "frontend/uploads/cars"
MAX_IMAGE_BYTES = 5 * 1024 * 1024
FORMATS = {
    ".jpg": ("JPEG", "image/jpeg"),
    ".jpeg": ("JPEG", "image/jpeg"),
    ".png": ("PNG", "image/png"),
    ".webp": ("WEBP", "image/webp"),
}
log = logging.getLogger(__name__)


def validate_image(data, filename, content_type):
    extension = Path(filename or "").suffix.lower()
    expected = FORMATS.get(extension)
    if not expected or content_type != expected[1]:
        raise DomainError(415, "invalid_image_type", "Upload a JPG, JPEG, PNG, or WebP image.")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as image:
                if image.format != expected[0] or image.width * image.height > 20_000_000:
                    raise ValueError("Image format mismatch or excessive dimensions")
                image.verify()
            with Image.open(io.BytesIO(data)) as image:
                image.load()
    except (
        UnidentifiedImageError,
        OSError,
        ValueError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
    ) as exc:
        raise DomainError(422, "invalid_image", "Provide a valid image of at most 20 megapixels.") from exc
    return ".jpg" if extension == ".jpeg" else extension


async def upload_car_image(session, actor, car_id, upload):
    saved = None
    try:
        async with transaction(session):
            car = await get_car(session, car_id, lock=True)
            require_owner(car, actor)
            data = await upload.read(MAX_IMAGE_BYTES + 1)
            if len(data) > MAX_IMAGE_BYTES:
                raise DomainError(413, "image_too_large", "Maximum image size is 5 MB.")
            extension = await run_in_threadpool(validate_image, data, upload.filename, upload.content_type)
            filename = f"{uuid4().hex}{extension}"
            UPLOAD_DIRECTORY.mkdir(parents=True, exist_ok=True)
            saved = UPLOAD_DIRECTORY / filename
            await run_in_threadpool(saved.write_bytes, data)
            car.image_url = f"/uploads/cars/{filename}"
            await session.flush()
            await session.refresh(car, ["updated_at"])
            response = car_read(car, private=True)
    except BaseException:
        if saved:
            saved.unlink(missing_ok=True)
        raise
    finally:
        await upload.close()
    # Retain previous files: a client may still hold a cached URL for up to 60s.
    await invalidate_catalog()
    return response
