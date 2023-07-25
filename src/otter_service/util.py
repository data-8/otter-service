import json


def get_course_config(solution_base_path):
    with open(f'{solution_base_path}/course-config.json', 'r', encoding="utf8") as filename:
        # Course DEPENDENT configuration file
        # Should contain page for hitting the gradebook (outcomes_url)
        # as well as resource IDs for assignments
        # e.g. sourcedid['3']['lab02'] = c09d043b662b4b4b96fceacb1f4aa1c9
        # Make sure that it's placed in the working directory of the service (pwdx <PID>)
        return json.load(filename)
