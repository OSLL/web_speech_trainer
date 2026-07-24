from flask import Blueprint


routes_interview = Blueprint('routes_interview', __name__)

# Регистрируем handlers после создания blueprint, чтобы избежать циклических импортов.
from app.routes import interview as _interview_routes  # noqa: F401,E402
from app.api import interview as _interview_api  # noqa: F401,E402