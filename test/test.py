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
