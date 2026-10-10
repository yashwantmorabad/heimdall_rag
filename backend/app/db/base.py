"""Base class for all database models. Alembic reads Base.metadata."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
