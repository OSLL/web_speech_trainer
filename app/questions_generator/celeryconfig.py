import os
import configparser

APP_CONF = os.getenv("APP_CONF")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

broker_url = REDIS_URL
result_backend = REDIS_URL

task_serializer = "json"
result_serializer = "json"
accept_content = ["json"]

task_track_started = True
worker_hijack_root_logger = False
task_time_limit = 60 * 60
parser = configparser.ConfigParser()

if not APP_CONF:
    raise RuntimeError("APP_CONF is not set")

read_files = parser.read(APP_CONF)
if not read_files:
    raise RuntimeError(f"Cannot read APP_CONF file: {APP_CONF}")

mongodb_url = parser.get(
    "mongodb",
    "url",
    fallback=os.getenv("MONGODB_URL", "mongodb://db:27017/")
)

if not mongodb_url.endswith("/"):
    mongodb_url += "/"

mongodb_database_name = parser.get(
    "mongodb",
    "database_name",
    fallback=parser.get(
        "mongodb",
        "database",
        fallback=os.getenv("MONGODB_DATABASE_NAME", "web_speech_trainer")
    )
)

storage_max_size_mbytes = parser.get(
    "constants",
    "storage_max_size_mbytes",
    fallback=os.getenv("STORAGE_MAX_SIZE_MBYTES", "1024")
)
