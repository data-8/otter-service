import os
import subprocess
from pydantic import NoneBytes
import yaml


def get(key_name) -> str:
    """
    This method first tries to decrypt sops file and then tries the
    environment. it will return an Exception if the key is not found

    :param key_name: the name of the key to retrieve from the Secrets or the environment
    :return: the secret
    """
    try:
        secret = get_via_env(key_name)
        if secret is None:
            secret = get_via_sops(key_name)
        return secret
    except Exception as ex:
        raise Exception(f"LTI key not configured: {key_name}; Grade NOT posted to LTI server; please configure: Error: {ex}") from ex


def get_via_sops(key, sops_path=None, secrets_path=None):
    """
    This function attempts to use sops to decrpyt the secrets/gke_key.yaml

    :param key: the key to find in Google Secrets Manager
    :param sops_path: [OPTIONAL] used to execute pytests
    :param secrets_path: [OPTIONAL] used to execute pytests
    :return: the value of the key or None
    """
    try:
        if sops_path is None:
            sops_path = "/root/go/bin/sops"

        if secrets_path is None:
            secrets_path = os.path.join(os.path.dirname(__file__), "secrets/gke_key.yaml")

        sops_output = subprocess.check_output([sops_path, "-d", secrets_path], stderr=subprocess.STDOUT)
        dct = yaml.safe_load(sops_output)
        return dct[key]
    except Exception as ex:
        raise ex


def get_via_env(key):
    """
    This checks the environment for the key.

    :param key: the key to find in the environment
    :return: the value of the key or None
    """
    if key in os.environ:
        return os.environ[key]
    return None
