import pytest
from evolution.schema import ensure_schema, SCHEMA_VERSION


def test_ensure_schema():
    ensure_schema(":memory:", target_version=SCHEMA_VERSION)
    # 应该不报错


def test_get_schema_version():
    from evolution.schema import get_schema_version
    version = get_schema_version(":memory:")
    assert version >= 0
