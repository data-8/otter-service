import asyncio
import async_timeout
import requests
import tarfile
import os
from otter_service import access_sops_keys
import shutil


def download_autograder_materials(url, save_path=None):
    """
    This function downloads the appropriate archive of autograder materials be used for testing

    :param url: the url to the archive of materials
    :param save_path: Where to save the archive -- for testing it is "." for normal it will /tmp
    """
    download_path = "/tmp/materials.tar.gz"
    if save_path is None:
        save_path = "."
        download_path = "./materials.tar.gz"
    r = requests.get(url, stream=True)
    if r.status_code == 200:
        with open(download_path, 'wb') as f:
            f.write(r.raw.read())
    file = tarfile.open(download_path)
    file.extractall(save_path)
    file.close()
    url_parts = url.split("/")
    branch = url_parts[-1].split(".")[0]
    file_name = os.environ["AUTOGRADER_REPO"]
    extracted_path = f"{save_path}/{file_name}-{branch}"
    storage_path = f"{save_path}/{file_name}"
    if os.path.isdir(storage_path):
        shutil.rmtree(storage_path)
    os.rename(extracted_path, storage_path)
    os.remove(download_path)
    return storage_path


async def grade_assignment(submission, sec='3', assignment='lab01', solutions_path=None, sops_path=None, secrets_file=None, save_path=None):
    """
    This function spins up a docker instance using otter, grades the submission
    and returns the grade

    :param submission: the path to the file you want to grade
    :param sec: the course section; it is used to determine the path to the solution file
    :param assignment: the name of the assignment; it is used to determine the path to the solution file
    :param solutions_path: [OPTIONAL] used to execute pytests
    :param sops_path: [OPTIONAL] used to execute pytests
    :param secrets_file: [OPTIONAL] used to execute pytests
    :param save_path: [OPTIONAL] used to execute pytests
    :return: grade
    :rtype: float
    """
    try:
        solutions_base_path = None
        if save_path is None:
            save_path = "/opt"
        if secrets_file is None:
            secrets_file = os.path.join(os.path.dirname(__file__), "secrets/gh_key.yaml")
        git_access_token = access_sops_keys.get("github_access_token", sops_path=sops_path, secrets_file=secrets_file)
        materials_url = os.environ["AUTOGRADER_MATERIALS_URL"]
        materials_url = f"https://{git_access_token}:@{materials_url}"
        autograder_materials_subpath = os.environ["AUTOGRADER_MATERIALS_SUBPATH"]
        solutions_base_path = download_autograder_materials(materials_url, save_path=save_path)
        assign_type = "lab"
        if "hw" in assignment:
            assign_type = "hw"
        if solutions_path is None:
            solutions_path = '{solutions_base_path}/{autograder_materials_subpath}/{assign_type}/{sec}/{assignment}/autograder.zip'
        zip_path = solutions_path.format(solutions_base_path=solutions_base_path,
                                         autograder_materials_subpath=autograder_materials_subpath,
                                         assign_type=assign_type,
                                         sec=sec,
                                         assignment=assignment)
        # command = [
        #     'otter', 'grade',
        #     '-a',
        #     zip_path, '-p',
        #     submission
        # ]
        command = [
            'otter', 'run',
            '-a',
            zip_path,
            submission
        ]
        process = await asyncio.create_subprocess_exec(
            *command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        async with async_timeout.timeout(600):
            stdout, stderr = await process.communicate()

        for line in stderr.decode('utf-8').split('\n'):
            if line.strip() == '':
                # Ignore empty lines
                continue
            if 'Killed' in line:
                # Our container was killed, so let's just skip this one
                raise Exception(f"Container was killed -- nothing will work: {submission}")
        # grade = stdout.decode("utf-8").strip()
        # if grade is None or grade == '':
        #     cmd = ' '.join(command)
        #     raise Exception(f"Unable to determine grade coming from otter on: {submission} using this commnad: {cmd}")
        lines = stdout.decode("utf-8").strip().split("\n")
        grade = None
        for line in lines:
            if "Total Score" in line:
                grade = line.split(" ")[5][1:-2]
        if grade is None:
            raise Exception(f"Unable to determine grade coming from otter on: {submission}")
        return float(grade) / 100
    except asyncio.TimeoutError:
        raise Exception(f'Grading timed out for {submission}')
    except Exception as e:
        raise e
