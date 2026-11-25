from typing import Literal

from app.schemas.common import Schema


class LiveRead(Schema):
    status: Literal["ok"] = "ok"


class HealthRead(Schema):
    status: Literal["ok", "degraded", "unavailable"]
    database: Literal["up", "down"]
    redis: Literal["up", "down", "unchecked"]
