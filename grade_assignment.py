import asyncio
import async_timeout


async def grade_assignment(submission, section='3', assignment='lab01'):
    if "hw" in assignment:
        assignment_container_path_template = '/srv/repo/materials/x19/hw/{section}/{assignment}/{assignment}.ipynb'
    else:
        assignment_container_path_template = '/srv/repo/materials/x19/lab/{section}/{assignment}/{assignment}.ipynb'
    grader_image = 'gofer'
    command = [
            'docker', 'run',
            '--rm',
            '-m', '2G',
            '-i',
            '--net=none',
            grader_image,
            "/srv/repo/grading/containergrade.bash",
            assignment_container_path_template.format(section=section, assignment=assignment)
        ]
    process = await asyncio.create_subprocess_exec(
            *command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
    with open(submission) as f:

        content = f.read().encode('utf-8')
        print(content)
        try:
            async with async_timeout.timeout(300):
                stdout, stderr = await process.communicate(content)
        except asyncio.TimeoutError:
            print(f'Grading timed out for {submission}')
            return False

        for line in stderr.decode('utf-8').split('\n'):
            if line.strip() == '':
                # Ignore empty lines
                continue
            if 'Killed' in line:
                # Our container was killed, so let's just skip this one
                return False
            if  "warning" not in line.lower():
                print(line)
                raise Exception("Found unrecognized output in stderr from {}, halting, line was {}".format(' '.join(command), line))
    lines = stdout.decode("utf-8").strip().split("\n")
    # print(lines)
    grade = float(lines[-1])
    return grade


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    task = loop.create_task(grade_assignment())
    loop.run_until_complete(task)
