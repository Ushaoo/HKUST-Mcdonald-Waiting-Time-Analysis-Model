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
    def __init__(self, model_name='yolov8n.pt', camera_id=0, width=1280, height=720):
        """Initialize YOLO model and camera
        
        Args:
            model_name: YOLO模型文件名
            camera_id: 摄像头ID
            width: 输入分辨率宽度 (推荐: 1280)
            height: 输入分辨率高度 (推荐: 720)
        """
        self.model = YOLO(model_name)
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
                    results = self.model(frame_to_detect, classes=0, conf=0.5, verbose=False)
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
        """生成视频流 - 专门用于视频播放，不做任何检测"""
        detection_frame_counter = 0
        
        print("[视频流] 开始生成视频帧流...", flush=True)
        
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
            
            # 获取最新的检测结果（来自后台线程）
            with self.lock:
                person_count = self.person_count
                density = self.density
                detections = self.detections
            
            # 绘制信息
            display_frame = self.draw_info(frame, person_count, density)
            
            # 绘制检测框
            if len(detections) > 0:
                for detection in detections:
                    x1, y1, x2, y2 = detection.xyxy[0]
                    cv2.rectangle(display_frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
            
            # 编码为JPEG（质量70以减少带宽）
            ret, buffer = cv2.imencode('.jpg', display_frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
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

# Initialize monitor with high resolution for better detection
monitor = CrowdDensityMonitor(width=1280, height=720)  # 1280x720 for better long-range detection
monitor.start_detection_thread()  # 启动后台检测线程

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def allowed_video(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in VIDEO_EXTENSIONS

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
    elif mode == 'upload_video':
        return render_template('upload_video.html')
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
    """处理上传的视频"""
    if 'file' not in request.files:
        return jsonify({'error': '没有文件'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': '没有选择文件'}), 400
    
    if file and allowed_video(file.filename):
        filename = secure_filename(file.filename)
        video_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(video_path)
        
        # 处理视频
        try:
            result_path, frames_analyzed, total_frames, people_data = process_video(video_path, monitor)
            
            if result_path is None:
                return jsonify({'error': '无法读取视频'}), 400
            
            return jsonify({
                'success': True,
                'video_url': f'/get_processed_video/{os.path.basename(result_path)}',
                'download_url': f'/download_video/{os.path.basename(result_path)}',
                'frames_analyzed': frames_analyzed,
                'total_frames': total_frames,
                'avg_people': float(people_data['avg']) if people_data['avg'] > 0 else 0,
                'max_people': int(people_data['max']),
                'min_people': int(people_data['min'])
            })
        except Exception as e:
            return jsonify({'error': f'处理视频失败: {str(e)}'}), 400
    
    return jsonify({'error': '文件格式不支持'}), 400

def process_video(video_path, monitor):
    """处理视频文件，返回处理后的视频路径和统计数据"""
    print(f"\n[视频处理开始] 文件: {video_path}", flush=True)
    start_time = datetime.now()
    
    cap = cv2.VideoCapture(video_path)
    
    if not cap.isOpened():
        print(f"[错误] 无法打开视频文件: {video_path}", flush=True)
        return None, 0, 0, {'avg': 0, 'max': 0, 'min': 0}
    
    # 获取视频属性
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    print(f"[视频信息] 分辨率: {width}x{height}, FPS: {fps}, 总帧数: {total_frames}", flush=True)
    
    # 验证和调整参数
    if fps <= 0:
        print(f"[警告] FPS无效({fps})，设置为30", flush=True)
        fps = 30
    
    if width <= 0 or height <= 0:
        print(f"[错误] 无效的分辨率: {width}x{height}", flush=True)
        cap.release()
        return None, 0, 0, {'avg': 0, 'max': 0, 'min': 0}
    
    # 确保分辨率是偶数（某些编码器需要）
    if width % 2 != 0:
        width = width - 1
    if height % 2 != 0:
        height = height - 1
    print(f"[调整后] 分辨率: {width}x{height}, FPS: {fps}", flush=True)
    
    if total_frames == 0:
        print(f"[警告] 无法获取视频总帧数，尝试连续读取", flush=True)
    
    # 设置输出视频 - 保存到本地 processed_videos 目录
    # 尝试多种编码格式
    output_filename = f'result_video_{datetime.now().strftime("%Y%m%d_%H%M%S")}.avi'
    output_path = os.path.join(app.config['OUTPUT_FOLDER'], output_filename)
    
    print(f"[输出设置] 输出文件: {output_filename}", flush=True)
    print(f"[输出路径] {output_path}", flush=True)
    
    # 使用MJPEG编码（更稳定）
    fourcc = cv2.VideoWriter_fourcc(*'MJPG')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    if not out.isOpened():
        print(f"[警告] MJPG编码失败，尝试XVID编码", flush=True)
        output_filename = f'result_video_{datetime.now().strftime("%Y%m%d_%H%M%S")}.avi'
        output_path = os.path.join(app.config['OUTPUT_FOLDER'], output_filename)
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        
        if not out.isOpened():
            print(f"[警告] XVID编码失败，尝试FFV1编码", flush=True)
            output_filename = f'result_video_{datetime.now().strftime("%Y%m%d_%H%M%S")}.avi'
            output_path = os.path.join(app.config['OUTPUT_FOLDER'], output_filename)
            fourcc = cv2.VideoWriter_fourcc(*'FFV1')
            out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
            
            if not out.isOpened():
                print(f"[错误] 所有编码格式都失败了", flush=True)
                cap.release()
                return None, 0, 0, {'avg': 0, 'max': 0, 'min': 0}
    
    print(f"[编码器] 成功使用编码器创建写入器", flush=True)
    
    frame_count = 0
    people_counts = []
    analyzed_frames = 0
    frame_skip = 5  # 每5帧处理一次，加快速度
    write_errors = 0
    
    print(f"[处理设置] 每{frame_skip}帧检测一次", flush=True)
    print(f"[开始处理] 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", flush=True)
    
    while True:
        ret, frame = cap.read()
        if not ret:
            print(f"[读取结束] 视频读取完毕，总共读取{frame_count}帧", flush=True)
            break
        
        # 调整帧大小到指定分辨率（以防原始分辨率有问题）
        if frame.shape[1] != width or frame.shape[0] != height:
            frame = cv2.resize(frame, (width, height))
        
        # 每frame_skip帧检测一次
        if frame_count % frame_skip == 0:
            try:
                detections = monitor.detect_people(frame)
                person_count, density = monitor.calculate_density(detections, frame.shape)
                people_counts.append(person_count)
                analyzed_frames += 1
                
                # 每50帧分析打印一次进度
                if analyzed_frames % 50 == 0:
                    progress_percent = (frame_count / max(total_frames, frame_count + 1)) * 100
                    print(f"[处理进度] 帧数: {frame_count}/{total_frames if total_frames > 0 else '?'} ({progress_percent:.1f}%) - 已分析: {analyzed_frames} - 当前人数: {person_count}", flush=True)
            except Exception as e:
                print(f"[警告] 第{frame_count}帧检测失败: {str(e)}", flush=True)
                person_count = people_counts[-1] if people_counts else 0
                analyzed_frames += 1
        else:
            if people_counts:
                person_count = people_counts[-1]
            else:
                person_count = 0
            density = person_count / (frame.shape[0] * frame.shape[1] / 10000)
            detections = []
        
        # 绘制信息
        display_frame = monitor.draw_info(frame, person_count, density)
        
        # 绘制检测框
        if len(detections) > 0:
            for detection in detections:
                x1, y1, x2, y2 = detection.xyxy[0]
                cv2.rectangle(display_frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
        
        # 尝试写入帧（注意：某些编码器的write()可能返回False但实际已写入）
        success = out.write(display_frame)
        if not success:
            write_errors += 1
            if write_errors == 1:
                print(f"[注意] 帧写入返回False（可能是OpenCV问题，但文件可能正确保存）", flush=True)
        
        frame_count += 1
    
    cap.release()
    out.release()
    
    print(f"[释放资源] 视频捕获和写入器已释放", flush=True)
    
    # 检查输出文件是否存在并有内容
    if os.path.exists(output_path):
        file_size = os.path.getsize(output_path)
        print(f"[成功] 输出文件大小: {file_size} 字节", flush=True)
    else:
        print(f"[错误] 输出文件未创建: {output_path}", flush=True)
    
    if write_errors > 0:
        print(f"[信息] write()函数返回失败{write_errors}次（这通常不是真正的错误）", flush=True)
    
    # 计算统计数据
    if people_counts:
        stats = {
            'avg': sum(people_counts) / len(people_counts),
            'max': max(people_counts),
            'min': min(people_counts)
        }
    else:
        stats = {'avg': 0, 'max': 0, 'min': 0}
    
    elapsed_time = datetime.now() - start_time
    print(f"[处理完成] 耗时: {elapsed_time.total_seconds():.2f}秒", flush=True)
    print(f"[统计结果] 平均人数: {stats['avg']:.2f}, 最大: {stats['max']}, 最小: {stats['min']}", flush=True)
    print(f"[本地文件] {output_path}", flush=True)
    
    return output_path, analyzed_frames, total_frames, stats

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

