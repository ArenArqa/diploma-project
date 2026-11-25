from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

BUSINESS_TZ = ZoneInfo("Asia/Yerevan")


def now() -> datetime:
    return datetime.now(UTC)


def today() -> date:
    return now().astimezone(BUSINESS_TZ).date()
