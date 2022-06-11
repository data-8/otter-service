import otter_service.create_database as cb
import os
import pytest
from helper import make_db, create_connection


@pytest.fixture
def setup():
    os.environ["VOLUME_PATH"] = "tests/test_files"
    db_path = os.environ["VOLUME_PATH"] + "/gradebook.db"
    make_db(db_path)
    conn = create_connection(db_path)
    yield conn
    conn.close()
    os.remove(db_path)
    del os.environ["VOLUME_PATH"]


def test_create_db():
    os.environ["VOLUME_PATH"] = "tests/test_files"
    db_path = os.environ["VOLUME_PATH"] + "/gradebook.db"
    cb.main()
    assert os.path.exists(db_path)


def test_get_records(setup):
    db_conn = setup
    cur = db_conn.cursor()
    cur.execute("SELECT * FROM GRADES;")
    data = cur.fetchall()
    cols = list(map(lambda x: x[0], cur.description))
    users = list(map(lambda x: x[0], data))
    assert "grade" in cols
    assert "TEST_USER" in users
