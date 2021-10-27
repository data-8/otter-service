import json
import requests
# so I can test from shell
from dotenv import load_dotenv
load_dotenv()


def submit_test():
    # I use this file to test from the shell
    with open("tests/test_files/hw01-SEAN.ipynb", 'r', encoding="utf-8") as myfile:
        data=myfile.read()

    data = json.loads(data)
    js = {'nb':data}
    #response = requests.post('http://grading.data8x.berkeley.edu:10101/services/gofer_nb/', data=json.dumps(js))
    response = requests.post('http://localhost:10101/services/gofer_nb/', data=json.dumps(js))
    print(response)

submit_test()