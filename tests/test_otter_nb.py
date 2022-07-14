import pytest
import os
import shutil
import otter_service.otter_nb as gn
from firebase_admin import firestore


@pytest.fixture
def app():
    return gn.start_server()


@pytest.mark.skip(reason="test oauth2 now")
async def test_http_client(http_server_client):
    resp = await http_server_client.fetch('/services/gofer_nb/')
    assert resp.code == 302
    http_server_client.close()


def test_write_grade():
    grade_info = {"userid": "WRITE_TEST", "course":"8x-test", "grade": 88.0, "section": "1", "assignment": "lab99"}
    doc = gn.write_grade(grade_info)[1]
    db = firestore.client()
    doc_ref = db.collection(f'{os.environ.get("ENVIRONMENT")}-grades').document(f'{doc.id}')
    doc_obj = doc_ref.get()
    doc_dict = doc_obj.to_dict()

    assert "WRITE_TEST" == doc_dict["user"]
    assert "1" == doc_dict["section"]
    assert 88.0 == doc_dict["grade"]
    assert "lab99" == doc_dict["assignment"]

    db.collection(f'{os.environ.get("ENVIRONMENT")}-grades').document(f'{doc.id}').delete()


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
