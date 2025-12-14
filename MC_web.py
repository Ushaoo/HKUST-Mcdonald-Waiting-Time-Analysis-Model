import cv2
import numpy as np
from ultralytics import YOLO
from collections import deque
from datetime import datetime
from flask import Flask, render_template, Response, request, jsonify, send_from_directory, redirect
import threading
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
UPLOAD_FOLDER = '/tmp/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp'}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

class CrowdDensityMonitor:
    def __init__(self, model_name='yolov8n.pt', camera_id=0):
        """Initialize YOLO model and camera"""
        self.model = YOLO(model_name)
        self.cap = cv2.VideoCapture(camera_id)
        self.cap.set(cv2.CAP_PROP_FPS, 30)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.density_history = deque(maxlen=100)
        self.detections = []
        self.lock = threading.Lock()
        self.frame_skip = 3
        self.frame_count = 0
        self.person_count = 0
        self.density = 0
        print("初始化完成，使用CPU推理（开发板）")
        
    def detect_people(self, frame):
        """Detect people in frame using YOLO"""
        results = self.model(frame, classes=0, conf=0.5, verbose=False)
        detections = results[0].boxes
        return detections
    
    def calculate_density(self, detections, frame_shape):
        """Calculate crowd density"""
        person_count = len(detections)
        frame_area = frame_shape[0] * frame_shape[1]
        density = person_count / (frame_area / 10000)
        self.density_history.append(person_count)
        return person_count, density
    
    def draw_info(self, frame, person_count, density):
        """Draw detection info on frame"""
        cv2.putText(frame, f'People Count: {person_count}', (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.putText(frame, f'Density: {density:.2f}', (10, 70),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.putText(frame, f'Time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}', (10, 110),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        return frame
    
    def generate_frames(self):
        """Generate frames for streaming"""
        while True:
            ret, frame = self.cap.read()
            if not ret:
                break
            
            frame_small = cv2.resize(frame, (640, 480))
            
            if self.frame_count % self.frame_skip == 0:
                detections = self.detect_people(frame_small)
                person_count, density = self.calculate_density(detections, frame_small.shape)
                with self.lock:
                    self.detections = detections
                    self.person_count = person_count
                    self.density = density
            else:
                with self.lock:
                    person_count = self.person_count
                    density = self.density
                    detections = self.detections
            
            self.frame_count += 1
            
            display_frame = self.draw_info(frame_small, person_count, density)
            
            for detection in detections:
                x1, y1, x2, y2 = detection.xyxy[0]
                cv2.rectangle(display_frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
            
            ret, buffer = cv2.imencode('.jpg', display_frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
            frame_data = buffer.tobytes()
            
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_data + b'\r\n')
    
    def process_image(self, image_path):
        """Process a single image"""
        frame = cv2.imread(image_path)
        if frame is None:
            return None, 0, 0
        
        # Resize if too large
        if frame.shape[0] > 1080 or frame.shape[1] > 1920:
            frame = cv2.resize(frame, (960, 720))
        
        detections = self.detect_people(frame)
        person_count, density = self.calculate_density(detections, frame.shape)
        
        display_frame = self.draw_info(frame, person_count, density)
        
        for detection in detections:
            x1, y1, x2, y2 = detection.xyxy[0]
            cv2.rectangle(display_frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
        
        return display_frame, person_count, density

# Initialize monitor
monitor = CrowdDensityMonitor()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ==================== Routes ====================

@app.route('/')
def index():
    """首页 - 选择模式"""
    return render_template('index.html')

@app.route('/mode/<mode>')
def mode_select(mode):
    """根据选择的模式返回相应页面"""
    if mode == 'video':
        return render_template('video.html')
    elif mode == 'upload':
        return render_template('upload.html')
    else:
        return redirect('/')

@app.route('/video_feed')
def video_feed():
    """实时视频流"""
    return Response(monitor.generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/upload', methods=['POST'])
def upload_file():
    """处理上传的照片"""
    if 'file' not in request.files:
        return jsonify({'error': '没有文件'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': '没有选择文件'}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # 处理图像
        result_frame, person_count, density = monitor.process_image(filepath)
        
        if result_frame is None:
            return jsonify({'error': '无法读取图像'}), 400
        
        # 保存结果图像
        result_filename = f'result_{datetime.now().strftime("%Y%m%d_%H%M%S")}.jpg'
        result_path = os.path.join(app.config['UPLOAD_FOLDER'], result_filename)
        cv2.imwrite(result_path, result_frame)
        
        return jsonify({
            'success': True,
            'person_count': int(person_count),
            'density': float(density),
            'image_url': f'/get_image/{result_filename}'
        })
    
    return jsonify({'error': '文件格式不支持'}), 400

@app.route('/get_image/<filename>')
def get_image(filename):
    """获取处理后的图像"""
    try:
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
    except:
        return jsonify({'error': '文件不存在'}), 404

if __name__ == '__main__':
    print("=" * 50)
    print("启动 Flask 服务器")
    print("=" * 50)
    print("在浏览器中打开: http://localhost:5000")
    print("=" * 50)
    app.run(host='0.0.0.0', port=5000, debug=False)
