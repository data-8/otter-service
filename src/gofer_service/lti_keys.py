from google.cloud import secretmanager
import os


def get(key_name) -> str:
    """
    This method first check the Google Secrets Manager for the key and then tries the
    environment. it will return None if the key is not found

    :param key_name: the name of the key to retrieve from the Secrets or the environment
    :return: the secret
    """
    secret = get_via_gcp_secrets(key_name)
    if secret is None:
        secret = get_via_env(key_name)
    if secret is None:
        raise Exception(f"LTI key not configured: {key_name}; Grade NOT posted to LTI server; please configure")
    return secret


def get_via_gcp_secrets(key):
    """
    This function look in Google Secrets Manager for the key.

    :param key: the key to find in Google Secrets Manager
    :return: the value of the key or None
    """
    # Create the Secret Manager client.
    client = secretmanager.SecretManagerServiceClient()
    project_id = os.getenv("GCP_PROJECT_ID")
    # Build the resource name of the secret version.
    name = f"projects/{project_id}/secrets/{key}/versions/latest"

    # Access the secret version.
    try:
        response = client.access_secret_version(request={"name": name})

        payload = response.payload.data.decode("UTF-8")
        return payload
    except:
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