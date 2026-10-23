"""Destructive-to-test-containers checks. Requires an isolated testing compose project."""

import os
from pathlib import Path
import subprocess
import time

import pytest
import requests

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.environ.get("WST_FAULT_TESTS") != "1"
        or "testing.py" not in os.environ.get("APP_CONF", ""),
        reason="Set WST_FAULT_TESTS=1 and APP_CONF=../app_conf/testing.py in an isolated compose project",
    ),
]
ROOT = Path(__file__).resolve().parents[2]
HOST = os.environ.get("WST_HOST", "http://127.0.0.1:5000")
WORKERS = ["worker_audio", "worker_presentation", "worker_training", "worker_passback"]


def compose(*args):
    subprocess.run(["docker", "compose", *args], cwd=ROOT, check=True, timeout=120)


def wait_for(check, timeout=420):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            result = check()
        except (requests.ConnectionError, requests.Timeout):
            # A service restart can interrupt a single polling request.
            result = False
        if result:
            return result
        time.sleep(1)
    pytest.fail("Timed out waiting for workflow recovery")


def prepare():
    client = requests.Session()
    assert client.get(HOST + "/init/", timeout=20).status_code == 200
    with open(ROOT / "tests/test_data/test_presentation_file_0.pdf", "rb") as source:
        response = client.post(
            HOST + "/api/files/presentations/",
            files={"presentation": ("test.pdf", source)},
            timeout=30,
        )
    assert response.status_code == 200, response.text
    file_id = response.json()["presentation_file_id"]
    response = client.post(
        HOST + f"/api/trainings/presentations/{file_id}/", timeout=20
    )
    assert response.status_code == 200, response.text
    training = response.json()["training_id"]
    for timestamp in (time.time(), time.time() + 15):
        assert client.put(
            HOST + f"/api/trainings/timestamps/{training}/",
            params={"timestamp": timestamp},
            timeout=20,
        ).ok
    with open(ROOT / "tests/simple_phrases_russian.mp3", "rb") as source:
        response = client.post(
            HOST + f"/api/trainings/presentation-records/{training}/",
            files={"presentationRecord": ("record.mp3", source)},
            data={"presentationRecordDuration": "15"},
            timeout=30,
        )
    assert response.status_code == 200, response.text
    return client, HOST + f"/api/trainings/{training}/"


def complete(client, url):
    state = client.get(url + "workflow/", timeout=20).json()
    assert state["state"] != "failed", state
    return state if state["state"] == "complete" else False


def test_jobs_survive_rabbitmq_container_recreation():
    client, url = prepare()
    compose("stop", "--timeout", "10", *WORKERS, "beat")
    try:
        assert client.post(url, timeout=60).status_code == 200
        run = client.get(url + "workflow/", timeout=20).json()["run_id"]
        compose("up", "-d", "--force-recreate", "rabbitmq")
    finally:
        compose("up", "-d", *WORKERS, "beat")
    state = wait_for(lambda: complete(client, url))
    assert state["run_id"] == run
    assert len(state["completed_stages"]) == 6


def test_publication_failure_is_recovered_without_another_user_request():
    client, url = prepare()
    compose("stop", "--timeout", "10", "rabbitmq")
    try:
        response = client.post(url, timeout=120)
        assert response.status_code == 503 and response.json()["recoverable"], (
            response.text
        )
        run = client.get(url + "workflow/", timeout=20).json()["run_id"]
    finally:
        compose("up", "-d", "rabbitmq")
    assert wait_for(lambda: complete(client, url))["run_id"] == run


def test_killed_audio_worker_resumes_after_lease_expires():
    client, url = prepare()
    assert client.post(url, timeout=60).status_code == 200

    def recognizing():
        state = client.get(url + "workflow/", timeout=20).json()
        assert state["state"] != "failed", state
        return "audio_recognition" in state["active_stages"]

    wait_for(recognizing, timeout=90)
    compose("kill", "-s", "SIGKILL", "worker_audio")
    compose("up", "-d", "worker_audio")
    state = wait_for(lambda: complete(client, url))
    assert len(state["completed_stages"]) == 6
