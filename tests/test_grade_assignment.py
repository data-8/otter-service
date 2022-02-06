import pytest
import gofer_service.grade_assignment as ga
import os


@pytest.mark.asyncio
async def test_some_asyncio_code():
    solutions_path = 'test_files/lab01-autograder.zip'
    grade = await ga.grade_assignment("test_files/lab01.ipynb", "1", "lab01", solutions_path=solutions_path)
    assert 0.75 == grade
