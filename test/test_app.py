from app.audio import Audio
from app.criteria import FillersRatioCriteria
from app.criteria_pack import FillersRatioCriteriaPack
from app.web_speech_trainer import app


def test_home_page():
    """
    GIVEN a Flask application configured for testing
    WHEN the '/' page is requested (GET)
    THEN check that the response is valid
    """
    flask_app = app

    with flask_app.test_client() as test_client:
        response = test_client.get('/')
        assert response.status_code == 200


def test_fillers_ratio_criteria():
    criteria = FillersRatioCriteria(
        parameters={'fillers': ['а', 'ну']},
        dependent_criterion=[],
    )
    with open('test_audio.json', 'rb') as test_audio_file:
        test_audio = Audio.from_json_file(test_audio_file)
        criteria_result = criteria.apply(test_audio, presentation=None, criteria_results={})
        assert criteria_result.result == 1 - 1 / 893
