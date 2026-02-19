from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.orm import DeclarativeBase, declared_attr


class Base(DeclarativeBase):
    pass


class TimeStampMixin:
    @declared_attr
    def created_at(cls):
        return sa.Column(
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        )
