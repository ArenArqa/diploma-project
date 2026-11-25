from enum import StrEnum


class Role(StrEnum):
    user = "user"
    dealer = "dealer"
    admin = "admin"


class ListingType(StrEnum):
    sale = "sale"
    rent = "rent"


class ListingStatus(StrEnum):
    active = "active"
    archived = "archived"
    sold = "sold"


class BookingStatus(StrEnum):
    confirmed = "confirmed"
    cancelled = "cancelled"


class FuelType(StrEnum):
    gasoline = "gasoline"
    diesel = "diesel"
    hybrid = "hybrid"
    electric = "electric"
    lpg = "lpg"


class Transmission(StrEnum):
    manual = "manual"
    automatic = "automatic"


class Condition(StrEnum):
    poor = "poor"
    fair = "fair"
    good = "good"
    excellent = "excellent"
