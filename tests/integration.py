import json
import requests


def submit_test():
    # I use this file to test from the shell
    with open("tests/test_files/lab01.ipynb", 'r', encoding="utf-8") as myfile:
        data = myfile.read()

    data = json.loads(data)
    js = {'nb': data}
    #  response = requests.post('http://grading.data8x.berkeley.edu:10101/services/gofer_nb/', data=json.dumps(js))
    #  response = requests.post('https://hubv2-staging.data8x.berkeley.edu/services/gofer_nb/', data=json.dumps(js))
    for x in range(1):
        response = requests.post('http://localhost:10101/services/gofer_nb/', data=json.dumps(js))
        #  response = requests.post('http://grading.data8x.berkeley.edu:10101/services/gofer_nb/', data=json.dumps(js))
        #  response = requests.post('https://hubv2-staging.data8x.berkeley.edu/services/gofer_nb/', data=json.dumps(js))
        print(response)


submit_test()
