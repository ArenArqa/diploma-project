from decimal import Decimal

SALE_VERSION = "sale-v1"
RENTAL_VERSION = "rent-v1"
CONDITION = {
    "poor": Decimal(".80"),
    "fair": Decimal(".90"),
    "good": Decimal("1.00"),
    "excellent": Decimal("1.08"),
}
SEASONS = {
    1: ".90",
    2: ".90",
    3: "1",
    4: "1",
    5: "1",
    6: "1.20",
    7: "1.20",
    8: "1.20",
    9: "1",
    10: "1",
    11: "1",
    12: "1.10",
}
