import json
import requests

server_map = {
    "local": "http://localhost:10101/services/gofer_nb/",
    "staging-lb": "http://34.134.82.125:10101/services/gofer_nb/",
    "dev-lb": "http://34.66.228.116:10101/services/gofer_nb/",
    "prod-lb": "http://34.70.18.176:10101/services/gofer_nb/",
    "stage-dns": "http://grader-staging.data8x.berkeley.edu:10101/services/gofer_nb/",
    "prod-dns": "http://grader-prod.data8x.berkeley.edu:10101/services/gofer_nb/",
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
        response = requests.post(server_map[""], data=json.dumps(js))
        print(response)


submit_test()
