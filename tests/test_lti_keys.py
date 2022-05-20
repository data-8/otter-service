import gofer_service.lti_keys as lti
import pytest
import os


@pytest.fixture
def setup():
    os.environ["LTI_CONSUMER_KEY"] = "TEST_ENV_KEY"
    yield
    if 'LTI_CONSUMER_KEY' in os.environ:
        del os.environ['LTI_CONSUMER_KEY']


def test_get_sops():
    secrets_path = os.path.join(os.path.dirname("."), "tests/test_files/gke_key.yaml")
    sops_path = "sops"
    key = lti.get_via_sops("LTI_CONSUMER_KEY", sops_path=sops_path, secrets_path=secrets_path)
    assert "test_lti_key" in key


def test_get_via_env(setup):
    key = lti.get_via_env("LTI_CONSUMER_KEY")
    assert "TEST_ENV_KEY" in key


def test_get(setup):
    key = lti.get("LTI_CONSUMER_KEY")
    assert "TEST_ENV_KEY" in key
    del os.environ['LTI_CONSUMER_KEY']
    try:
        key = lti.get("LTI_CONSUMER_KEY")  # this should raise Exception
        assert False
    except Exception:
        assert True
