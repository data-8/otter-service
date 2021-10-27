from google.cloud import secretmanager
import os
import subprocess
import yaml

def get(key_name, secrets_file_path=None) -> str:
    """
    This method first tries to decrypt sops file and then tries the
    environment. it will return an Exception if the key is not found

    :param key_name: the name of the key to retrieve from the Secrets or the environment
    :return: the secret
    """
    secret = None
    if secrets_file_path is not None:
        secret = get_via_sops(key_name, secrets_file_path)
    if secret is None:
        secret = get_via_env(key_name)
    if secret is None:
        raise Exception(f"LTI key not configured: {key_name}; Grade NOT posted to LTI server; please configure")
    return secret


def get_via_sops(key, secrets_file_path):
    """
    This function attempts to use sops to decrpyt the secrets/gke_key.yaml

    :param key: the key to find in Google Secrets Manager
    :return: the value of the key or None
    """
    try:
        sops_output = subprocess.check_output(['sops', "-d", "secrets/gke_key.yaml"])
        dct = yaml.safe_load(sops_output)
        return dct[key.lower()]
    except Exception as e:
        return None

def get_via_env(key):
    """
    This checks the environment for the key.

    :param key: the key to find in the environment
    :return: the value of the key or None
    """
    if key in os.environ:
        return os.environ[key]
    return None
