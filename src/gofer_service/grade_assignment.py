import asyncio
import os
import async_timeout



async def grade_assignment(submission, sec='3', assignment='lab01'):
    """
    This function spins up a docker instance using otter, grades the submission
    and returns the grade

    :param submission: the path to the file you want to grade
    :param sec: the course section; it is used to determine the path to the solution file
    :param assignment: the name of the assignment; it is used to determine the path to the solution file
    :return: grade
    :rtype: float
    """
    try:
        assign_type = "lab"
        if "hw" in assignment:
            assign_type = "hw"
        p = '{wd}/materials-x19/otter-materials-grading/x19/{assign_type}/{sec}/{assignment}/autograder/autograder.zip'
        zip_path = p.format(wd=os.getcwd(), assign_type=assign_type, sec=sec, assignment=assignment)
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

        async with async_timeout.timeout(300):
            stdout, stderr = await process.communicate()

        for line in stderr.decode('utf-8').split('\n'):
            if line.strip() == '':
                # Ignore empty lines
                continue
            if 'Killed' in line:
                # Our container was killed, so let's just skip this one
                raise Exception(f"Container was killed -- nothing will work: {submission}")
            if "warning" not in line.lower():
                cmd = ' '.join(command)
                raise Exception("Found unrecognized output in stderr from {}, halting, line was {}".format(cmd, line))
        lines = stdout.decode("utf-8").strip().split("\n")
        grade = None
        for line in lines:
            if "Total Score" in line:
                score = line.split(" ")
                raw = float(score[2])
                total = float(score[4])
                grade = raw / total
        if grade is None:
            raise Exception(f"Unable to determine grade coming from otter on: {submission}")
        return grade
    except asyncio.TimeoutError:
        raise Exception(f'Grading timed out for {submission}')
    except Exception as e:
        raise e
