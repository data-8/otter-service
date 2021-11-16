import pytest
import gofer_service.grade_assignment as ga
import os


@pytest.fixture(scope="function")
def change_test_dir(request):
    # change working dir for this test to get materials-x19(which need to be in parent dir)
    os.chdir(os.path.dirname(os.getcwd()))
    yield
    os.chdir(request.config.invocation_dir)

@pytest.mark.asyncio
async def test_some_asyncio_code(change_test_dir):
    grade = await ga.grade_assignment("gofer_service/tests/test_files/hw01-SEAN.ipynb", "1", "lab01")
    assert 0.14285714285714285 == grade
