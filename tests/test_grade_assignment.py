import pytest
import otter_service.grade_assignment as ga
import os


@pytest.mark.asyncio
@pytest.mark.skip(reason="waiting for otter-grader new release")
async def test_some_asyncio_code():
    solutions_path = 'tests/test_files/lab01-autograder.zip'
    grade = await ga.grade_assignment("tests/test_files/lab01.ipynb", "1", "lab01", solutions_path=solutions_path)
    assert "1.0" == grade
