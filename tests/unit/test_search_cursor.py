from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.core.exceptions import DomainError
from app.repositories.search import decode_cursor, encode_cursor
from app.schemas.listing import ListingSearchQuery


def test_cursor_round_trip_and_filter_binding():
    params = ListingSearchQuery(pagination="cursor")
    value, identifier = datetime(2026, 1, 1, tzinfo=UTC), uuid4()
    cursor = encode_cursor(params, value.isoformat(), identifier)
    assert decode_cursor(params.model_copy(update={"cursor": cursor})) == (value, identifier)
    with pytest.raises(DomainError):
        decode_cursor(params.model_copy(update={"cursor": cursor, "year_min": 2020}))


def test_tampered_cursor():
    with pytest.raises(DomainError):
        decode_cursor(ListingSearchQuery(pagination="cursor", cursor="not-a-signed-cursor"))


@pytest.mark.parametrize(
    "values",
    [
        {"year_min": 2025, "year_max": 2020},
        {"sort": "price_asc"},
        {"cursor": "x"},
        {"pagination": "cursor", "offset": 20},
    ],
)
def test_invalid_search(values):
    with pytest.raises(ValidationError):
        ListingSearchQuery(**values)
