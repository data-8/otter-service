import asyncio
import async_timeout
import jwt
import requests
import tarfile
import time
import os
import glob
from otter_service import access_sops_keys
import shutil
import otter_service.util as util


def get_github_app_token(app_id, private_key_pem, installation_id):
    """
    Exchange GitHub App credentials for a short-lived installation access token.
    """
    now = int(time.time())
    payload = {
        "iat": now - 60,
        "exp": now + 600,
        "iss": str(app_id),
    }
    encoded_jwt = jwt.encode(payload, private_key_pem, algorithm="RS256")
    resp = requests.post(
        f"https://api.github.com/app/installations/{installation_id}/access_tokens",
        headers={
            "Authorization": f"Bearer {encoded_jwt}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
    )
    resp.raise_for_status()
    return resp.json()["token"]


def download_autograder_materials(course, sops_path, secrets_file, save_path=None):
    """
    This function downloads the appropriate archive of autograder materials be used for testing. The archive
    must be on the main branch(but it will also try the master branch if main fails)

    :param course: key to autograder_repo in secrets file
    :param sops_path: path to sops executable
    :param secrets_file: path to secrets file
    :param save_path: Where to save the archive -- for testing it is "." for normal it will /tmp
    """
    branch = "main"
    app_id = access_sops_keys.get(None, "github_app_id", sops_path=sops_path, secrets_file=secrets_file)
    private_key = access_sops_keys.get(None, "github_app_private_key", sops_path=sops_path, secrets_file=secrets_file)
    installation_id = access_sops_keys.get(None, "github_app_installation_id", sops_path=sops_path, secrets_file=secrets_file)
    git_access_token = get_github_app_token(app_id, private_key, installation_id)
    autograder_materials_repo = access_sops_keys.get(course, "autograder_repo", sops_path=sops_path, secrets_file=secrets_file)
    materials_url = f"https://x-access-token:{git_access_token}@{autograder_materials_repo}/archive/{branch}.tar.gz"

    download_path = "/tmp/materials.tar.gz"
    if save_path is None:
        save_path = "."
        download_path = "./materials.tar.gz"
    r = requests.get(materials_url, stream=True)
    if r.status_code != 200:
        branch = "master"
        materials_url = f"https://x-access-token:{git_access_token}@{autograder_materials_repo}/archive/{branch}.tar.gz"
        r = requests.get(materials_url, stream=True)

    if r.status_code == 200:
        with open(download_path, 'wb') as f:
            f.write(r.raw.read())
        file = tarfile.open(download_path)
        file.extractall(save_path)
        file.close()
        url_parts = materials_url.split("/")
        branch = url_parts[-1].split(".")[0]
        file_name = autograder_materials_repo.split("/")[-1]
        extracted_path = f"{save_path}/{file_name}-{branch}"
        storage_path = f"{save_path}/{file_name}"
        if os.path.isdir(storage_path):
            shutil.rmtree(storage_path)
        os.rename(extracted_path, storage_path)
        os.remove(download_path)
    else:
        raise Exception(f"Unable to access: {autograder_materials_repo}")
    return storage_path


def remove_notebook(submission):
    files = glob.glob(f'{submission}')
    for f in files:
        if not os.path.isdir(f):
            try:
                os.remove(f)
            except Exception:
                pass


async def grade_assignment(submission,
                           args,
                           sops_path=None, secrets_file=None, save_path=None):
    """
    This function spins up a docker instance using otter, grades the submission
    and returns the grade

    :param submission: the path to the file you want to grade
    :param args: json containing metadata from notebook
        - course: used as key to secrets file and course config
        - section: key to course config
        - assignment: key to assignment name
    :param sops_path: [OPTIONAL] used to execute pytests
    :param secrets_file: [OPTIONAL] used to execute pytests
    :param save_path: [OPTIONAL] used to execute pytests
    :return: grade, solutions_base_path
    :rtype: float, string
    """
    try:
        solutions_base_path = None
        if save_path is None:
            save_path = "/opt"
        if secrets_file is None:
            secrets_file = os.path.join(os.path.dirname(__file__), "secrets/gh_key.yaml")
        solutions_base_path = download_autograder_materials(args["course"], sops_path, secrets_file, save_path=save_path)

        course_config = util.get_course_config(solutions_base_path)

        autograder_subpath = course_config[args["course"]][args["section"]]["subpath_to_zips"]

        solutions_path = f'{solutions_base_path}/{autograder_subpath}/{args["assignment"]}-autograder.zip'
        command = [
            'otter', 'grade',
            '-n', f'{args["course"]}.{args["section"]}.{args["assignment"]}',
            '-a', solutions_path,
            submission
        ]
        process = await asyncio.create_subprocess_exec(
            *command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        # this is waiting for communication back from the process
        # some images are quite big and take some time to build the first
        # time through - like 20 min for otter-grader
        async with async_timeout.timeout(2000):
            stdout, stderr = await process.communicate()

        for line in stderr.decode('utf-8').split('\n'):
            if line.strip() == '':
                # Ignore empty lines
                continue
            if 'Killed' in line:
                # Our container was killed, so let's just skip this one
                raise Exception(f"Container was killed -- nothing will work: {submission}")

        grade = stdout.decode("utf-8").strip()
        if grade is None or grade == '':
            cmd = ' '.join(command)
            raise Exception(f"Unable to determine grade coming from otter on: {submission} using this commnad: {cmd}")

        return round(float(grade), 3), solutions_base_path
    except asyncio.TimeoutError:
        raise Exception(f'Grading timed out for {submission}')
    except Exception as e:
        raise e
    finally:
        remove_notebook(submission)
