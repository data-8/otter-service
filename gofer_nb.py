import aiohttp
import asyncio
import async_timeout
import base64
import json
import os
import time
import sqlite3
import tornado.web
import tornado.httpserver
import tornado.ioloop
import tornado.escape
import tornado.options
from grade_assignment import grade_assignment
import logging
import traceback
import pandas as pd
from time import gmtime, strftime
from hashlib import sha1
from jupyterhub.services.auth import HubAuthenticated
from lxml import etree
from oauthlib.oauth1.rfc5849 import signature, parameters
from sqlite3 import Error

prefix = os.environ.get('JUPYTERHUB_SERVICE_PREFIX', '/')
ERROR_FILE = "tornado_errors.csv"
ERROR_PATH = "tornadoerrors"


def write_grade(grade_info, db_fname="gradebook.db"):
    sql_cmd = """INSERT INTO grades(userid, grade, section, lab, timestamp)
                 VALUES(?,?,?,?,?)"""
    try:
        conn = sqlite3.connect(db_fname)
        # context manager here takes care of conn.commit()
        with conn:
            conn.execute(sql_cmd, grade_info)
    except Error as e:
        print(e)
        print("Error inserting into database for the following record")
        print(grade_info)
    finally:
        conn.close()


class GradePostException(Exception):
    def __init__(self, response=None):
        self.response = response


async def post_grade(user_id, grade, sourcedid, outcomes_url):
    # TODO: extract this into a real library with real XML parsing
    # WARNING: You can use this only with data you trust! Beware, etc.
    post_xml = r"""
    <?xml version = "1.0" encoding = "UTF-8"?>
    <imsx_POXEnvelopeRequest xmlns = "http://www.imsglobal.org/services/ltiv1p1/xsd/imsoms_v1p0">
      <imsx_POXHeader>
        <imsx_POXRequestHeaderInfo>
          <imsx_version>V1.0</imsx_version>
          <imsx_messageIdentifier>999999123</imsx_messageIdentifier>
        </imsx_POXRequestHeaderInfo>
      </imsx_POXHeader>
      <imsx_POXBody>
        <replaceResultRequest>
          <resultRecord>
            <sourcedGUID>
              <sourcedId>{sourcedid}</sourcedId>
            </sourcedGUID>
            <result>
              <resultScore>
                <language>en</language>
                <textString>{grade}</textString>
              </resultScore>
            </result>
          </resultRecord>
        </replaceResultRequest>
      </imsx_POXBody>
    </imsx_POXEnvelopeRequest>
    """
    # Assumes these are read in from a config file in Jupyterhub
    consumer_key = os.environ['LTI_CONSUMER_KEY']
    consumer_secret = os.environ['LTI_CONSUMER_SECRET']
    sourcedid = "{}:{}".format(sourcedid, user_id)
    post_data = post_xml.format(grade=float(grade), sourcedid=sourcedid)

    # Yes, we do have to use sha1 :(
    body_hash_sha = sha1()
    body_hash_sha.update(post_data.encode('utf-8'))
    body_hash = base64.b64encode(body_hash_sha.digest()).decode('utf-8')
    args = {
        'oauth_body_hash': body_hash,
        'oauth_consumer_key': consumer_key,
        'oauth_timestamp': str(time.time()),
        'oauth_nonce': str(time.time())
    }

    base_string = signature.construct_base_string(
        'POST',
        signature.normalize_base_string_uri(outcomes_url),
        signature.normalize_parameters(
            signature.collect_parameters(body=args, headers={})
        )
    )

    oauth_signature = signature.sign_hmac_sha1(base_string, consumer_secret, None)
    args['oauth_signature'] = oauth_signature

    headers = parameters.prepare_headers(args, headers={
        'Content-Type': 'application/xml'
    })


    async with async_timeout.timeout(10):
        async with aiohttp.ClientSession() as session:
            async with session.post(outcomes_url, data=post_data, headers=headers) as response:
                resp_text = await response.text()

                if response.status != 200:
                    raise GradePostException(response)

    response_tree = etree.fromstring(resp_text.encode('utf-8'))

    # XML and its namespaces. UBOOF!
    status_tree = response_tree.find('.//{http://www.imsglobal.org/services/ltiv1p1/xsd/imsoms_v1p0}imsx_statusInfo')
    code_major = status_tree.find('{http://www.imsglobal.org/services/ltiv1p1/xsd/imsoms_v1p0}imsx_codeMajor').text

    if code_major != 'success':
        raise GradePostException(response)


class GoferHandler(HubAuthenticated, tornado.web.RequestHandler):

    async def get(self):
        self.write("This is a post only page. You probably shouldn't be here!")
        self.finish()

    async def post(self):
        """Accept notebook submissions, saves, then grades them"""
        user = self.get_current_user()
        req_data = tornado.escape.json_decode(self.request.body)
        # in the future, assignment should be metadata in notebook
        notebook = req_data['nb']
        section = notebook['metadata']['section']
        try:
            assignment = notebook['metadata']['assignment']
        except:
            assignment = notebook['metadata']['lab']

        try:
            course = notebook['metadata']['course']
        except:
            course = "8x"


        timestamp = str(time.time())
        # save notebook submission with user id and time stamp
        submission_file = "/home/vipasu/gofer_service/submissions/{}_{}_{}_{}.ipynb".format(user['name'], section, assignment, timestamp)
        with open(submission_file, 'w') as outfile:
            json.dump(notebook, outfile)

        # Let user know their submission was received
        self.write("User submission has been received. Grade will be posted to the gradebook once it's finished running!")
        self.finish()

        try:
            # Grade assignment
            grade = await grade_assignment(submission_file, section, assignment)

            # Write the grade to a sqlite database
            grade_info = (user['name'], grade, section, assignment, timestamp)
            write_grade(grade_info)
        except:
            logErrorCSV(timestamp, user['name'], section, assignment, traceback.format_exc())

        # post grade to EdX
        with open('/home/vipasu/x19_config.json', 'r') as fname:
            # Course DEPENDENT configuration file
            # Should contain page for hitting the gradebook (outcomes_url)
            # as well as resource IDs for assignments
            # e.g. sourcedid['3']['lab02'] = c09d043b662b4b4b96fceacb1f4aa1c9
            # Make sure that it's placed in the working directory of the service (pwdx <PID>)
            course_config = json.load(fname)

        try:
            await post_grade(user['name'], grade,
                            course_config[course]["sourcedid"][section][assignment],
                            course_config[course]["outcomes_url"][section][assignment])
        except GradePostException as e:
            logErrorCSV(timestamp, user['name'], section, assignment, str(e.response) + "\n" + traceback.format_exc())
        except:
            logErrorCSV(timestamp, user['name'], section, assignment, traceback.format_exc())

def logErrorCSV(timestamp, username, section, assignment, msg):
    try:
        df = pd.read_csv(ERROR_FILE)
    except:
        df = pd.DataFrame(columns=["timestamp", "username","section","assignment","error","filename"])

    ts = strftime("%a, %d %b %Y %H:%M:%S +0000", gmtime())
    filename = timestamp + "_" + str(username)
    trace = str(traceback.format_exc())
    error_msg = trace.rsplit('\n',2)[1]

    with open("{}/{}.txt".format(ERROR_PATH,filename), "w") as f:
        f.write(trace)

    df.loc[len(df.index)] = [ts,username,section,assignment, str(error_msg), filename]
    df.to_csv(ERROR_FILE, index=False)


class csvHandler(logging.FileHandler):
    def emit(self, record):
        logErrorCSV(str(time.time()), None, None, None, traceback.format_exc())



if __name__ == '__main__':
    tornado.options.parse_command_line()
    app = tornado.web.Application([(prefix, GoferHandler)])

    logger = logging.getLogger('tornado.application')
    logger.addHandler(csvHandler(ERROR_FILE))

    app.listen(10101)

    tornado.ioloop.IOLoop.current().start()
