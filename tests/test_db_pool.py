import pytest
from evolution.db_pool import DatabasePool


def test_singleton():
    p1 = DatabasePool()
    p2 = DatabasePool()
    assert p1 is p2


def test_connection_context():
    pool = DatabasePool()
    with pool.connection(":memory:") as conn:
        conn.execute("CREATE TABLE test (id INTEGER)")
        conn.execute("INSERT INTO test VALUES (1)")
        row = conn.execute("SELECT * FROM test").fetchone()
        assert row[0] == 1
