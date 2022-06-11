import asyncio
import async_timeout


async def grade_assignment(submission, sec='3', assignment='lab01', solutions_path=None):
    """
    This function spins up a docker instance using otter, grades the submission
    and returns the grade

    :param submission: the path to the file you want to grade
    :param sec: the course section; it is used to determine the path to the solution file
    :param assignment: the name of the assignment; it is used to determine the path to the solution file
    :param solutions_path: [OPTIONAL] used to execute pytests
    :return: grade
    :rtype: float
    """
    try:
        assign_type = "lab"
        if "hw" in assignment:
            assign_type = "hw"
        if solutions_path is None:
            solutions_path = '/opt/materials-x22-private/materials/x22/{assign_type}/{sec}/{assignment}/autograder.zip'
        zip_path = solutions_path.format(assign_type=assign_type, sec=sec, assignment=assignment)
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
