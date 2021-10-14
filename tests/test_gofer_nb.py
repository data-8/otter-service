import json
import requests
import pytest
import os
import gofer_service.gofer_nb as gn
from helper import make_db, create_connection


@pytest.fixture
def app():
    VOLUME_PATH = "/tmp/gofer"
    os.makedirs(VOLUME_PATH, exist_ok=True)
    gn.ERROR_FILE = f"{VOLUME_PATH}/" + os.getenv("ERROR_FILE")
    return gn.start_server()


@pytest.fixture
def setup_db():
    os.environ["VOLUME_PATH"] = "tests/test_files"
    db_path = os.environ["VOLUME_PATH"] + "/gradebook.db"
    make_db(db_path)
    conn = create_connection(db_path)
    yield conn, db_path
    os.remove(db_path)
    del os.environ["VOLUME_PATH"]

async def test_http_client(http_server_client):
    resp = await http_server_client.fetch('/services/gofer_nb/')
    assert resp.code == 200
    http_server_client.close()

def test_write_grade(setup_db):
    db_conn, db_path = setup_db
    grade_info = ("WRITE_TEST", 88.0, "1", "lab99", "1111")
    gn.write_grade(grade_info, db_path)

    cur = db_conn.cursor()
    cur.execute("SELECT * FROM GRADES;")
    data = cur.fetchall()
    assert "WRITE_TEST" in data[1]
    assert "1" in data[1]
    assert 88.0 in data[1]
    assert "lab99" in data[1]
    assert "1111" in data[1]


