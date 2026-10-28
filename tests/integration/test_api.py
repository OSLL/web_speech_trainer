"""HTTP and BSON export checks against the isolated real stack."""

from io import BytesIO
from pathlib import Path
import os
from zipfile import ZipFile

from bson import decode_all
import pytest
import requests

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        "testing.py" not in os.environ.get("APP_CONF", "")
        or not os.environ.get("COMPOSE_PROJECT_NAME"),
        reason="Requires testing.py and an isolated Compose project",
    ),
]
HOST = os.environ.get("WST_HOST", "http://127.0.0.1:5000")
ROOT = Path(__file__).resolve().parents[2]


def test_database_exports_include_bson_and_gridfs():
    client = requests.Session()
    assert client.get(HOST + "/init/", timeout=20).status_code == 200
    with (ROOT / "tests/test_data/test_presentation_file_0.pdf").open("rb") as source:
        upload = client.post(
            HOST + "/api/files/presentations/",
            files={"presentation": ("export.pdf", source)},
            timeout=30,
        )
    assert upload.status_code == 200, upload.text
    for name in ("backup.zip", "backup_nochunks.zip"):
        assert (
            client.get(HOST + "/api/dumps/create/" + name, timeout=20).status_code
            == 405
        )
        created = client.post(HOST + "/api/dumps/create/" + name, timeout=60)
        assert created.status_code == 200, created.text
        exported = client.get(HOST + "/api/dumps/download/" + name, timeout=60)
        assert exported.status_code == 200
        with ZipFile(BytesIO(exported.content)) as archive:
            assert archive.testzip() is None
            assert "testing_database/fs.files.bson" in archive.namelist()
            assert decode_all(archive.read("testing_database/fs.files.bson"))
            assert "testing_database/fs.files.metadata.json" in archive.namelist()
            assert ("testing_database/fs.chunks.bson" in archive.namelist()) == (
                name == "backup.zip"
            )


def test_pages_and_read_apis_are_available():
    client = requests.Session()
    assert client.get(HOST + "/init/", timeout=20).status_code == 200
    for path in (
        "/",
        "/training_greeting/",
        "/admin/",
        "/dumps/",
        "/api/sessions/info/",
        "/api/sessions/admin/",
        "/api/trainings/?page=0&count=10",
        "/api/presentations/?page=0&count=10",
        "/api/logs/?page=0&count=10",
        "/api/dumps/",
        "/api/version/info/",
        "/api/criterion/SimpleDurationCriterion/",
        "/api/criterion/SpeechDurationCriterion/structure/",
        "/api/criteria_pack/SimplePack/",
    ):
        response = client.get(HOST + path, timeout=20)
        assert response.status_code == 200, (path, response.text)
    for path in (
        "/api/trainings/not-an-id/",
        "/api/presentations/not-an-id/",
        "/api/criterion/not-a-criterion/structure/",
    ):
        assert client.get(HOST + path, timeout=20).status_code == 404
