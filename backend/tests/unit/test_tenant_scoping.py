"""Architecture guard: every tenant-owned table must have tenant_id NOT NULL, indexed.

Add a new table to TENANT_EXEMPT only if it is not tenant-owned (for example "tenants").
"""

import app.db.models  # noqa: F401  (registers all tables)
from app.db.base import Base

TENANT_EXEMPT = {"tenants"}


def test_every_tenant_owned_table_has_indexed_not_null_tenant_id():
    for name, table in Base.metadata.tables.items():
        if name in TENANT_EXEMPT:
            continue
        column = table.c.get("tenant_id")
        assert column is not None, f"{name} is missing tenant_id"
        assert not column.nullable, f"{name}.tenant_id must be NOT NULL"
        indexed = any(
            list(index.columns)[0].name == "tenant_id" for index in table.indexes
        )
        assert indexed, f"{name}.tenant_id needs an index"


def test_expected_tables_exist():
    assert {"tenants", "users", "api_keys"} <= set(Base.metadata.tables)


def test_api_key_table_never_stores_the_raw_key():
    columns = set(Base.metadata.tables["api_keys"].c.keys())
    assert "key_hash" in columns and "key_prefix" in columns
    assert "key" not in columns and "raw_key" not in columns
