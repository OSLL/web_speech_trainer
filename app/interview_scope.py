"""Interview storage key, independent of cookies and unique to an LTI namespace.

Legacy username-only keys are intentionally not read: their consumer/task ownership
cannot be inferred safely. Workers receive this key explicitly from the server.
"""
import json
from flask import session


def interview_session_id():
    username = session.get("session_id")
    consumer = session.get("consumer_key")
    task = session.get("task_id")
    if not username or not consumer or not task:
        return None
    return "interview:v1:" + json.dumps(
        [consumer, task, username], ensure_ascii=True, separators=(",", ":")
    )
