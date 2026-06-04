"""
Database-agnostic type helpers for SQLAlchemy models.

When running against PostgreSQL (production), we use native PostgreSQL types.
When running against SQLite (tests), we fall back to portable equivalents.
"""
from __future__ import annotations

import uuid as _uuid_mod
from typing import Any

from sqlalchemy import DateTime, JSON, String, TypeDecorator, CHAR
from sqlalchemy.dialects.postgresql import UUID as PG_UUID


class UUIDType(TypeDecorator):
    """
    Platform-independent UUID column type.
    - PostgreSQL: uses native UUID type
    - SQLite / others: stores as CHAR(36) string
    """
    impl = CHAR(36)
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if dialect.name == "postgresql":
            return value if isinstance(value, _uuid_mod.UUID) else _uuid_mod.UUID(str(value))
        return str(value) if isinstance(value, _uuid_mod.UUID) else str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if not isinstance(value, _uuid_mod.UUID):
            return _uuid_mod.UUID(str(value))
        return value


# Timezone-aware datetime, works on both PostgreSQL and SQLite
TZDateTime = DateTime(timezone=True)
