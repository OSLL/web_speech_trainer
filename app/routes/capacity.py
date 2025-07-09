from flask import Blueprint, render_template
from app.mongo_odm import DBManager
from app.root_logger import get_root_logger
from app.lti_session_passback.auth_checkers import is_admin

logger = get_root_logger()

BYTES_PER_MB = 1024*1024

routes_capacity = Blueprint(
    'routes_capacity', __name__, url_prefix='/capacity')

@routes_capacity.route('/', methods=['GET'])
def storage_capacity():
    if not is_admin():
        return {}, 404
    current_size = DBManager().get_used_storage_size()
    max_size = DBManager().get_max_size()
    ratio = current_size / max_size
    return render_template(
        'capacity.html',
        size=round(current_size / BYTES_PER_MB, 2),
        max_size=round(max_size / BYTES_PER_MB, 2),
        ratio=round(ratio * 100, 1)
    )
    