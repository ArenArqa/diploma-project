import uuid
from datetime import datetime
from typing import Annotated

from sqlalchemy import DateTime, MetaData, func
from sqlalchemy.orm import DeclarativeBase, mapped_column

NAMING = {
    "ix": "ix_%(table_name)s_%(column_0_name)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING)


UUIDPK = Annotated[uuid.UUID, mapped_column(primary_key=True, default=uuid.uuid4)]
Created = Annotated[datetime, mapped_column(DateTime(timezone=True), server_default=func.now())]
Updated = Annotated[
    datetime, mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
]
