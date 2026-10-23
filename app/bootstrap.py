"""Idempotent schema/data bootstrap; no executable jobs are stored in MongoDB."""

import os
from app.config import Config


def bootstrap():
    Config.init_config(os.environ["APP_CONF"])
    from app.mongo_odm import DBManager
    from pymodm.connection import _get_db

    DBManager()
    db = _get_db()
    from app.db_versioning.versions import LAST_VERSION, VERSIONS

    version = db.db_version.find_one()
    if version and version["version"] != LAST_VERSION:
        VERSIONS[LAST_VERSION].update_database(db, version["version"])
        db.db_version.update_one(
            {"_id": version["_id"]}, {"$set": VERSIONS[LAST_VERSION].to_dict()}
        )
    elif not version:
        db.db_version.insert_one(VERSIONS[LAST_VERSION].to_dict())
    db.oauth_nonces.create_index("expires_at", expireAfterSeconds=0)
    for name in ("criterion", "criterion_pack"):
        db[name].create_index("name", unique=True)
    db.consumers.create_index("consumer_key", unique=True)
    # Preserve access to legacy data, using its original LTI consumer identity.
    for attempt in db.task_attempts.find({"consumer_key": {"$in": [None, ""]}}):
        key = attempt.get("params_for_passback", {}).get("oauth_consumer_key")
        if key:
            db.task_attempts.update_one(
                {"_id": attempt["_id"]}, {"$set": {"consumer_key": key}}
            )
            db.trainings.update_many(
                {"task_attempt_id": attempt["_id"]}, {"$set": {"consumer_key": key}}
            )
    # Legacy tasks were global; clone their configuration into each consumer namespace.
    for task in db.tasks.find({"consumer_key": {"$in": [None, ""]}}):
        keys = db.task_attempts.distinct("consumer_key", {"task_id": task["task_id"]})
        for key in filter(None, keys):
            values = {name: value for name, value in task.items() if name != "_id"}
            values["consumer_key"] = key
            db.tasks.update_one(
                {"task_id": task["task_id"], "consumer_key": key},
                {"$setOnInsert": values},
                upsert=True,
            )
    for presentation in db.presentation_files.find({"owner": {"$in": [None, ""]}}):
        owners = {
            (item.get("username"), item.get("consumer_key"))
            for item in db.trainings.find(
                {"presentation_file_id": presentation["file_id"]},
                {"username": 1, "consumer_key": 1},
            )
        }
        if len(owners) == 1:
            owner, key = owners.pop()
            if owner and key:
                db.presentation_files.update_one(
                    {"_id": presentation["_id"]},
                    {"$set": {"owner": owner, "consumer_key": key}},
                )
    db.trainings.create_index([("processing_state", 1), ("processing_dispatch_at", 1)])
    db.trainings.create_index([("username", 1), ("consumer_key", 1), ("_id", -1)])
    db.tasks.create_index([("consumer_key", 1), ("task_id", 1)], unique=True)
    db.sessions.create_index([("consumer_key", 1), ("session_id", 1)], unique=True)
    db.task_attempts.create_index([("username", 1), ("task_id", 1), ("_id", -1)])
    from app.criteria.preconfigured_criterions import add_preconfigured_criterions_to_db
    from app.criteria_pack.preconfigured_pack import add_preconf_packs

    add_preconfigured_criterions_to_db()
    add_preconf_packs()
    from app.mongo_models import Consumers

    db.consumers.update_one(
        {"consumer_key": Config.c.constants.lti_consumer_key},
        {
            "$set": {"consumer_secret": Config.c.constants.lti_consumer_secret},
            "$setOnInsert": {
                "_cls": Consumers._mongometa.object_name,
                "timestamp_and_nonce": [],
            },
        },
        upsert=True,
    )


if __name__ == "__main__":
    bootstrap()
