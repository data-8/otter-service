import otter_service.dump_grades as dg
import pytest
from helper import make_db, create_connection
import os


@pytest.fixture
def setup():
    os.environ["VOLUME_PATH"] = "tests/test_files"
    db_path = os.environ["VOLUME_PATH"] + "/gradebook.db"
    make_db(db_path)
    conn = create_connection(db_path)
    yield conn
    conn.close()
    os.remove(db_path)
    os.remove(os.getenv("VOLUME_PATH") + '/grades.csv')
    del os.environ["VOLUME_PATH"]


def test_main(setup):
    dg.main()
    assert os.path.exists(os.getenv("VOLUME_PATH") + '/grades.csv')

    with open(os.getenv("VOLUME_PATH") + '/grades.csv', 'r') as f:
        lines = f.readlines()
    assert "TEST_USER" in lines[1]
