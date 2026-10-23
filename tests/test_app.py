from app.audio import Audio
from app.criteria import FillersRatioCriterion



def test_init_page(*, app):
    flask_app = app

    with flask_app.test_client() as test_client:
        response = test_client.get('/init/')
        assert response.status_code == 200


def test_fillers_ratio_criteria():
    criterion = FillersRatioCriterion(
        parameters={'fillers': ['а', 'ну', 'это самое']},
        dependent_criteria=[],
    )
    with open('test_data/test_audio_7.json', 'rb') as test_audio_file:
        test_audio = Audio.from_json_file(test_audio_file)
        criterion_result = criterion.apply(test_audio, presentation=None, training_id=None, criteria_results={})
        assert criterion_result.result == 1 - 1 / 893
