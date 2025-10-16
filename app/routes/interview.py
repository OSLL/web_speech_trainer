from flask import Blueprint, render_template

routes_interview = Blueprint('routes_interview', __name__)

@routes_interview.route('/interview', methods=['GET'])
def interview_page():
    return render_template(
        'interview.html'
    ), 200
