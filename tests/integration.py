import json
import requests
import sys

JUPYTERHUB_SERVICE_PREFIX = "/services/otter_grade/"
server_map = {
    "local": f"http://localhost:10101{JUPYTERHUB_SERVICE_PREFIX}",
    "staging-lb": f"http://35.193.0.244:10101{JUPYTERHUB_SERVICE_PREFIX}",
    "dev-lb": f"http://34.134.165.169:10101{JUPYTERHUB_SERVICE_PREFIX}",
    "prod-lb": f"http://35.224.71.117:10101{JUPYTERHUB_SERVICE_PREFIX}",
    "staging-dns": f"http://grader-staging.data8x.berkeley.edu:10101{JUPYTERHUB_SERVICE_PREFIX}",
    "prod-dns": f"http://grader-prod.data8x.berkeley.edu:10101{JUPYTERHUB_SERVICE_PREFIX}",
    "dev-dns": f"http://grader-dev.data8x.berkeley.edu:10101{JUPYTERHUB_SERVICE_PREFIX}",
    "staging-hub": f"https://hubv2-staging.data8x.berkeley.edu{JUPYTERHUB_SERVICE_PREFIX}",
    "prod-hub": f"https://hubv2.data8x.berkeley.edu{JUPYTERHUB_SERVICE_PREFIX}"
}


def submit_test(map_item):
    # I use this file to test from the shell
    with open("tests/test_files/lab01.ipynb", 'r', encoding="utf-8") as myfile:
        data = myfile.read()

    data = json.loads(data)
    js = {'nb': data}
    for x in range(1):
        response = requests.post(server_map[map_item], data=json.dumps(js))
        print(response)


if sys.argv[1] == "keys":
    print(*list(server_map.keys()), sep="\n - ")
else:
    submit_test(sys.argv[1])
