import pytest
import tempfile
import os
from evolution.db_utils import get_evolution_db


@pytest.fixture
def temp_db():
    """隔离的内存数据库"""
    conn = get_evolution_db(":memory:")
    yield conn
    conn.close()


@pytest.fixture
def clean_data_dir(tmp_path):
    """隔离的数据目录"""
    os.environ["EVOLUTION_DATA_DIR"] = str(tmp_path)
    yield tmp_path
    if "EVOLUTION_DATA_DIR" in os.environ:
        del os.environ["EVOLUTION_DATA_DIR"]
