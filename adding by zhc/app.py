from flask import Flask, render_template, jsonify, Response
from data.mock_data import get_realtime_data, get_history_data
import cv2

app = Flask(__name__)

# 打开摄像头（0 为默认摄像头）
camera = cv2.VideoCapture(0)

def gen_frames():
    while True:
        success, frame = camera.read()
        if not success:
            break
        else:
            ret, buffer = cv2.imencode('.jpg', frame)
            frame_bytes = buffer.tobytes()

            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')


@app.route('/')
def realtime_view():
    data = get_realtime_data()
    return render_template('index.html', data=data)


@app.route('/history')
def history_view():
    data = get_history_data()
    return render_template('history.html', data=data)


@app.route('/api/realtime')
def api_realtime():
    return jsonify(get_realtime_data())


@app.route('/api/history')
def api_history():
    return jsonify(get_history_data())


@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


if __name__ == '__main__':
    app.run(debug=True)
