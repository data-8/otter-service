import base64
import json
import time
import logging
import signal
from functools import partial
import traceback
from datetime import datetime
import os
from hashlib import sha1
from sqlite3 import Error
from oauthlib.oauth1.rfc5849 import signature, parameters
import pandas as pd
import pytz
from pytz import timezone
from jupyterhub.services.auth import HubOAuthenticated, HubOAuthCallbackHandler
from jupyterhub.utils import url_path_join
from lxml import etree
import aiohttp
import async_timeout
import tornado.web
import tornado.httpserver
import tornado.ioloop
import tornado.escape
import tornado.options
import tornado.gen
from tornado.web import authenticated
from otter_service import access_sops_keys
from otter_service.grade_assignment import grade_assignment
from otter_service import create_database
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore

PREFIX = os.environ.get('JUPYTERHUB_SERVICE_PREFIX', '/services/gofer_nb/')
VOLUME_PATH = os.getenv("VOLUME_PATH")
ACCESS_LOG_FILE = f"{VOLUME_PATH}/" + os.getenv("ACCESS_LOG_FILE")
SERVER_LOG_FILE = f"{VOLUME_PATH}/" + os.getenv("SERVER_LOG_FILE")
OTTER_LOG_FILE = f"{VOLUME_PATH}/" + os.getenv("OTTER_LOG_FILE")
ERROR_FILE = f"{VOLUME_PATH}/" + os.getenv("ERROR_FILE")
ERROR_PATH = f"{VOLUME_PATH}/" + os.getenv("ERROR_PATH")
SUBMISSIONS_PATH = f"{VOLUME_PATH}/" + os.getenv("SUBMISSIONS_PATH")
DB_PATH = f"{VOLUME_PATH}/" + os.getenv("DB_PATH")


def write_grade(grade_info):
    """
    write the grade to the database

    :param grade_info: the four values in a tuple(userid, grade, section, lab, timestamp)
    :return Google FireStore document id
    """
    # Use the application default credentials
    cred = credentials.ApplicationDefault()
    firebase_admin.initialize_app(cred, {
        'projectId': os.environ.get("GCP_PROJECT_ID"),
    })

    db = firestore.client()
    date_format = "%Y-%m-%d %H:%M:%S %Z"
    date = datetime.now(tz=pytz.utc)
    date = date.astimezone(timezone('US/Pacific'))
    data = {
        'user': grade_info["userid"],
        'grade': grade_info["grade"],
        'section': grade_info["section"],
        'lab': grade_info["lab"],
        'date': date.strftime(date_format)
    }
    try:
        return db.collection(os.environ.get("ENVIRONMENT")).add(data)
    except Error as err:
        raise Exception(f"Error inserting into Google FireStore for the following record: {grade_info}") from err


class GradePostException(Exception):
    """
    custom Exception to throw for problems when you post grade
    """
    def __init__(self, message=None):
        self.message = message
        super().__init__(self.message)


class GradeSubmissionException(Exception):
    """
    custom Exception to throw for problems with the submission itself
    """
    def __init__(self, message=None):
        self.message = message
        super().__init__()


def create_post_url(course_id, assignment_id):
    """
    This creates post url used to save the grade to edx
    :param course_id: the course id for this notebook
    :param assignment_id:  the assignment id for this notebook
    :return: formatted string
    """
    post_url = f"https://{os.environ['EDX_URL']}/courses/course-v1:{course_id}/xblock/block-v1:{course_id}+type@lti_consumer+block@{assignment_id}"
    post_url += "/handler_noauth/outcome_service_handler"
    return post_url


def create_sourced_id(course_id, assignment_id):
    """
    This creates the string representing the source id used by EdX
    :param course_id: the course id for this notebook
    :param assignment_id:  the assignment id for this notebook
    :return: formatted string
    """
    return f"course-v1%3A{course_id}:{os.environ['EDX_URL']}-{assignment_id}"


async def post_grade(user_id, grade, course, section, assignment):
    """
    This posts the grade to the LTI server
    :param user_id: the user to post the grade for
    :param grade: the grade as a float
    :param course: the course this notebook is in
    :param section: the section this notebook is in
    :param assignment:  the assignment name for this notebook
    """
    body_hash = ""
    consumer_key = ""
    try:
        # post grade to EdX
        with open(f'{os.environ["COURSE_CONFIG_PATH"]}', 'r', encoding="utf8") as filename:
            # Course DEPENDENT configuration file
            # Should contain page for hitting the gradebook (outcomes_url)
            # as well as resource IDs for assignments
            # e.g. sourcedid['3']['lab02'] = c09d043b662b4b4b96fceacb1f4aa1c9
            # Make sure that it's placed in the working directory of the service (pwdx <PID>)
            course_config = json.load(filename)

        course_id = course_config[course][section]["course_id"]
        assignment_id = course_config[course][section]["assignments"][assignment]

        log_info_csv(user_id, course, section, assignment, f"Edx Course Config Loaded: Course Id: {course_id}, Assignment_id: {assignment_id}")

        sourced_id = create_sourced_id(course_id, assignment_id)
        outcomes_url = create_post_url(course_id, assignment_id)

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
        secrets_file = os.path.join(os.path.dirname(__file__), "secrets/gke_key.yaml")
        consumer_key = access_sops_keys.get("LTI_CONSUMER_KEY", secrets_file=secrets_file)
        consumer_secret = access_sops_keys.get("LTI_CONSUMER_SECRET", secrets_file=secrets_file)

        sourced_id = f"{sourced_id}:{user_id}"
        post_data = post_xml.format(grade=float(grade), sourcedid=sourced_id)

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
        status = response_tree.find('.//{http://www.imsglobal.org/services/ltiv1p1/xsd/imsoms_v1p0}imsx_statusInfo')
        code_major = status.find('{http://www.imsglobal.org/services/ltiv1p1/xsd/imsoms_v1p0}imsx_codeMajor').text
        desc = status.find('{http://www.imsglobal.org/services/ltiv1p1/xsd/imsoms_v1p0}imsx_description').text

        log_info_csv(user_id, course, section, assignment, f"Posted to Edx: code: {code_major}, desc: {desc}")

        if code_major != 'success':
            raise GradePostException(desc)

    except GradePostException as grade_post_exception:
        raise grade_post_exception
    except Exception as ex:
        raise Exception(f"Problem Posting Grade to LTI:{ex}") from ex


class GoferHandler(HubOAuthenticated, tornado.web.RequestHandler):
    """
    This class handles the HTTP requests for this tornado instance
    """
    def data_received(self, chunk):
        """
        abstract methods empty
        :param chunk
        """
        self.write("This is a post only page. You probably shouldn't be here!")

    @authenticated
    async def get(self):
        self.write("This is a post only page. You probably shouldn't be here!")
        self.finish()

    @authenticated
    async def post(self):
        notebook = None
        section = None
        assignment = None
        user = {}
        course = "8x"
        timestamp = get_timestamp()
        using_test_user = False
        try:
            # Accept notebook submissions, saves, then grades them
            
            user = self.get_current_user()
            log_info_csv("PRINT USER OBJ", course, section, assignment, str(user))
            if user is None:
                url_referer = self.request.headers.get("Referer")
                user = {"name": url_referer.split("/")[4]}
                using_test_user = True
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

            log_info_csv(user["name"], course, section, assignment, f"User logged in at {timestamp} -  Using Referrer: {using_test_user}")
            # save notebook submission with user id and time stamp
            submission_file = f"{VOLUME_PATH}/submissions/{user['name']}_{section}_{assignment}_{timestamp}.ipynb"
            with open(submission_file, 'w', encoding="utf8") as outfile:
                json.dump(notebook, outfile)

            args = {}
            args["course"] = course
            args["section"] = section
            args["assignments"] = assignment
            args["name"] = user["name"]
            args["submission_file"] = submission_file
            args["timestamp"] = str(timestamp)

            tornado.ioloop.IOLoop.current().spawn_callback(self._grade_and_post, args)

            # Let user know their submission was received
            self.write("Your submission is being graded and will be posted to the gradebook once it is finished running!")
            self.finish()
        except GradeSubmissionException as grade_submission_exception:
            if notebook is None:
                section = "No notebook was in the request body"
                assignment = "No notebook was in the request body"
            else:
                if section is None:
                    section = "Section: problem getting section - not in notebook?"
                if assignment is None:
                    assignment = "Assignment: problem getting assignment - not in notebook?"

            log_error_csv(timestamp, user['name'], section, assignment, str(grade_submission_exception))
        except Exception as ex:  # pylint: disable=broad-except
            log_error_csv(timestamp, user['name'], section, assignment, str(ex))

    async def _grade_and_post(self, args):
        """
        This is called by spawn_callback method on the IOLoop to move the actual grading and
        posting of the grade out of the main thread.

        :param args course, section, assignments, name, submission_file, timestamp coming from post method above
        """
        course = args["course"]
        section = args["section"]
        assignment = args["assignments"]
        name = args["name"]
        file_path = args["submission_file"]
        timestamp = args["timestamp"]
        try:
            # Grade assignment
            grade = await grade_assignment(file_path, section, assignment)
            log_info_csv(name, course, section, assignment, f"Grade: {grade}")
            # Write the grade to a sqlite database
            grade_info = (name, grade, section, assignment, timestamp)
            db_path = f"{VOLUME_PATH}/gradebook.db"
            write_grade(grade_info, db_path)
            log_info_csv(name, course, section, assignment, f"Grade Written to database: {grade}")

            if os.getenv("POST_GRADE").lower() in ("true", '1', 't'):
                await post_grade(name, grade, course, section, assignment)
            else:
                log_info_csv(name, course, section, assignment, f"Grade NOT posted to EdX on purpose: {grade}")
                raise GradePostException("NOT POSTING Grades on purpose; see deployment-config-encrypted.yaml -- POST_GRADE")
        except GradePostException as gp:
            log_error_csv(timestamp, name, section, assignment, str(gp))
        except Exception as ex:
            log_error_csv(timestamp, name, section, assignment, str(ex))


def get_timestamp():
    """
    returns the time stamp in PST Time
    """
    utc_now = pytz.utc.localize(datetime.utcnow())
    pst_now = utc_now.astimezone(pytz.timezone("America/Los_Angeles"))
    return pst_now.strftime("%Y-%m-%d-%H:%M:%S.%f")[:-3]


def log_info_csv(username, course, section, assignment, msg):
    """
    This logs information in the chain of events -- user logs in and submits,
    graded, posted to Edx

    :param username: the username
    :param course: the course
    :param section: the section
    :param assignment: the assignment
    :param msg: optional message to logs
    """
    if os.getenv("VERBOSE_LOGGING") == "True":
        try:
            data_frame = pd.read_csv(OTTER_LOG_FILE)
        except Exception:
            data_frame = pd.DataFrame(columns=["timestamp", "username", "course", "section", "assignment", "message"])

        data_frame.loc[len(data_frame.index)] = [get_timestamp(), username, course, section, assignment, msg]
        data_frame.to_csv(OTTER_LOG_FILE, index=False)


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
        data_frame = pd.read_csv(ERROR_FILE)
    except Exception:
        data_frame = pd.DataFrame(columns=["timestamp", "username", "section", "assignment", "error", "filename"])

    filename = timestamp + "_" + str(username)
    trace = f"User: {username}\nSection: {section}\nAssignment: {assignment}\n\n"
    trace += str(traceback.format_exc())

    with open(f"{ERROR_PATH}/{filename}.txt", "a+", encoding="utf8") as file_handle:
        file_handle.write(trace)

    data_frame.loc[len(data_frame.index)] = [timestamp, username, section, assignment, msg, filename]
    data_frame.to_csv(ERROR_FILE, index=False)


def start_server():
    """
    start the tornado server listening on port 10101 - I seperated this function from the main()
    in order to make testing easier
    :return: the application tornado object
    """
    tornado.options.parse_command_line()

    # app = tornado.web.Application(
    #     [(PREFIX, GoferHandler)]
    # )
    app = tornado.web.Application(
        [
            (PREFIX, GoferHandler),
            (
                url_path_join(
                    os.environ['JUPYTERHUB_SERVICE_PREFIX'], 'oauth_callback'
                ),
                HubOAuthCallbackHandler,
            )
        ],
        cookie_secret=os.urandom(32),
    )

    logger = logging.getLogger('tornado.application')
    file_handler = logging.FileHandler(SERVER_LOG_FILE)
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    access_logger = logging.getLogger("tornado.access")
    access_logger.setLevel(logging.DEBUG)
    access_file_handler = logging.FileHandler(ACCESS_LOG_FILE)
    access_file_handler.setFormatter(formatter)
    access_logger.addHandler(access_file_handler)

    server = tornado.httpserver.HTTPServer(app)
    server.listen(10101)

    signal.signal(signal.SIGTERM, partial(sig_handler, server))
    signal.signal(signal.SIGINT, partial(sig_handler, server))

    return app


def main():
    """
    This sets up the paths needed for gofer and starts tornado
    """
    try:
        if not os.path.exists(ERROR_PATH):
            os.makedirs(ERROR_PATH)
        if not os.path.exists(SUBMISSIONS_PATH):
            os.makedirs(SUBMISSIONS_PATH)

        if not os.path.exists(DB_PATH):
            create_database.main()
        start_server()
        logging.getLogger('tornado.application').info("Starting Server")
        tornado.ioloop.IOLoop.current().start()
    except Exception:
        logging.getLogger('tornado.application').error(traceback.format_exc())


def sig_handler(server, sig, frame):
    io_loop = tornado.ioloop.IOLoop.instance()
    MAX_WAIT_SECONDS_BEFORE_SHUTDOWN = 3

    def stop_loop(deadline):
        io_loop.stop()
        logging.info('Shutdown finally')

    def shutdown():
        logging.info('Stopping http server')
        server.stop()
        logging.info('Will shutdown in %s seconds ...',
                     MAX_WAIT_SECONDS_BEFORE_SHUTDOWN)
        stop_loop(time.time() + MAX_WAIT_SECONDS_BEFORE_SHUTDOWN)

    logging.warning('Caught signal: %s', sig)
    io_loop.add_callback_from_signal(shutdown)


if __name__ == '__main__':
    main()
