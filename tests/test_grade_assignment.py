import pytest
import otter_service.grade_assignment as ga
import os
import shutil


@pytest.fixture()
def configure():
    print("Starting tests")
    yield "resource"
    print("Removing Tree")
    if os.path.isdir("./materials-x22-private"):
        shutil.rmtree("./materials-x22-private")


def test_download_autograder_materials(configure):
    key_test = "tests/test_files/gh_key.yaml"
    sops_path = "sops"
    ga.download_autograder_materials("8x", sops_path, key_test)
    assert os.path.isdir("./materials-x22-private")


@pytest.mark.asyncio
async def test_grade_assignment(configure):
    secrets_file = os.path.join(os.path.dirname(__file__), "test_files/gh_key.yaml")
    args = {
        "course": "8x",
        "section": "1",
        "assignment": "lab01",
        "autograder_materials_repo": "github.com/data-8/materials-x22-private"
    }
    grade, _ = await ga.grade_assignment("tests/test_files/lab01.ipynb",
                                         args,
                                         sops_path="sops",
                                         secrets_file=secrets_file,
                                         save_path=".")
    assert 1.0 == grade
