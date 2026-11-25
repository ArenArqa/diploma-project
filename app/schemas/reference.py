from uuid import UUID

from app.schemas.common import Schema


class BrandRead(Schema):
    id: UUID
    name: str
    slug: str


class ModelRead(Schema):
    id: UUID
    brand_id: UUID
    name: str
    slug: str
