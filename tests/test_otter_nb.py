import pytest
import os
import shutil
import otter_service.otter_nb as gn
from helper import make_db, create_connection


@pytest.fixture
def app():
    os.environ["VOLUME_PATH"] = "/tmp/otter"
    error_file = os.environ["SERVER_LOG_FILE"]
    os.makedirs(os.environ["VOLUME_PATH"], exist_ok=True)
    gn.ERROR_FILE = os.environ["VOLUME_PATH"] + f"/{error_file}"
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
    os.remove(gn.ERROR_FILE)
    shutil.rmtree(os.environ["VOLUME_PATH"])
    os.makedirs(os.environ["VOLUME_PATH"])
    del os.environ["VOLUME_PATH"]


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


def test_create_post_url():
    os.environ['EDX_URL'] = "edge.edx.org"
    url = gn.create_post_url("BerkeleyX+Data8.1x+2021", "6333e19d6b4d46f88df671ba50f616d8")
    assert "BerkeleyX+Data8.1x+2021/xblock/block-v1:BerkeleyX+Data8.1x+2021+type@lti_consumer+block@6333e19d6b4d46f88df671ba50f616d8" in url
    del os.environ['EDX_URL']


def test_create_sourced_id():
    os.environ['EDX_URL'] = "edge.edx.org"
    url = gn.create_sourced_id("BerkeleyX+Data8.1x+2021", "6333e19d6b4d46f88df671ba50f616d8")
    assert url == "course-v1%3ABerkeleyX+Data8.1x+2021:edge.edx.org-6333e19d6b4d46f88df671ba50f616d8"
    del os.environ['EDX_URL']
