import json
import requests
import sys

JUPYTERHUB_SERVICE_PREFIX = "/services/otter_grade/"
server_map = {
    "local": f"http://localhost:10101{JUPYTERHUB_SERVICE_PREFIX}",
    "staging-lb": f"http://35.193.0.244:10101{JUPYTERHUB_SERVICE_PREFIX}",
    "dev-lb": f"http://34.134.165.169:10101{JUPYTERHUB_SERVICE_PREFIX}",
    "prod-lb": f"http://35.224.71.117:10101{JUPYTERHUB_SERVICE_PREFIX}",
    "staging-dns": f"http://grader-srv-staging.datahub.berkeley.edu:10101{JUPYTERHUB_SERVICE_PREFIX}",
    "prod-dns": f"http://grader-srv.datahub.berkeley.edu:10101{JUPYTERHUB_SERVICE_PREFIX}",
    "dev-dns": f"http://grader-srv-dev.datahub.berkeley.edu:10101{JUPYTERHUB_SERVICE_PREFIX}",
    "staging-hub": f"https://edx-staging.datahub.berkeley.edu{JUPYTERHUB_SERVICE_PREFIX}",
    "prod-hub": f"https://edx.datahub.berkeley.edu{JUPYTERHUB_SERVICE_PREFIX}"
}


def submit_test(args):
    map_item = args[1]
    test = args[2]
    test_file = "lab01.ipynb"
    if test == "88e":
        test_file = "lab01-88e.ipynb"

    # I use this file to test from the shell
    with open(f"tests/test_files/{test_file}", 'r', encoding="utf-8") as myfile:
        data = myfile.read()

    data = json.loads(data)
    js = {'nb': data}
    response = requests.post(server_map[map_item], data=json.dumps(js))
    print(response)


# sample usage
# integration.py dev-lb 88e
# integration.py dev-lb 8x
if sys.argv[1] == "keys":
    print(*list(server_map.keys()), sep="\n - ")
else:
    submit_test(sys.argv)
