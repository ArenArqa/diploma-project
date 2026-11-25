from decimal import Decimal
from typing import Annotated, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer, model_validator

DecimalValue = Annotated[
    Decimal, PlainSerializer(lambda value: format(value, "f"), return_type=str, when_used="json")
]
Money = Annotated[DecimalValue, Field(gt=0, max_digits=14, decimal_places=0)]
T = TypeVar("T")


class Schema(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True, str_strip_whitespace=True)


class Patch(Schema):
    @model_validator(mode="after")
    def forbid_explicit_null(self):
        for field in self.model_fields_set:
            if getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null; omit it to leave it unchanged")
        if not self.model_fields_set:
            raise ValueError("Supply at least one field")
        return self


class Page(Schema, Generic[T]):
    items: list[T]
    limit: int
    offset: int | None = None
    total: int | None = None
    next_cursor: str | None = None


class OffsetQuery(Schema):
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0, le=10000)


class ErrorBody(Schema):
    code: str
    message: str
    details: dict | list | None = None


class ErrorResponse(Schema):
    error: ErrorBody
