import base64
import hashlib
import hmac
import json
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select, tuple_

from app.core.config import get_settings
from app.core.exceptions import DomainError
from app.models import Car, CarModel, Listing, User
from app.models.enums import ListingStatus
from app.repositories.inventory import listing_options


def fingerprint(params):
    data = params.model_dump(mode="json", exclude={"cursor", "limit", "offset", "pagination"})
    return hashlib.sha256(json.dumps(data, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def encode_cursor(params, value, listing_id):
    payload = json.dumps(
        {"v": 1, "filter": fingerprint(params), "value": str(value), "id": str(listing_id)},
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    signature = hmac.new(get_settings().jwt_secret.encode(), b"catalog-cursor:" + payload, "sha256").digest()
    return base64.urlsafe_b64encode(signature + payload).decode()


def decode_cursor(params):
    try:
        raw = base64.b64decode(params.cursor, altchars=b"-_", validate=True)
        signature, payload = raw[:32], raw[32:]
        expected = hmac.new(
            get_settings().jwt_secret.encode(), b"catalog-cursor:" + payload, "sha256"
        ).digest()
        if not hmac.compare_digest(signature, expected):
            raise ValueError
        data = json.loads(payload)
        if data["v"] != 1 or data["filter"] != fingerprint(params):
            raise ValueError
        listing_id = UUID(data["id"])
        if params.sort == "newest":
            value = datetime.fromisoformat(data["value"])
            if value.tzinfo is None:
                raise ValueError
        elif params.sort.startswith("price"):
            value = Decimal(data["value"])
            if not value.is_finite() or value <= 0:
                raise ValueError
        else:
            value = int(data["value"])
        return value, listing_id
    except (ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        raise DomainError(
            422, "invalid_cursor", "Cursor is invalid or belongs to different filters."
        ) from exc


def sort_spec(sort):
    return {
        "newest": (Listing.created_at, True),
        "price_asc": (Listing.price_amd, False),
        "price_desc": (Listing.price_amd, True),
        "year_desc": (Car.year, True),
        "mileage_asc": (Car.mileage_km, False),
    }[sort]


def search_query(params):
    query = (
        select(Listing)
        .join(Car)
        .join(CarModel)
        .join(User, Car.owner_id == User.id)
        .where(Listing.status == ListingStatus.active, User.is_active.is_(True))
    )
    for value, expression in [
        (params.brand_id, CarModel.brand_id == params.brand_id),
        (params.model_id, Car.model_id == params.model_id),
        (params.year_min, Car.year >= (params.year_min or 0)),
        (params.year_max, Car.year <= (params.year_max or 2100)),
        (params.price_min, Listing.price_amd >= (params.price_min or 0)),
        (params.price_max, Listing.price_amd <= (params.price_max or 0)),
        (params.mileage_max, Car.mileage_km <= (params.mileage_max or 0)),
        (params.fuel_type, Car.fuel_type == params.fuel_type),
        (params.listing_type, Listing.listing_type == params.listing_type),
    ]:
        if value is not None:
            query = query.where(expression)
    return query


def paginated_query(query, params):
    column, descending = sort_spec(params.sort)
    if params.cursor:
        value, listing_id = decode_cursor(params)
        boundary = tuple_(column, Listing.id)
        query = query.where(boundary < (value, listing_id) if descending else boundary > (value, listing_id))
    query = query.order_by(
        column.desc() if descending else column.asc(), Listing.id.desc() if descending else Listing.id.asc()
    )
    return query.options(*listing_options()).offset(params.offset if params.pagination == "offset" else 0)


def cursor_value(listing, sort):
    return {
        "newest": listing.created_at,
        "price_asc": listing.price_amd,
        "price_desc": listing.price_amd,
        "year_desc": listing.car.year,
        "mileage_asc": listing.car.mileage_km,
    }[sort]
