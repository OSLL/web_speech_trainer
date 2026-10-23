"""Application settings; environment variables override defaults."""

import os

CONSTANTS_PRESENTATION_FILE_MAX_SIZE_IN_MEGABYTES = os.environ.get(
    "CONSTANTS_PRESENTATION_FILE_MAX_SIZE_IN_MEGABYTES", "16"
)
CONSTANTS_APP_SECRET_KEY = os.environ.get("APP_SECRET_KEY", "secret_key_placeholder")
CONSTANTS_LTI_CONSUMER_KEY = os.environ.get("LTI_CONSUMER_KEY", "secretconsumerkey")
CONSTANTS_LTI_CONSUMER_SECRET = os.environ.get(
    "LTI_CONSUMER_SECRET", "supersecretconsumersecret"
)
CONSTANTS_VERSION_FILE = os.environ.get("CONSTANTS_VERSION_FILE", "VERSION.json")
CONSTANTS_BACKUP_PATH = os.environ.get(
    "CONSTANTS_BACKUP_PATH", "../dump/database-dump/"
)
MONGODB_URL = os.environ.get("MONGODB_URL", "mongodb://localhost:27017/")
MONGODB_DATABASE_NAME = os.environ.get("MONGODB_DATABASE_NAME", "database")
WHISPER_URL = os.environ.get("WHISPER_URL", "http://localhost:9000/asr")
USER_AGENT_PLATFORM_WINDOWS = os.environ.get("USER_AGENT_PLATFORM_WINDOWS", "True")
USER_AGENT_PLATFORM_LINUX = os.environ.get("USER_AGENT_PLATFORM_LINUX", "True")
USER_AGENT_BROWSER_CHROME = os.environ.get("USER_AGENT_BROWSER_CHROME", "89")
USER_AGENT_BROWSER_FIREFOX = os.environ.get("USER_AGENT_BROWSER_FIREFOX", "87")
LOCALE_LANGUAGE = os.environ.get("LOCALE_LANGUAGE", "ru")
BUGREPORT_FORM_LINK = os.environ.get(
    "BUGREPORT_FORM_LINK",
    "https://docs.google.com/forms/d/e/1FAIpQLScUudcDPUwtTvmN_sbeljicHYhubK7pPQIM1o8Wh54HstT2BQ/viewform?usp=sf_link",
)
BUGREPORT_REPORT_MAIL = os.environ.get("BUGREPORT_REPORT_MAIL", "support@moevm.info")

CONSTANTS_STORAGE_MAX_SIZE_MBYTES = os.environ.get(
    "CONSTANTS_STORAGE_MAX_SIZE_MBYTES", "20000"
)
CONSTANTS_ACCESS_TOKEN = os.environ.get("API_ACCESS_TOKEN", "")
