import os
import subprocess
from pydantic import NoneBytes
import yaml


def get(key_name, sops_path=None, secrets_file=None) -> str:
    """
    This method first tries to decrypt sops file and then tries the
    environment. it will return an Exception if the key is not found

    :param key_name: the name of the key to retrieve from the Secrets or the environment
    :param secrets_file: the name of the secrets file associated with the key
    :return: the secret
    """
    try:
        secret = get_via_env(key_name)
        if secret is None:
            secret = get_via_sops(key_name, sops_path=sops_path, secrets_file=secrets_file)
        return secret
    except Exception as ex:
        raise Exception(f"Key not decrypted: {key_name}; please configure: Error: {ex}") from ex


def get_via_sops(key, sops_path=None, secrets_file=None):
    """
    This function attempts to use sops to decrpyt the secrets/{secrets_file}

    :param key: the key to find in Google Secrets Manager
    :param sops_path: [OPTIONAL] used to execute pytests
    :param secrets_file: [OPTIONAL] used to execute pytests
    :return: the value of the key or None
    """
    try:
        if sops_path is None:
            sops_path = "/root/go/bin/sops"

        secrets_file = secrets_file

        sops_output = subprocess.check_output([sops_path, "-d", secrets_file], stderr=subprocess.STDOUT)
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
