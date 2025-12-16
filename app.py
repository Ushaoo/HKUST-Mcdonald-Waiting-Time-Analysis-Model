from flask import Flask, render_template, jsonify
from data.mock_data import get_realtime_data, get_history_data

app = Flask(__name__)

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

if __name__ == '__main__':
    app.run(debug=True)
