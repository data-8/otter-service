import json
import requests

server_map = {
    "local": "http://localhost:10101",
    "staging-lb": "http://34.134.82.125:10101",
    "dev-lb": "http://34.134.165.169:10101",
    "prod-lb": "http://34.70.18.176:10101",
    "stage-dns": "http://grader-staging.data8x.berkeley.edu:10101",
    "prod-dns": "http://grader-prod.data8x.berkeley.edu:10101",
    "dev-dns": "http://grader-dev.data8x.berkeley.edu:10101",
    "staging-hub": "https://hubv2-staging.data8x.berkeley.edu/services/gofer_nb/",
    "prod-hub": "https://hubv2.data8x.berkeley.edu/services/gofer_nb/"
}


def submit_test():
    # I use this file to test from the shell
    with open("tests/test_files/lab01.ipynb", 'r', encoding="utf-8") as myfile:
        data = myfile.read()

    data = json.loads(data)
    js = {'nb': data}
    for x in range(1):
        response = requests.post(server_map["dev-dns"], data=json.dumps(js))
        print(response)


submit_test()
