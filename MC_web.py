import cv2
import numpy as np
from ultralytics import YOLO
from collections import deque
from datetime import datetime
from flask import Flask, render_template, Response, request, jsonify, send_from_directory, redirect
import threading
import os
import sys
from werkzeug.utils import secure_filename

app = Flask(__name__)
UPLOAD_FOLDER = '/tmp/uploads'
OUTPUT_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'processed_videos')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp'}
VIDEO_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv', 'flv', 'wmv'}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max file size

class CrowdDensityMonitor:
    def __init__(self, model_name='yolov8n.pt', camera_id=0, width=1280, height=720, conf=0.1):
        """Initialize YOLO model and camera
        
        Args:
            model_name: YOLO模型文件名 (yolov8n/s/m/l/x.pt)
            camera_id: 摄像头ID
            width: 输入分辨率宽度 (推荐: 1280)
            height: 输入分辨率高度 (推荐: 720)
            conf: 置信度阈值 (默认: 0.35，范围: 0.1-0.9)
        """
        # 实时视频流专用模型
        self.model = YOLO(model_name)
        # 上传文件处理专用模型 - 独立实例，不与实时视频竞争资源
        self.upload_model = YOLO(model_name)
        
        # 检测参数 - 可配置
        self.confidence_threshold = conf
        self.cap = cv2.VideoCapture(camera_id)
        self.cap.set(cv2.CAP_PROP_FPS, 30)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        
        # 验证实际分辨率
        actual_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        self.density_history = deque(maxlen=100)
        self.detections = []
        self.lock = threading.Lock()
        
        # 视频流参数
        self.current_frame = None
        self.frame_for_detection = None
        self.frame_count = 0
        self.inference_time = 0
        
        # 检测结果
        self.person_count = 0
        self.density = 0
        
        # 后台检测线程
        self.detection_thread = None
        self.stop_detection = False
        self.detection_interval = 3  # 每3帧检测一次
        
        print("初始化完成（高分辨率+多线程优化）")
        print(f"  - 请求分辨率: {width}x{height}")
        print(f"  - 实际分辨率: {actual_width}x{actual_height}")
        print(f"  - 模型: {model_name}")
        print(f"  - 置信度阈值: {self.confidence_threshold} (越低检测越灵敏，越容易误检)")
        print(f"  - 模式: 多线程分离视频流和检测")
        print(f"  - 检测间隔: 每{self.detection_interval}帧")
        print(f"  - 视频流: 独立处理，保证30 FPS流畅 + 高精度检测")
        
    def start_detection_thread(self):
        """启动后台检测线程"""
        self.stop_detection = False
        self.detection_thread = threading.Thread(target=self._detection_worker, daemon=True)
        self.detection_thread.start()
        print("[✓] 后台检测线程已启动", flush=True)
        
    def stop_detection_thread(self):
        """停止后台检测线程"""
        self.stop_detection = True
        if self.detection_thread:
            self.detection_thread.join(timeout=2)
        
    def _detection_worker(self):
        """后台检测工作线程 - 独立处理，不影响视频流"""
        import time
        detection_count = 0
        
        while not self.stop_detection:
            # 从缓冲中获取待检测的帧
            with self.lock:
                frame_to_detect = self.frame_for_detection
            
            if frame_to_detect is not None:
                try:
                    start_time = time.time()
                    # 使用原始分辨率进行高精度检测
                    results = self.model(frame_to_detect, classes=0, conf=self.confidence_threshold, verbose=False)
                    self.inference_time = time.time() - start_time
                    detections = results[0].boxes
                    
                    person_count = len(detections)
                    frame_area = frame_to_detect.shape[0] * frame_to_detect.shape[1]
                    density = person_count / (frame_area / 10000)
                    
                    # 更新检测结果
                    with self.lock:
                        self.detections = detections
                        self.person_count = person_count
                        self.density = density
                    
                    detection_count += 1
                    if detection_count % 5 == 0:
                        print(f"[检测] 已处理{detection_count}次 | 最新: {person_count}人 | 耗时: {self.inference_time*1000:.0f}ms", flush=True)
                    
                except Exception as e:
                    print(f"[警告] 检测失败: {e}", flush=True)
            
            time.sleep(0.01)  # 避免CPU空转
        
    def detect_people(self, frame):
        """检测人群（使用后台线程结果）"""
        with self.lock:
            return self.detections
    
    def calculate_density(self, detections, frame_shape):
        """计算密度（使用后台线程结果）"""
        with self.lock:
            return self.person_count, self.density
    
    def draw_info(self, frame, person_count, density):
        """Draw detection info on frame"""
        cv2.putText(frame, f'People Count: {person_count}', (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.putText(frame, f'Density: {density:.2f}', (10, 70),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.putText(frame, f'Time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}', (10, 110),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        # 显示推理时间和模式
        fps_text = f'Inference: {self.inference_time*1000:.0f}ms (后台处理)'
        cv2.putText(frame, fps_text, (10, 150),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        return frame
    
    def generate_frames(self):
        """生成视频流 - 仅用于视频播放，不做任何检测或绘制
        
        这是轻量级方案：只输出原始视频流，不在服务器端绘制
        检测结果通过单独的 API 返回，由客户端负责可视化
        这样可以大大减少 RDK 的 CPU 占用"""
        print("[视频流] 开始生成轻量级视频帧流（无绘制）...", flush=True)
        detection_frame_counter = 0
        
        while True:
            ret, frame = self.cap.read()
            if not ret:
                print("[视频流] 视频流结束", flush=True)
                break
            
            # 每隔detection_interval帧提供一个给检测线程
            if detection_frame_counter % self.detection_interval == 0:
                with self.lock:
                    self.frame_for_detection = frame.copy()
            
            detection_frame_counter += 1
            self.frame_count += 1
            
            # 编码为JPEG（质量70以减少带宽）- 仅输出原始视频，无任何绘制
            ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
            frame_data = buffer.tobytes()
            
            # 流式输出
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
    
    def process_uploaded_image(self, image_path):
        """
        [上传文件专用] 处理上传的图片 - 使用独立的模型实例
        避免与实时视频流竞争资源，确保更快的处理速度
        """
        import time
        frame = cv2.imread(image_path)
        if frame is None:
            return None, 0, 0
        
        # Resize if too large
        if frame.shape[0] > 1080 or frame.shape[1] > 1920:
            frame = cv2.resize(frame, (960, 720))
        
        try:
            start_time = time.time()
            # 使用独立的 upload_model 进行检测，不受实时视频线程影响
            results = self.upload_model(frame, classes=0, conf=self.confidence_threshold, verbose=False)
            inference_time = time.time() - start_time
            detections = results[0].boxes
            
            person_count = len(detections)
            frame_area = frame.shape[0] * frame.shape[1]
            density = person_count / (frame_area / 10000)
            
            print(f"[上传图片] 检测完成 | {person_count}人 | 耗时: {inference_time*1000:.0f}ms", flush=True)
            
            display_frame = self.draw_info(frame, person_count, density)
            
            for detection in detections:
                x1, y1, x2, y2 = detection.xyxy[0]
                cv2.rectangle(display_frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
            
            return display_frame, person_count, density
        
        except Exception as e:
            print(f"[上传图片] 检测失败: {e}", flush=True)
            return None, 0, 0
    
    def process_uploaded_video(self, video_path, output_path):
        """
        [上传文件专用] 处理上传的视频 - 使用独立的模型实例
        避免与实时视频流竞争资源，实现全速处理
        """
        import time
        cap = cv2.VideoCapture(video_path)
        
        if not cap.isOpened():
            return None
        
        frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        # 定义视频编码和输出
        codec_chain = [
            ('MJPG', cv2.VideoWriter_fourcc(*'MJPG'), 'avi'),
            ('XVID', cv2.VideoWriter_fourcc(*'XVID'), 'avi'),
            ('FFV1', cv2.VideoWriter_fourcc(*'FFV1'), 'avi'),
        ]
        
        out = None
        output_file = None
        
        for codec_name, fourcc, ext in codec_chain:
            output_file = output_path.replace('.avi', '') + f'.{ext}'
            try:
                out = cv2.VideoWriter(output_file, fourcc, fps, (frame_width, frame_height))
                if out.isOpened():
                    print(f"[上传视频] 编码器: {codec_name}", flush=True)
                    break
            except:
                pass
        
        if out is None or not out.isOpened():
            print("[上传视频] 无法创建输出视频", flush=True)
            cap.release()
            return None
        
        frame_count = 0
        person_counts = []
        density_values = []
        
        print(f"[上传视频] 开始处理 | 总帧数: {total_frames} | 分辨率: {frame_width}x{frame_height}", flush=True)
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            frame_count += 1
            
            try:
                # 使用独立的 upload_model 进行检测，全速处理
                results = self.upload_model(frame, classes=0, conf=self.confidence_threshold, verbose=False)
                detections = results[0].boxes
                
                person_count = len(detections)
                frame_area = frame.shape[0] * frame.shape[1]
                density = person_count / (frame_area / 10000)
                
                person_counts.append(person_count)
                density_values.append(density)
                
                # 绘制信息
                display_frame = self.draw_info(frame, person_count, density)
                
                # 绘制检测框
                for detection in detections:
                    x1, y1, x2, y2 = detection.xyxy[0]
                    cv2.rectangle(display_frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
                
                out.write(display_frame)
                
                # 每50帧输出一次进度
                if frame_count % 50 == 0:
                    progress = (frame_count / total_frames) * 100
                    print(f"[上传视频] 进度: {frame_count}/{total_frames} ({progress:.1f}%) | 当前: {person_count}人", flush=True)
            
            except Exception as e:
                print(f"[上传视频] 处理第{frame_count}帧失败: {e}", flush=True)
                out.write(frame)
        
        cap.release()
        out.release()
        
        # 计算统计信息
        avg_count = sum(person_counts) / len(person_counts) if person_counts else 0
        min_count = min(person_counts) if person_counts else 0
        max_count = max(person_counts) if person_counts else 0
        
        print(f"[上传视频] 处理完成 | 平均: {avg_count:.1f}人 | 最小: {min_count}人 | 最大: {max_count}人", flush=True)
        
        return {
            'avg_count': avg_count,
            'min_count': min_count,
            'max_count': max_count,
            'total_frames': frame_count,
            'output_file': output_file
        }

# Initialize monitor with high resolution for better detection
# conf=0.35 使得检测更灵敏，可以检测到边缘和部分遮挡的人体
monitor = CrowdDensityMonitor(width=1280, height=720, conf=0.35)
monitor.start_detection_thread()  # 启动后台检测线程

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def allowed_video(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in VIDEO_EXTENSIONS

def is_image(filename):
    """检查是否为图片"""
    return allowed_file(filename)

def is_video(filename):
    """检查是否为视频"""
    return allowed_video(filename)

# ==================== Routes ====================

@app.route('/')
def index():
    """首页 - 选择模式"""
    return render_template('index.html')

@app.route('/mode/<mode>')
def mode_select(mode):
    """根据选择的模式返回相应页面"""
    if mode == 'video' or mode == 'video_optimized':
        # 统一使用优化版本（客户端渲染）
        return render_template('video_optimized.html')
    elif mode == 'upload':
        return render_template('upload.html')
    elif mode == 'upload_video':
        return render_template('upload_video.html')
    elif mode == 'upload_unified':
        return render_template('upload_unified.html')
    else:
        return redirect('/')

@app.route('/video_feed')
def video_feed():
    """实时视频流"""
    return Response(monitor.generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/api/config', methods=['GET', 'POST'])
def config_api():
    """获取或修改配置参数"""
    if request.method == 'GET':
        return jsonify({
            'confidence_threshold': monitor.confidence_threshold,
            'detection_interval': monitor.detection_interval,
            'model_info': {
                'model': 'yolov8n (nano) - 速度快，精度中等',
                'models_available': [
                    'yolov8n.pt (nano) - 最快，精度最低',
                    'yolov8s.pt (small) - 更好的精度',
                    'yolov8m.pt (medium) - 很好的精度，较慢',
                    'yolov8l.pt (large) - 最高精度，最慢',
                ]
            }
        })
    
    elif request.method == 'POST':
        data = request.get_json()
        
        # 修改置信度阈值
        if 'confidence_threshold' in data:
            new_conf = float(data['confidence_threshold'])
            if 0.1 <= new_conf <= 0.9:
                monitor.confidence_threshold = new_conf
                print(f"[配置] 置信度已更新为: {new_conf}", flush=True)
                return jsonify({'success': True, 'message': f'置信度已更新为 {new_conf}'})
            else:
                return jsonify({'success': False, 'error': '置信度必须在 0.1-0.9 之间'}), 400
        
        return jsonify({'success': False, 'error': '无有效参数'}), 400

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """获取实时检测统计"""
    with monitor.lock:
        return jsonify({
            'person_count': monitor.person_count,
            'density': monitor.density,
            'inference_time': monitor.inference_time,
            'confidence_threshold': monitor.confidence_threshold,
            'frame_count': monitor.frame_count
        })

@app.route('/api/detections', methods=['GET'])
def get_detections():
    """获取最新的检测结果 - 用于浏览器端可视化
    
    返回格式:
    {
        'person_count': 人数,
        'density': 密度,
        'inference_time': 推理耗时(秒),
        'detections': [
            {'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2, 'confidence': conf},
            ...
        ],
        'frame_info': {
            'width': 宽度,
            'height': 高度,
            'frame_count': 帧数
        }
    }
    """
    with monitor.lock:
        detections_list = []
        
        # 转换 YOLO 检测结果为坐标数据
        if len(monitor.detections) > 0:
            for detection in monitor.detections:
                x1, y1, x2, y2 = detection.xyxy[0]
                conf = detection.conf[0]
                detections_list.append({
                    'x1': float(x1),
                    'y1': float(y1),
                    'x2': float(x2),
                    'y2': float(y2),
                    'confidence': float(conf)
                })
        
        return jsonify({
            'person_count': monitor.person_count,
            'density': monitor.density,
            'inference_time': monitor.inference_time,
            'detections': detections_list,
            'frame_info': {
                'width': 1280,
                'height': 720,
                'frame_count': monitor.frame_count
            },
            'timestamp': datetime.now().isoformat()
        })

@app.route('/upload', methods=['POST'])
def upload_file():
    """处理上传的照片 [使用独立模型，不影响实时视频]"""
    if 'file' not in request.files:
        return jsonify({'error': '没有文件'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': '没有选择文件'}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # 使用专用的上传模型处理图像 - 独立的资源，不与实时视频竞争
        result_frame, person_count, density = monitor.process_uploaded_image(filepath)
        
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

@app.route('/download_video/<filename>')
def download_video(filename):
    """下载处理后的视频"""
    try:
        return send_from_directory(app.config['OUTPUT_FOLDER'], filename, as_attachment=True)
    except:
        return jsonify({'error': '文件不存在'}), 404

@app.route('/get_processed_video/<filename>')
def get_processed_video(filename):
    """获取处理后的视频用于播放"""
    try:
        return send_from_directory(app.config['OUTPUT_FOLDER'], filename)
    except:
        return jsonify({'error': '文件不存在'}), 404

@app.route('/upload_video', methods=['POST'])
def upload_video():
    """处理上传的视频 [使用独立模型，不影响实时视频]"""
    if 'file' not in request.files:
        return jsonify({'error': '没有文件'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': '没有选择文件'}), 400
    
    if file and allowed_video(file.filename):
        filename = secure_filename(file.filename)
        video_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(video_path)
        
        # 使用专用的上传模型处理视频 - 独立的资源，不与实时视频竞争
        output_filename = f'result_video_{datetime.now().strftime("%Y%m%d_%H%M%S")}.avi'
        output_path = os.path.join(app.config['OUTPUT_FOLDER'], output_filename)
        
        try:
            result = monitor.process_uploaded_video(video_path, output_path)
            
            if result is None:
                return jsonify({'error': '无法读取视频'}), 400
            
            return jsonify({
                'success': True,
                'video_url': f'/get_processed_video/{os.path.basename(result["output_file"])}',
                'download_url': f'/download_video/{os.path.basename(result["output_file"])}',
                'frames_analyzed': result['total_frames'],
                'total_frames': result['total_frames'],
                'avg_people': float(result['avg_count']),
                'max_people': int(result['max_count']),
                'min_people': int(result['min_count'])
            })
        except Exception as e:
            return jsonify({'error': f'处理视频失败: {str(e)}'}), 400
    
    return jsonify({'error': '文件格式不支持'}), 400


if __name__ == '__main__':
    print("=" * 50)
    print("启动 Flask 服务器")
    print("=" * 50)
    print("在浏览器中打开: http://localhost:5000")
    print("=" * 50)
    try:
        app.run(host='0.0.0.0', port=5000, debug=False)
    except KeyboardInterrupt:
        print("\n正在关闭...")
        monitor.stop_detection_thread()
        print("✓ 已安全关闭")

