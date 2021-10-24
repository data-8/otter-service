import aiohttp
import async_timeout
import base64
import json
import time
import sqlite3
import tornado.web
import tornado.httpserver
import tornado.ioloop
import tornado.escape
import tornado.options
from gofer_service.grade_assignment import grade_assignment
import gofer_service.create_database as create_database
import logging
import traceback
import pandas as pd
from time import gmtime, strftime
from hashlib import sha1
from jupyterhub.services.auth import HubAuthenticated
from lxml import etree
from oauthlib.oauth1.rfc5849 import signature, parameters
from sqlite3 import Error
import os
import gofer_service.lti_keys as lti_keys

prefix = os.environ.get('JUPYTERHUB_SERVICE_PREFIX', '/')
VOLUME_PATH = os.getenv("VOLUME_PATH")
ERROR_FILE = f"{VOLUME_PATH}/" + os.getenv("ERROR_FILE")
ERROR_PATH = f"{VOLUME_PATH}/" + os.getenv("ERROR_PATH")
SUBMISSIONS_PATH = f"{VOLUME_PATH}/" + os.getenv("SUBMISSIONS_PATH")
DB_PATH = f"{VOLUME_PATH}/" + os.getenv("DB_PATH")


def write_grade(grade_info, db_filename):
    """
    write the grade to the database

    :param grade_info: the four values in a tuple(userid, grade, section, lab, timestamp)
    :param db_filename: the filename(path) the sqlite3 db
    """
    conn = None
    sql_cmd = """INSERT INTO grades(userid, grade, section, lab, timestamp)
                 VALUES(?,?,?,?,?)"""
    try:
        conn = sqlite3.connect(db_filename)
        # context manager here takes care of conn.commit()
        with conn:
            conn.execute(sql_cmd, grade_info)
    except Error:
        raise Exception(f"Error inserting into database for the following record: {grade_info}")
    finally:
        if conn is not None:
            conn.close()


class GradePostException(Exception):
    """
    custom Exception to throw for problems when you post grade
    """
    def __init__(self, response=None):
        self.response = response


class GradeSubmissionException(Exception):
    """
    custom Exception to throw for problems with the submission itself
    """
    def __init__(self, response=None):
        self.response = response


async def post_grade(user_id, grade, sourcedid, outcomes_url):
    """
    This posts the grade to the LTI server
    :param user_id: the user to post the grade for
    :param grade: the grade as a float
    :param sourcedid: source id for the record
    :param outcomes_url: the url that the lti server accepts for this assignment
    :return:
    """
    # TODO: extract this into a real library with real XML parsing
    # WARNING: You can use this only with data you trust! Beware, etc.
    try:
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
        consumer_key = lti_keys.get("LTI_CONSUMER_KEY")
        consumer_secret = lti_keys.get("LTI_CONSUMER_SECRET")

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

        if os.getenv("POST_GRADE").lower() in ("true", '1', 't'):
            print("SHOULD NOT BE HERE")
            async with async_timeout.timeout(10):
                async with aiohttp.ClientSession() as session:
                    async with session.post(outcomes_url, data=post_data, headers=headers) as response:
                        resp_text = await response.text()

                        if response.status != 200:
                            raise GradePostException(response)

            response_tree = etree.fromstring(resp_text.encode('utf-8'))

            # XML and its namespaces. UBOOF!
            status = response_tree.find('.//{http://www.imsglobal.org/services/ltiv1p1/xsd/imsoms_v1p0}imsx_statusInfo')
            code_major = status.find('{http://www.imsglobal.org/services/ltiv1p1/xsd/imsoms_v1p0}imsx_codeMajor').text

            if code_major != 'success':
                raise GradePostException(response)
        else:
            raise GradePostException("NOT POSTING Grades on purpose; see .env -- POST_GRADE")

    except GradePostException as g:
        raise GradePostException(g)
    except Exception as e:
        raise Exception(f"Problem Posting Grade to LTI:{e}")


class GoferHandler(HubAuthenticated, tornado.web.RequestHandler):
    async def data_received(self, chunk):
        """
        abstract methods empty
        :param chunk:
        :return:
        """
        pass

    async def get(self):
        self.write("This is a post only page. You probably shouldn't be here!")

    async def post(self):
        notebook = None
        section = None
        assignment = None
        user = None
        course = "8x"
        timestamp = str(time.time())
        try:
            # Accept notebook submissions, saves, then grades them
            user = self.get_current_user()
            if user is None:
                user = {"name": "TEST_USER"}

            req_data = tornado.escape.json_decode(self.request.body)
            # in the future, assignment should be metadata in notebook
            if 'nb' in req_data:
                notebook = req_data['nb']

            if "section" in notebook['metadata']:
                section = notebook['metadata']['section']

            if "assignment" in notebook['metadata']:
                assignment = notebook['metadata']['assignment']
            elif "lab" in notebook['metadata']:
                assignment = notebook['metadata']['lab']

            if "course" in notebook['metadata']:
                course = notebook['metadata']['course']

            if notebook is None or section is None or assignment is None:
                raise GradeSubmissionException("Notebook does not have required metadata or maybe no notebook in post")

            # save notebook submission with user id and time stamp
            submission_file = f"{VOLUME_PATH}/submissions/{user['name']}_{section}_{assignment}_{timestamp}.ipynb"
            with open(submission_file, 'w') as outfile:
                json.dump(notebook, outfile)

            # Let user know their submission was received
            self.write("User submission received. Grade will be posted to the gradebook once it's finished running!")
            self.finish()

            # Grade assignment
            grade = await grade_assignment(submission_file, section, assignment)

            # Write the grade to a sqlite database
            grade_info = (user['name'], grade, section, assignment, timestamp)
            db_path = f"{VOLUME_PATH}/gradebook.db"
            write_grade(grade_info, db_path)

            # post grade to EdX
            with open('{}/materials-x19/x19_config.json'.format(os.getcwd()), 'r') as filename:
                # Course DEPENDENT configuration file
                # Should contain page for hitting the gradebook (outcomes_url)
                # as well as resource IDs for assignments
                # e.g. sourcedid['3']['lab02'] = c09d043b662b4b4b96fceacb1f4aa1c9
                # Make sure that it's placed in the working directory of the service (pwdx <PID>)
                course_config = json.load(filename)

            await post_grade(user['name'], grade,
                            course_config[course]["sourcedid"][section][assignment],
                            course_config[course]["outcomes_url"][section][assignment])
        except GradePostException as p:
            log_error_csv(timestamp, user['name'], section, assignment, str(p.response) + "\n" + traceback.format_exc())
        except GradeSubmissionException as g:
            if notebook is None:
                section = "No notebook was in the request body"
                assignment = "No notebook was in the request body"
            else:
                if section is None:
                    section = "Section: problem getting section - not in notebook?"
                if assignment is None:
                    assignment = "Assignment: problem getting assignment - not in notebook?"

            log_error_csv(timestamp, user['name'], section, assignment, str(g.response) + "\n" + traceback.format_exc())
        except Exception as e:
            log_error_csv(timestamp, user['name'], section, assignment, str(e) + "\n" + traceback.format_exc())


def log_error_csv(timestamp, username, section, assignment, msg):
    """
    This logs the errors occurring when posting assignments

    :param timestamp: when the error occurred
    :param username: the username
    :param section: the section
    :param assignment: the assignment
    :param msg: optional message to logs
    """
    try:
        df = pd.read_csv(ERROR_FILE)
    except:
        df = pd.DataFrame(columns=["timestamp", "username", "section", "assignment", "error", "filename"])

    ts = strftime("%a, %d %b %Y %H:%M:%S +0000", gmtime())
    filename = timestamp + "_" + str(username)
    trace = f"User: {username}\nSection: {section}\nAssignment: {assignment}\n\n"
    trace += str(traceback.format_exc()) + "\n"
    trace += msg + "\n"
    error_msg = trace.rsplit('\n', 2)[1]

    with open("{}/{}.txt".format(ERROR_PATH, filename), "a+") as f:
        f.write(trace)

    df.loc[len(df.index)] = [ts, username, section, assignment, str(error_msg), filename]
    df.to_csv(ERROR_FILE, index=False)


class CsvHandler(logging.FileHandler):
    """
    this handles the logging any error to CSV file for quick reference
    """
    def emit(self, record):
        log_error_csv(str(time.time()), None, None, None, traceback.format_exc())


def start_server():
    """
    start the tornado server listening on port 10101 - I seperated this function from the main()
    in order to make testing easier
    :return: the application tornado object
    """
    tornado.options.parse_command_line()
    app = tornado.web.Application([(prefix, GoferHandler)])

    logger = logging.getLogger('tornado.application')
    logger.addHandler(CsvHandler(ERROR_FILE))
    app.listen(10101)

    return app


def main():
    from dotenv import load_dotenv
    load_dotenv()
    if not os.path.exists(ERROR_PATH):
        os.makedirs(ERROR_PATH)
    if not os.path.exists(SUBMISSIONS_PATH):
        os.makedirs(SUBMISSIONS_PATH)

    if not os.path.exists(DB_PATH):
        create_database.main()

    start_server()
    tornado.ioloop.IOLoop.current().start()


if __name__ == '__main__':
    main()

