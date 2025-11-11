from flask import Blueprint, render_template

routes_interview = Blueprint('routes_interview', __name__)

@routes_interview.route('/interview', methods=['GET'])
def interview_page():
    return render_template(
        'interview.html'
    ), 200


@routes_interview.route("/avatar_stream")
def avatar_stream():
    def generate():
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        _, buffer = cv2.imencode('.jpg', frame)
        jpg_bytes = buffer.tobytes()

        while True:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + jpg_bytes + b'\r\n')

    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')
