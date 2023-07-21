import pytest
import otter_service.access_sops_keys as ask
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
    git_access_token = ask.get_via_sops("github_access_token", sops_path=sops_path, secrets_file=key_test)
    materials_url = f"https://{git_access_token}:@github.com/data-8/materials-x22-private/archive/main.tar.gz"
    ga.download_autograder_materials(materials_url)
    assert os.path.isdir("./materials-x22-private")


@pytest.mark.asyncio
async def test_grade_assignment(configure):
    solutions_path = 'tests/test_files/autograder.zip'
    secrets_file = os.path.join(os.path.dirname(__file__), "test_files/gh_key.yaml")
    grade = await ga.grade_assignment("tests/test_files/lab01.ipynb",
                                      "1",
                                      "lab01",
                                      solutions_path=solutions_path,
                                      sops_path="sops",
                                      secrets_file=secrets_file,
                                      save_path=".")
    assert 1.0 == grade
