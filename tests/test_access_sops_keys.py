import otter_service.access_sops_keys as ask
import pytest
import os


@pytest.fixture
def setup():
    os.environ["LTI_CONSUMER_KEY"] = "TEST_ENV_KEY"
    yield
    if 'LTI_CONSUMER_KEY' in os.environ:
        del os.environ['LTI_CONSUMER_KEY']


def test_get_sops():
    secrets_path = os.path.join(os.path.dirname(__file__), "test_files/test_key.yaml")
    sops_path = "sops"
    key = ask.get_via_sops(None, "LTI_CONSUMER_KEY", sops_path=sops_path, secrets_file=secrets_path)
    assert "test_lti_key" in key


def test_get_via_env(setup):
    key = ask.get_via_env(None, "LTI_CONSUMER_KEY")
    assert "TEST_ENV_KEY" in key


def test_get(setup):
    key = ask.get(None, "LTI_CONSUMER_KEY")
    assert "TEST_ENV_KEY" in key
    del os.environ['LTI_CONSUMER_KEY']
    try:
        key = ask.get("LTI_CONSUMER_KEY")  # this should raise Exception
        assert False
    except Exception:
        assert True
