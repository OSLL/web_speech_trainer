"""Application settings; environment variables override defaults."""

import os

CONSTANTS_PRESENTATION_FILE_MAX_SIZE_IN_MEGABYTES = os.environ.get(
    "CONSTANTS_PRESENTATION_FILE_MAX_SIZE_IN_MEGABYTES", "16"
)
CONSTANTS_APP_SECRET_KEY = os.environ.get("APP_SECRET_KEY", "testing_app_secret_key")
CONSTANTS_LTI_CONSUMER_KEY = os.environ.get(
    "LTI_CONSUMER_KEY", "testing_lti_consumer_key"
)
CONSTANTS_LTI_CONSUMER_SECRET = os.environ.get(
    "LTI_CONSUMER_SECRET", "testing_lti_consumer_secret"
)
CONSTANTS_VERSION_FILE = os.environ.get("CONSTANTS_VERSION_FILE", "VERSION.json")
CONSTANTS_BACKUP_PATH = os.environ.get(
    "CONSTANTS_BACKUP_PATH", "../dump/database-dump/"
)
CONSTANTS_STORAGE_MAX_SIZE_MBYTES = os.environ.get(
    "CONSTANTS_STORAGE_MAX_SIZE_MBYTES", "20000"
)
CONSTANTS_ACCESS_TOKEN = os.environ.get("API_ACCESS_TOKEN", "access_token_for_api")
MONGODB_URL = os.environ.get("MONGODB_URL", "mongodb://db:27017/")
MONGODB_DATABASE_NAME = os.environ.get("MONGODB_DATABASE_NAME", "testing_database")
WHISPER_URL = os.environ.get("WHISPER_URL", "http://whisper:9000/asr")
TESTING_ACTIVE = os.environ.get("TESTING_ACTIVE", "True")
TESTING_SESSION_ID = os.environ.get("TESTING_SESSION_ID", "testing_session_id")
TESTING_LIS_OUTCOME_SERVICE_URL = os.environ.get(
    "TESTING_LIS_OUTCOME_SERVICE_URL", "http://example.com"
)
TESTING_LIS_RESULT_SOURCE_DID = os.environ.get(
    "TESTING_LIS_RESULT_SOURCE_DID",
    '"{\\"data\\":{\\"instanceid\\":\\"123\\",\\"userid\\":\\"456\\",\\"typeid\\":\\"789\\",\\"launchid\\":0123456789},\\"hash\\":\\"00112233445566778899aabbccddeeffffeeddccbbaa998877665544332211\\"}"',
)
TESTING_OAUTH_CONSUMER_KEY = os.environ.get(
    "TESTING_OAUTH_CONSUMER_KEY", "testing_oath_consumer_key"
)
TESTING_IS_ADMIN = os.environ.get("TESTING_IS_ADMIN", "True")
TESTING_LIS_PERSON_NAME_FULL = os.environ.get(
    "TESTING_LIS_PERSON_NAME_FULL", "testing_lis_person_name_full"
)
TESTING_CUSTOM_TASK_ID = os.environ.get(
    "TESTING_CUSTOM_TASK_ID", "testing_custom_task_id"
)
TESTING_CUSTOM_TASK_DESCRIPTION = os.environ.get(
    "TESTING_CUSTOM_TASK_DESCRIPTION", "testing_custom_task_description"
)
TESTING_CUSTOM_ATTEMPT_COUNT = os.environ.get("TESTING_CUSTOM_ATTEMPT_COUNT", "3")
TESTING_CUSTOM_REQUIRED_POINTS = os.environ.get("TESTING_CUSTOM_REQUIRED_POINTS", "1.5")
TESTING_CUSTOM_CRITERIA_PACK_ID = os.environ.get(
    "TESTING_CUSTOM_CRITERIA_PACK_ID", "SimplePack"
)
TESTING_CUSTOM_FEEDBACK_EVALUATOR_ID = os.environ.get(
    "TESTING_CUSTOM_FEEDBACK_EVALUATOR_ID", "1"
)
TESTING_CUSTOM_FORMATS = os.environ.get("TESTING_CUSTOM_FORMATS", "pdf,pptx,ppt,odp")
TESTING_ROLES = os.environ.get("TESTING_ROLES", "Instructor")
USER_AGENT_PLATFORM_WINDOWS = os.environ.get("USER_AGENT_PLATFORM_WINDOWS", "True")
USER_AGENT_PLATFORM_LINUX = os.environ.get("USER_AGENT_PLATFORM_LINUX", "True")
USER_AGENT_BROWSER_CHROME = os.environ.get("USER_AGENT_BROWSER_CHROME", "89")
USER_AGENT_BROWSER_FIREFOX = os.environ.get("USER_AGENT_BROWSER_FIREFOX", "87")
LOCALE_LANGUAGE = os.environ.get("LOCALE_LANGUAGE", "ru")
BUGREPORT_FORM_LINK = os.environ.get("BUGREPORT_FORM_LINK", "forms/")
BUGREPORT_REPORT_MAIL = os.environ.get("BUGREPORT_REPORT_MAIL", "mail")

# Interview mode (custom_mode=interview in the LTI launch).
CONSTANTS_ALLOWED_EXPLANATORY_NOTE_EXTENSIONS = {'.docx', '.doc'}
CONSTANTS_DEFAULT_INTERVIEW_QUESTIONS_COUNT = 3
CONSTANTS_DEFAULT_INTERVIEW_SESSION_MINUTES = 3
CONSTANTS_DEFAULT_INTERVIEW_ATTEMPT_COUNT = 2
CONSTANTS_QUESTIONS_POLL_INTERVALS_MS = 2000
CONSTANTS_INTERVIEW_CRITERIA_PACK_ID = 'INTERVIEW_SIMPLE_V1'
CONSTANTS_INTERVIEW_FEEDBACK_EVALUATION_ID = 0
CONSTANTS_IDEAL_ANSWER_MIN_SEC = 15
CONSTANTS_IDEAL_ANSWER_MAX_SEC = 60
CONSTANTS_MIN_ANSWER_SEC = 5
CONSTANTS_QUESTION_GENERATION_TASK_NAME = 'app.questions_generator.tasks.generate_questions'
