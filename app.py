import cv2
import numpy as np
from ultralytics import YOLO
from collections import deque
from datetime import datetime, timedelta
from flask import Flask, render_template, Response, request, jsonify, send_from_directory
import threading
import os
from werkzeug.utils import secure_filename
from pathlib import Path

# 导入数据库模块
from database import get_db, init_db

# 导入配置
try:
    from config import (
        FLASK_CONFIG, CAMERA_CONFIG, MODEL_CONFIG, 
        STATS_CONFIG, SECURITY_CONFIG, get_startup_info, print_routes_info
    )
except ImportError:
    print("[警告] 无法导入config.py，使用默认配置")
    FLASK_CONFIG = {'DEBUG': False, 'HOST': '0.0.0.0', 'PORT': 5000, 'THREADED': True}
    CAMERA_CONFIG = {'enabled': True, 'camera_id': 0, 'width': 1280, 'height': 720}
    MODEL_CONFIG = {'enabled': True, 'model_name': 'yolov8n.pt', 'confidence_threshold': 0.2}
    STATS_CONFIG = {'history_maxlen': 100, 'update_interval': 2000}
    SECURITY_CONFIG = {'max_file_size': 500 * 1024 * 1024, 'allowed_image_extensions': {'png', 'jpg', 'jpeg'}}

app = Flask(__name__)

# 配置文件夹
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
OUTPUT_FOLDER = os.path.join(BASE_DIR, 'processed_videos')
TEMPLATE_FOLDER = os.path.join(BASE_DIR, 'templates')
STATIC_FOLDER = os.path.join(BASE_DIR, 'static')

ALLOWED_EXTENSIONS = SECURITY_CONFIG.get('allowed_image_extensions', {'png', 'jpg', 'jpeg', 'gif', 'bmp'})
VIDEO_EXTENSIONS = SECURITY_CONFIG.get('allowed_video_extensions', {'mp4', 'avi', 'mov', 'mkv', 'flv', 'wmv'})

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER
app.config['MAX_CONTENT_LENGTH'] = SECURITY_CONFIG.get('max_file_size', 500 * 1024 * 1024)

# 重新配置模板和静态文件夹
app.template_folder = TEMPLATE_FOLDER
app.static_folder = STATIC_FOLDER

class CrowdDensityMonitor:
    """人群密度监测器 - 集成YOLO8和实时数据统计"""
    
    def __init__(self, model_name='yolov8n.pt', camera_id=0, width=1280, height=720, conf=0.2):
        """初始化YOLO模型和摄像头
        
        Args:
            model_name: YOLO模型文件名 (yolov8n/s/m/l/x.pt)
            camera_id: 摄像头ID
            width: 输入分辨率宽度 (推荐: 1280)
            height: 输入分辨率高度 (推荐: 720)
            conf: 置信度阈值 (默认: 0.1，范围: 0.1-0.9)
        """
        # 模型初始化
        self.model = YOLO(model_name)
        self.upload_model = YOLO(model_name)
        
        # 检测参数
        self.confidence_threshold = conf
        self.cap = cv2.VideoCapture(camera_id)
        self.cap.set(cv2.CAP_PROP_FPS, 30)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        
        actual_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        # 检测结果
        self.person_count = 0
        self.density = 0
        self.detections = []
        self.frame_count = 0
        self.inference_time = 0
        
        # 实时数据统计
        self.density_history = deque(maxlen=100)
        self.person_count_history = deque(maxlen=100)
        self.timestamp_history = deque(maxlen=100)
        
        # 线程锁
        self.lock = threading.Lock()
        
        # 视频流参数
        self.current_frame = None
        self.frame_for_detection = None
        self.detection_interval = 3
        
        # 后台检测线程
        self.detection_thread = None
        self.stop_detection = False
        
        # 统计数据（按时段）
        self.hourly_stats = {}  # 按小时统计
        self.daily_stats = []   # 日统计
        
        # 数据库相关
        self.db = None
        self.last_db_save_time = datetime.now()
        self.db_save_interval = 60  # 每1分钟保存一次（60秒）- 建议频率：1分钟最优，足以捕捉人流变化且不过度记录
        
        # 初始化数据库
        try:
            self.db = init_db()
            print("[✓] 数据库已初始化")
        except Exception as e:
            print(f"[警告] 数据库初始化失败: {e}")
            self.db = None
        
        print("=" * 50)
        print("人群密度监测器初始化完成")
        print(f"  - 分辨率: {actual_width}x{actual_height}")
        print(f"  - 模型: {model_name}")
        print(f"  - 置信度阈值: {self.confidence_threshold}")
        print("=" * 50)
    
    def start_detection_thread(self):
        """启动后台检测线程"""
        self.stop_detection = False
        self.detection_thread = threading.Thread(target=self._detection_worker, daemon=True)
        self.detection_thread.start()
        print("[✓] 后台检测线程已启动")
    
    def stop_detection_thread(self):
        """停止后台检测线程"""
        self.stop_detection = True
        if self.detection_thread:
            self.detection_thread.join(timeout=2)
    
    def _detection_worker(self):
        """后台检测工作线程"""
        import time
        detection_count = 0
        
        while not self.stop_detection:
            with self.lock:
                frame_to_detect = self.frame_for_detection
            
            if frame_to_detect is not None:
                try:
                    start_time = time.time()
                    results = self.model(frame_to_detect, classes=0, conf=self.confidence_threshold, verbose=False)
                    self.inference_time = time.time() - start_time
                    detections = results[0].boxes
                    
                    person_count = len(detections)
                    frame_area = frame_to_detect.shape[0] * frame_to_detect.shape[1]
                    density = person_count / (frame_area / 10000)
                    
                    # 更新检测结果和统计数据
                    with self.lock:
                        self.detections = detections
                        self.person_count = person_count
                        self.density = density
                        self.density_history.append(density)
                        self.person_count_history.append(person_count)
                        self.timestamp_history.append(datetime.now())
                        
                        # 更新小时统计
                        now = datetime.now()
                        hour_key = now.strftime("%H:00")
                        if hour_key not in self.hourly_stats:
                            self.hourly_stats[hour_key] = {
                                'count': 0,
                                'total_people': 0,
                                'max_people': 0,
                                'min_people': float('inf')
                            }
                        
                        stats = self.hourly_stats[hour_key]
                        stats['count'] += 1
                        stats['total_people'] += person_count
                        stats['max_people'] = max(stats['max_people'], person_count)
                        stats['min_people'] = min(stats['min_people'], person_count)
                        
                        # 定期保存到数据库 (每1分钟)
                        if (datetime.now() - self.last_db_save_time).total_seconds() >= self.db_save_interval:
                            if self.db:
                                try:
                                    # 只在营业时间内保存数据 (7:00 - 23:55)
                                    if 7 <= now.hour < 24:
                                        # 保存当前时间的数据 (仅保存：人数、时间、星期几)
                                        weekday = now.weekday()
                                        result = self.db.add_record(now, person_count, weekday)
                                        self.last_db_save_time = now
                                        # 每次保存时打印日志
                                        if detection_count % 100 == 0:
                                            print(f"[数据库] 已保存数据: {person_count}人 @ {now.strftime('%Y-%m-%d %H:%M:%S')}")
                                except Exception as e:
                                    print(f"[警告] 数据库保存失败: {e}")
                    
                    detection_count += 1
                    if detection_count % 10 == 0:
                        print(f"[检测] 已处理{detection_count}次 | 最新: {person_count}人 | 耗时: {self.inference_time*1000:.0f}ms")
                
                except Exception as e:
                    print(f"[警告] 检测失败: {e}")
            
            time.sleep(0.01)
    
    def generate_frames(self):
        """生成视频流 - 带有检测框和信息绘制"""
        detection_frame_counter = 0
        
        while True:
            ret, frame = self.cap.read()
            if not ret:
                print("[视频流] 视频流结束")
                break
            
            # 每隔N帧提供一个给检测线程
            if detection_frame_counter % self.detection_interval == 0:
                with self.lock:
                    self.frame_for_detection = frame.copy()
            
            detection_frame_counter += 1
            self.frame_count += 1
            
            # 在视频帧上绘制检测结果
            display_frame = frame.copy()
            with self.lock:
                detections = self.detections
                person_count = self.person_count
                density = self.density
                inference_time = self.inference_time
            
            # 绘制检测框
            for detection in detections:
                x1, y1, x2, y2 = detection.xyxy[0]
                cv2.rectangle(display_frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
            
            # 绘制文字信息
            cv2.putText(display_frame, f'People Count: {person_count}', (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.putText(display_frame, f'Density: {density:.2f}', (10, 70),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.putText(display_frame, f'Time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}', (10, 110),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            cv2.putText(display_frame, f'Inference: {inference_time*1000:.0f}ms', (10, 150),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            
            # 编码为JPEG
            ret, buffer = cv2.imencode('.jpg', display_frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
            frame_data = buffer.tobytes()
            
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_data + b'\r\n')
    
    def process_uploaded_image(self, image_path):
        """处理上传的图片"""
        frame = cv2.imread(image_path)
        if frame is None:
            return None, 0, 0
        
        if frame.shape[0] > 1080 or frame.shape[1] > 1920:
            frame = cv2.resize(frame, (960, 720))
        
        try:
            import time
            start_time = time.time()
            results = self.upload_model(frame, classes=0, conf=self.confidence_threshold, verbose=False)
            inference_time = time.time() - start_time
            detections = results[0].boxes
            
            person_count = len(detections)
            frame_area = frame.shape[0] * frame.shape[1]
            density = person_count / (frame_area / 10000)
            
            print(f"[上传图片] 检测完成 | {person_count}人 | 耗时: {inference_time*1000:.0f}ms")
            
            display_frame = frame.copy()
            for detection in detections:
                x1, y1, x2, y2 = detection.xyxy[0]
                cv2.rectangle(display_frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
            
            return display_frame, person_count, density
        
        except Exception as e:
            print(f"[上传图片] 检测失败: {e}")
            return None, 0, 0
    
    def get_realtime_stats(self):
        """获取实时统计数据"""
        with self.lock:
            if len(self.person_count_history) == 0:
                return {
                    "pickup_time": "计算中...",
                    "crowd_level": "无数据",
                    "crowd_range": "0人"
                }
            
            current_count = self.person_count
            
            # 根据人数估算取餐时间
            if current_count < 10:
                pickup_time = "2-5分钟"
                crowd_level = "低"
            elif current_count < 20:
                pickup_time = "5-10分钟"
                crowd_level = "中等"
            elif current_count < 30:
                pickup_time = "10-30分钟"
                crowd_level = "高"
            else:
                pickup_time = "30分钟以上"
                crowd_level = "非常高"
            
            return {
                "pickup_time": pickup_time,
                "crowd_level": crowd_level,
                "crowd_range": f"约{current_count}人（当前）"
            }
    
    def get_history_stats(self):
        """获取历史统计数据"""
        with self.lock:
            # 周人流量（最近7天）
            if len(self.person_count_history) > 0:
                avg_count = int(np.mean(list(self.person_count_history)))
            else:
                avg_count = 0
            weekly_flow = [avg_count] * 7
            
            # 高峰时段统计
            peak_times = {}
            for hour_key in sorted(self.hourly_stats.keys()):
                stats = self.hourly_stats[hour_key]
                avg = stats['total_people'] / stats['count'] if stats['count'] > 0 else 0
                peak_times[hour_key] = int(avg)
            
            if not peak_times:
                peak_times = {"09:00": 20, "12:00": 60, "18:00": 40}
            
            # 热力图数据
            heatmap = [
                [10, 20, 30, 40],
                [15, 25, 35, 45],
                [20, 30, 40, 50]
            ]
            
            return {
                "weekly_flow": weekly_flow,
                "peak_times": peak_times,
                "heatmap": heatmap
            }


# 全局监测器实例
monitor = None

def init_monitor():
    """初始化监测器"""
    global monitor
    try:
        monitor = CrowdDensityMonitor(
            model_name='yolov8n.pt' if os.path.exists('yolov8n.pt') else 'yolov8n.pt',
            camera_id=0,
            width=1280,
            height=720,
            conf=0.2
        )
        monitor.start_detection_thread()
    except Exception as e:
        print(f"[错误] 无法初始化监测器: {e}")
        print("[信息] 将使用模拟数据")
        monitor = None


def allowed_file(filename):
    """检查文件是否被允许"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def allowed_video(filename):
    """检查视频文件是否被允许"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in VIDEO_EXTENSIONS


# ========== 路由定义 ==========

@app.route('/')
def index():
    """首页 - 实时取餐时间预估"""
    if monitor:
        data = monitor.get_realtime_stats()
    else:
        data = {
            "pickup_time": "8-12分钟",
            "crowd_level": "中等",
            "crowd_range": "约35-50人"
        }
    return render_template('index.html', data=data)


@app.route('/history')
def history():
    """历史数据页面"""
    if monitor:
        data = monitor.get_history_stats()
    else:
        data = {
            "weekly_flow": [30, 45, 60, 50, 70, 80, 65],
            "peak_times": {"早上": 20, "中午": 60, "晚上": 40},
            "heatmap": [
                [10, 20, 30, 40],
                [15, 25, 35, 45],
                [20, 30, 40, 50]
            ]
        }
    return render_template('history.html', data=data)


@app.route('/api/time')
def api_time():
    """获取服务器当前时间 API"""
    now = datetime.now()
    return jsonify({
        'timestamp': now.isoformat(),
        'formatted': now.strftime('%Y-%m-%d %H:%M:%S'),
        'hour': now.hour,
        'minute': now.minute,
        'second': now.second,
        'weekday': now.weekday()
    })


@app.route('/api/realtime')
def api_realtime():
    """获取实时数据 API"""
    if monitor:
        return jsonify(monitor.get_realtime_stats())
    else:
        return jsonify({
            "pickup_time": "8-12分钟",
            "crowd_level": "中等",
            "crowd_range": "约35-50人"
        })


@app.route('/api/history')
def api_history():
    """获取历史数据 API"""
    if monitor:
        return jsonify(monitor.get_history_stats())
    else:
        return jsonify({
            "weekly_flow": [30, 45, 60, 50, 70, 80, 65],
            "peak_times": {"早上": 20, "中午": 60, "晚上": 40},
            "heatmap": [
                [10, 20, 30, 40],
                [15, 25, 35, 45],
                [20, 30, 40, 50]
            ]
        })


@app.route('/api/weekday/<int:weekday>')
def api_weekday_data(weekday):
    """获取指定星期几的历史数据
    
    weekday: 0=Monday, 1=Tuesday, ..., 6=Sunday
    返回该星期几所有日期的人数随时间的变化
    """
    try:
        db = get_db()
        if not db:
            return jsonify({'error': '数据库未初始化'}), 503
        
        if weekday < 0 or weekday > 6:
            return jsonify({'error': '星期几参数错误，应为0-6'}), 400
        
        # 获取该星期几的所有记录
        records = db.get_records_by_weekday(weekday)
        
        if not records:
            return jsonify({
                'weekday': weekday,
                'weekday_name': ['周一', '周二', '周三', '周四', '周五', '周六', '周日'][weekday],
                'records_count': 0,
                'data': [],
                'stats': {
                    'avg_people': 0,
                    'max_people': 0,
                    'min_people': 0
                }
            })
        
        # 获取统计数据
        stats = db.get_weekday_stats(weekday)
        
        # 格式化记录数据，按时间排序
        data = []
        for record in records:
            data.append({
                'timestamp': record['timestamp'],
                'person_count': record['person_count'],
                'time': record['timestamp'].split('T')[1][:5] if 'T' in record['timestamp'] else ''
            })
        
        return jsonify({
            'weekday': weekday,
            'weekday_name': ['周一', '周二', '周三', '周四', '周五', '周六', '周日'][weekday],
            'records_count': len(records),
            'data': data,
            'stats': {
                'avg_people': round(stats['avg_people'], 1) if stats else 0,
                'max_people': stats['max_people'] if stats else 0,
                'min_people': stats['min_people'] if stats else 0
            }
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/db/stats')
def api_db_stats():
    """获取数据库统计信息"""
    try:
        db = get_db()
        if not db:
            return jsonify({'error': '数据库未初始化'}), 503
        
        record_count = db.get_record_count()
        db_size = db.get_database_size()
        
        return jsonify({
            'db_path': db.db_path,
            'record_count': record_count,
            'db_size_mb': round(db_size, 2),
            'db_status': 'normal' if record_count > 0 else 'empty'
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500



@app.route('/api/stats')
def get_stats():
    """获取实时检测统计"""
    if monitor:
        with monitor.lock:
            return jsonify({
                'person_count': monitor.person_count,
                'density': monitor.density,
                'inference_time': monitor.inference_time,
                'confidence_threshold': monitor.confidence_threshold,
                'frame_count': monitor.frame_count
            })
    else:
        return jsonify({
            'person_count': 0,
            'density': 0,
            'inference_time': 0,
            'confidence_threshold': 0.2,
            'frame_count': 0
        })


@app.route('/video_feed')
def video_feed():
    """实时视频流"""
    if monitor:
        return Response(monitor.generate_frames(),
                        mimetype='multipart/x-mixed-replace; boundary=frame')
    else:
        # 返回占位符
        return jsonify({'error': '摄像头未初始化'}), 503


@app.route('/upload', methods=['POST'])
def upload_file():
    """处理上传的照片"""
    if monitor is None:
        return jsonify({'error': '检测器未初始化'}), 503
    
    if 'file' not in request.files:
        return jsonify({'error': '没有文件'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': '没有选择文件'}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        result_frame, person_count, density = monitor.process_uploaded_image(filepath)
        
        if result_frame is None:
            return jsonify({'error': '无法读取图像'}), 400
        
        result_filename = f'result_{datetime.now().strftime("%Y%m%d_%H%M%S")}.jpg'
        result_path = os.path.join(app.config['UPLOAD_FOLDER'], result_filename)
        cv2.imwrite(result_path, result_frame)
        
        return jsonify({
            'success': True,
            'person_count': int(person_count),
            'density': float(density),
            'image_url': f'/static/{result_filename}'
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
    print("=" * 70)
    print("启动集成 Flask 服务器 (MC + Frontend)")
    print("=" * 70)
    print(f"模板文件夹: {TEMPLATE_FOLDER}")
    print(f"静态文件夹: {STATIC_FOLDER}")
    
    # 尝试打印配置信息
    try:
        print_routes_info()
        startup_info = get_startup_info()
        print("\n访问地址:")
        for key, url in startup_info.items():
            print(f"  - {key:15}: {url}")
    except:
        print("\n访问地址:")
        print(f"  - 主页: http://localhost:5000")
        print(f"  - 历史数据: http://localhost:5000/history")
    
    print("=" * 70)
    
    try:
        init_monitor()
        port = FLASK_CONFIG.get('PORT', 5000)
        host = FLASK_CONFIG.get('HOST', '0.0.0.0')
        debug = FLASK_CONFIG.get('DEBUG', False)
        threaded = FLASK_CONFIG.get('THREADED', True)
        
        app.run(host=host, port=port, debug=debug, threaded=threaded)
    except KeyboardInterrupt:
        print("\n正在关闭...")
        if monitor:
            monitor.stop_detection_thread()
        print("✓ 已安全关闭")
