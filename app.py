import cv2
import numpy as np
from ultralytics import YOLO
from collections import deque
from datetime import datetime, timedelta
from flask import Flask, render_template, Response, request, jsonify, send_from_directory
import threading
import time
import os
import signal
import atexit
from werkzeug.utils import secure_filename
from pathlib import Path

# Import Database module
from database import get_db, init_db

# Import configuration
try:
    from config import (
        FLASK_CONFIG, CAMERA_CONFIG, MODEL_CONFIG, 
        STATS_CONFIG, SECURITY_CONFIG, get_startup_info, print_routes_info
    )
except ImportError:
    print("[WARNING] Unable to import config.py, using default configuration")
    FLASK_CONFIG = {'DEBUG': False, 'HOST': '0.0.0.0', 'PORT': 5000, 'THREADED': True}
    CAMERA_CONFIG = {'enabled': True, 'camera_id': 0, 'width': 1280, 'height': 720}
    MODEL_CONFIG = {'enabled': True, 'model_name': 'yolov8n.pt', 'confidence_threshold': 0.2}
    STATS_CONFIG = {'history_maxlen': 100, 'update_interval': 2000}
    SECURITY_CONFIG = {'max_file_size': 500 * 1024 * 1024, 'allowed_image_extensions': {'png', 'jpg', 'jpeg'}}

app = Flask(__name__)

# Configure folders
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

# Reconfigure template and static folders
app.template_folder = TEMPLATE_FOLDER
app.static_folder = STATIC_FOLDER

# ==================== Data Smoothing Function ====================
def smooth_data(data, window_size=5):
    """
    Simple moving average smoothing for data
    
    Args:
        data: Original data list
        window_size: Moving window size (default 5, meaning average of 2 data points before and after)
    
    Returns:
        Smoothed data list
    """
    if len(data) < window_size:
        return data
    
    smoothed = []
    half_window = window_size // 2
    
    for i in range(len(data)):
        # Determine window range
        start = max(0, i - half_window)
        end = min(len(data), i + half_window + 1)
        
        # Calculate average within the window
        window_avg = sum(data[start:end]) / (end - start)
        smoothed.append(int(round(window_avg)))
    
    return smoothed

# ==================== Classes and Routes Definitions ====================

class CrowdDensityMonitor:
    """Crowd Density Monitor - Integrates YOLO8 and Real-time Data Statistics"""
    
    def __init__(self, model_name='yolov8n.pt', camera_id=0, width=1280, height=720, conf=0.2):
        """Initialize YOLO model and camera
        
        Args:
            model_name: YOLO model filename (yolov8n/s/m/l/x.pt)
            camera_id: Camera ID
            width: Input resolution width (recommended: 1280)
            height: Input resolution height (recommended: 720)
            conf: Confidence threshold (default: 0.1, range: 0.1-0.9)
        """
        # Model initialization
        self.model = YOLO(model_name)
        self.upload_model = YOLO(model_name)
        
        # Detection parameters
        self.confidence_threshold = conf
        self.cap = cv2.VideoCapture(camera_id)
        self.cap.set(cv2.CAP_PROP_FPS, 30)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        
        actual_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        # Detection results
        self.person_count = 0
        self.density = 0
        self.detections = []
        self.frame_count = 0
        self.inference_time = 0
        
        # Real-time data statistics
        self.density_history = deque(maxlen=100)
        self.person_count_history = deque(maxlen=100)
        self.timestamp_history = deque(maxlen=100)
        
        # Thread lock
        self.lock = threading.Lock()
        
        # Frame for detection
        self.current_frame = None
        self.frame_for_detection = None
        self.detection_interval = 3
        
        # Background detection thread
        self.detection_thread = None
        self.stop_detection = False
        
        # Statistics data (by time period)
        self.hourly_stats = {}  # Hourly statistics
        self.daily_stats = []   # Daily statistics
        
        # Database related
        self.db = None
        self.last_db_save_time = datetime.now()
        self.db_save_interval = 60  
        
        # GPIO related - Button and LED
        # First set (Pin 31 button, Pin 13 LED): Data save + LED blink
        self.button_thread = None
        self.stop_button = False
        self.button_state = None
        self.last_button_press = 0
        self.button_debounce_time = 0.5  # Debounce delay (seconds)
        
        # Second set (Pin 29 button, Pin 11 LED): Drawing control
        self.button2_thread = None
        self.stop_button2 = False
        self.last_button2_press = 0
        self.button2_debounce_time = 0.5  # Debounce delay (seconds)
        self.drawing_enabled = True  # Default: drawing is enabled
        
        # GPIO initialization
        try:
            import Hobot.GPIO as GPIO
            self.GPIO = GPIO
            
            # First set pins
            self.LED_PIN = 13       # First set LED
            self.BUTTON_PIN = 31    # First set button
            
            # Second set pins
            self.BUTTON2_PIN = 29   # Second set button
            self.LED2_PIN = 11      # Second set LED
            
            GPIO.setmode(GPIO.BOARD)
            
            # Setup first set
            GPIO.setup(self.LED_PIN, GPIO.OUT)
            GPIO.setup(self.BUTTON_PIN, GPIO.IN)
            GPIO.output(self.LED_PIN, GPIO.LOW)  # Initialize LED to off
            
            # Setup second set
            GPIO.setup(self.BUTTON2_PIN, GPIO.IN)
            GPIO.setup(self.LED2_PIN, GPIO.OUT)
            GPIO.output(self.LED2_PIN, GPIO.HIGH)  # Initialize LED on (drawing enabled)
            
            print("[OK] GPIO initialized")
            print(f"  - Set 1: Button Pin 31, LED Pin 13 (Data save + LED blink)")
            print(f"  - Set 2: Button Pin 29, LED Pin 11 (Drawing control, default ON)")
        except ImportError:
            print("[WARNING] Hobot.GPIO not installed, GPIO features disabled")
            self.GPIO = None
        except Exception as e:
            print(f"[WARNING] GPIO initialization failed: {e}")
            self.GPIO = None
        
        # Initialize database
        try:
            self.db = init_db()
            print("[OK] Database initialized")
        except Exception as e:
            print(f"[WARNING] Database initialization failed: {e}")
            self.db = None
        
        print("=" * 50)
        print("Crowd density monitor initialization complete")
        print(f"  - Resolution: {actual_width}x{actual_height}")
        print(f"  - Model: {model_name}")
        print(f"  - Confidence threshold: {self.confidence_threshold}")
        print("=" * 50)
    
    def start_detection_thread(self):
        """Start background detection thread"""
        self.stop_detection = False
        self.detection_thread = threading.Thread(target=self._detection_worker, daemon=True)
        self.detection_thread.start()
        print("[✓] Background detection thread started")
        
        # Start button listening threads
        if self.GPIO:
            # Start first button listener
            self.stop_button = False
            self.button_thread = threading.Thread(target=self._button_worker, daemon=True)
            self.button_thread.start()
            print("[✓] Button 1 listening thread started")
            
            # Start second button listener
            self.stop_button2 = False
            self.button2_thread = threading.Thread(target=self._button2_worker, daemon=True)
            self.button2_thread.start()
            print("[✓] Button 2 listening thread started")
    
    def stop_detection_thread(self):
        """Stop background detection thread"""
        self.stop_detection = True
        self.stop_button = True
        self.stop_button2 = True
        if self.detection_thread:
            self.detection_thread.join(timeout=2)
        if self.button_thread:
            self.button_thread.join(timeout=2)
        if self.button2_thread:
            self.button2_thread.join(timeout=2)
    
    def _detection_worker(self):
        """Background detection worker thread"""
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
                    
                    # Update detection results and statistics
                    with self.lock:
                        self.detections = detections
                        self.person_count = person_count
                        self.density = density
                        self.density_history.append(density)
                        self.person_count_history.append(person_count)
                        self.timestamp_history.append(datetime.now())
                        
                        # Update hourly statistics
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
                        
                        # Periodically save to Database (every 1 minute)
                        if (datetime.now() - self.last_db_save_time).total_seconds() >= self.db_save_interval:
                            if self.db:
                                try:
                                    # Only save data during business hours (7:00 - 23:55)
                                    if 7 <= now.hour < 24:
                                        # Save current time data (only save: people count, time, weekday)
                                        weekday = now.weekday()
                                        result = self.db.add_record(now, person_count, weekday)
                                        self.last_db_save_time = now
                                        # Print log each time data is saved
                                        if detection_count % 100 == 0:
                                            print(f"[Database] Data saved: {person_count} people @ {now.strftime('%Y-%m-%d %H:%M:%S')}")
                                except Exception as e:
                                    print(f"[WARNING] Database save failed: {e}")
                    
                    detection_count += 1
                    if detection_count % 10 == 0:
                        print(f"[Detection] Processed {detection_count} times | Latest: {person_count} people | Time: {self.inference_time*1000:.0f}ms")
                
                except Exception as e:
                    print(f"[WARNING] Detection failed: {e}")
            
            time.sleep(0.01)
    
    def blink_led(self, times=3, interval=0.2):
        """LED blink function
        
        Args:
            times: Number of blinks
            interval: Blink interval (seconds)
        """
        if not self.GPIO:
            return
        
        try:
            for _ in range(times):
                self.GPIO.output(self.LED_PIN, self.GPIO.HIGH)
                time.sleep(interval)
                self.GPIO.output(self.LED_PIN, self.GPIO.LOW)
                time.sleep(interval)
        except Exception as e:
            print(f"[WARNING] LED blink failed: {e}")
    
    def save_button_data(self):
        """Save current crowd data when button is pressed"""
        if not self.db:
            return
        
        try:
            now = datetime.now()
            person_count = self.person_count
            weekday = now.weekday()
            
            # Only save data during business hours (7:00 - 23:55)
            if 7 <= now.hour < 24:
                result = self.db.add_record(now, person_count, weekday)
                print(f"[Button Save] Data saved: {person_count} people @ {now.strftime('%Y-%m-%d %H:%M:%S')}")
                return True
            else:
                print(f"[Button Save] Data not saved: Outside business hours")
                return False
        except Exception as e:
            print(f"[WARNING] Button save failed: {e}")
            return False
    
    def _button_worker(self):
        """Button listening worker thread"""
        import time
        last_state = self.GPIO.LOW
        
        while not self.stop_button:
            try:
                button_state = self.GPIO.input(self.BUTTON_PIN)
                
                # Detect button press from LOW to HIGH
                if button_state == self.GPIO.HIGH and last_state == self.GPIO.LOW:
                    current_time = time.time()
                    
                    # Debounce handling
                    if (current_time - self.last_button_press) > self.button_debounce_time:
                        print("[Button] Button pressed ✓")
                        
                        # Save data
                        self.save_button_data()
                        
                        # LED blink (3 times, 0.1 seconds each)
                        self.blink_led(times=3, interval=0.1)
                        
                        self.last_button_press = current_time
                
                last_state = button_state
                time.sleep(0.05)  # Debounce delay
                
            except Exception as e:
                print(f"[WARNING] Button listening failed: {e}")
                time.sleep(0.1)
    
    def _button2_worker(self):
        """Second button listening worker thread - controls video drawing"""
        import time
        last_state = self.GPIO.LOW
        
        while not self.stop_button2:
            try:
                button_state = self.GPIO.input(self.BUTTON2_PIN)
                
                # Detect button press from LOW to HIGH
                if button_state == self.GPIO.HIGH and last_state == self.GPIO.LOW:
                    current_time = time.time()
                    
                    # Debounce handling
                    if (current_time - self.last_button2_press) > self.button2_debounce_time:
                        # Toggle drawing state
                        self.drawing_enabled = not self.drawing_enabled
                        
                        if self.drawing_enabled:
                            print("[Button2] Drawing enabled ✓")
                            # Turn on LED
                            self.GPIO.output(self.LED2_PIN, self.GPIO.HIGH)
                        else:
                            print("[Button2] Drawing disabled ✗")
                            # Turn off LED
                            self.GPIO.output(self.LED2_PIN, self.GPIO.LOW)
                        
                        self.last_button2_press = current_time
                
                last_state = button_state
                time.sleep(0.05)  # Debounce delay
                
            except Exception as e:
                print(f"[WARNING] Button 2 listening failed: {e}")
                time.sleep(0.1)
    
    def generate_frames(self):
        """Generate video stream - with detection boxes and information overlay"""
        detection_frame_counter = 0
        
        while True:
            ret, frame = self.cap.read()
            if not ret:
                print("[Video Stream] Video stream ended")
                break
            
            # Provide a frame for detection every N frames
            if detection_frame_counter % self.detection_interval == 0:
                with self.lock:
                    self.frame_for_detection = frame.copy()
            
            detection_frame_counter += 1
            self.frame_count += 1
            
            # Draw detection results on video frame
            display_frame = frame.copy()
            with self.lock:
                detections = self.detections
                person_count = self.person_count
                density = self.density
                inference_time = self.inference_time
                drawing_enabled = self.drawing_enabled
            
            # Only draw if drawing is enabled
            if drawing_enabled:
                # Draw detection boxes
                for detection in detections:
                    x1, y1, x2, y2 = detection.xyxy[0]
                    cv2.rectangle(display_frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
                
                # Draw text information
                cv2.putText(display_frame, f'People Count: {person_count}', (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                cv2.putText(display_frame, f'Density: {density:.2f}', (10, 70),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                cv2.putText(display_frame, f'Time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}', (10, 110),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                cv2.putText(display_frame, f'Inference: {inference_time*1000:.0f}ms', (10, 150),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            else:
                # Show "Drawing Disabled" message when drawing is off
                cv2.putText(display_frame, 'Drawing Disabled', (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            
            # Encode as JPEG
            ret, buffer = cv2.imencode('.jpg', display_frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
            frame_data = buffer.tobytes()
            
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_data + b'\r\n')
    
    def process_uploaded_image(self, image_path):
        """Process uploaded image"""
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
            
            print(f"[Uploaded Image] Detection completed | {person_count} people | Time: {inference_time*1000:.0f}ms")
            
            display_frame = frame.copy()
            for detection in detections:
                x1, y1, x2, y2 = detection.xyxy[0]
                cv2.rectangle(display_frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
            
            return display_frame, person_count, density
        
        except Exception as e:
            print(f"[Uploaded Image] Detection failed: {e}")
            return None, 0, 0
    
    def get_realtime_stats(self):
        """Get real-time statistics"""
        with self.lock:
            if len(self.person_count_history) == 0:
                return {
                    "pickup_time": "Calculating...",
                    "crowd_level": "No data",
                    "crowd_range": "0人"
                }
            
            current_count = self.person_count
            
            # Estimate pickup time based on crowd size
            if current_count < 10:
                pickup_time = "2-5 minutes"
                crowd_level = "Low"
            elif current_count < 20:
                pickup_time = "5-10 minutes"
                crowd_level = "Medium"
            elif current_count < 30:
                pickup_time = "10-30 minutes"
                crowd_level = "High"
            else:
                pickup_time = "Over 30 minutes"
                crowd_level = "Very High"
            
            return {
                "pickup_time": pickup_time,
                "crowd_level": crowd_level,
                "crowd_range": f"Approximately {current_count} people (current)"
            }
    
    def get_history_stats(self):
        """Get historical statistics"""
        with self.lock:
            # Weekly flow (last 7 days)
            if len(self.person_count_history) > 0:
                avg_count = int(np.mean(list(self.person_count_history)))
            else:
                avg_count = 0
            weekly_flow = [avg_count] * 7
            
            # Peak time statistics
            peak_times = {}
            for hour_key in sorted(self.hourly_stats.keys()):
                stats = self.hourly_stats[hour_key]
                avg = stats['total_people'] / stats['count'] if stats['count'] > 0 else 0
                peak_times[hour_key] = int(avg)
            
            if not peak_times:
                peak_times = {"09:00": 20, "12:00": 60, "18:00": 40}
            
            # Heatmap data
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
    
    def __del__(self):
        """Destructor - clean up resources"""
        try:
            # Release the camera
            if self.cap:
                self.cap.release()
            
            # Clean up GPIO
            if self.GPIO:
                try:
                    # Turn off all LEDs
                    self.GPIO.output(self.LED_PIN, self.GPIO.LOW)
                    self.GPIO.output(self.LED2_PIN, self.GPIO.LOW)
                    self.GPIO.cleanup()
                    print("[✓] GPIO cleaned up - all LEDs turned off")
                except Exception as e:
                    print(f"[WARNING] GPIO cleanup failed: {e}")
        except Exception as e:
            print(f"[WARNING] Destructor execution failed: {e}")

# Global monitor instance
monitor = None

def cleanup_gpio():
    """Clean up GPIO on exit"""
    global monitor
    if monitor and monitor.GPIO:
        try:
            print("\n[GPIO Cleanup] Turning off LEDs...")
            monitor.GPIO.output(monitor.LED_PIN, monitor.GPIO.LOW)
            monitor.GPIO.output(monitor.LED2_PIN, monitor.GPIO.LOW)
            monitor.GPIO.cleanup()
            print("[✓] GPIO successfully cleaned up")
        except Exception as e:
            print(f"[WARNING] GPIO cleanup error: {e}")

def signal_handler(signum, frame):
    """Handle signals (SIGINT, SIGTERM)"""
    print("\n[SIGNAL] Received interrupt signal")
    cleanup_gpio()
    if monitor:
        monitor.stop_detection_thread()
    print("✓ Exiting...")
    exit(0)

def init_monitor():
    """Initialize the monitor"""
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
        
        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Register atexit handler as fallback
        atexit.register(cleanup_gpio)
        
    except Exception as e:
        print(f"[ERROR] Failed to initialize monitor: {e}")
        print("[INFO] Using simulated data")
        monitor = None


def allowed_file(filename):
    """Check if the file is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def allowed_video(filename):
    """Check if the video file is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in VIDEO_EXTENSIONS


# ========== Route Definitions ==========
@app.route('/')
def index():
    """Home - Real-time Pickup Time Estimation"""
    if monitor:
        data = monitor.get_realtime_stats()
    else:
        data = {
            "pickup_time": "8-12 minutes",
            "crowd_level": "Medium",
            "crowd_range": "Approximately 35-50 people"
        }
    return render_template('index.html', data=data)


@app.route('/history')
def history():
    """Historical Data Page"""
    if monitor:
        data = monitor.get_history_stats()
    else:
        data = {
            "weekly_flow": [30, 45, 60, 50, 70, 80, 65],
            "peak_times": {"Morning": 20, "Noon": 60, "Evening": 40},
            "heatmap": [
                [10, 20, 30, 40],
                [15, 25, 35, 45],
                [20, 30, 40, 50]
            ]
        }
    return render_template('history.html', data=data)


@app.route('/api/time')
def api_time():
    """Get current server time API"""
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
    """Get real-time data API"""
    if monitor:
        return jsonify(monitor.get_realtime_stats())
    else:
        return jsonify({
            "pickup_time": "8-12 minutes",
            "crowd_level": "Medium",
            "crowd_range": "Approximately 35-50 people"
        })


@app.route('/api/save-manual', methods=['POST'])
def api_save_manual():
    """Manually save current data API (optional Web trigger)"""
    if monitor:
        success = monitor.save_button_data()
        monitor.blink_led(times=2, interval=0.15)
        return jsonify({
            'success': success,
            'person_count': monitor.person_count,
            'timestamp': datetime.now().isoformat()
        })
    else:
        return jsonify({'success': False, 'error': 'Monitor not initialized'}), 500


@app.route('/api/history')
def api_history():
    """Get historical data API"""
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
    """Get historical data for a specific weekday
    
    weekday: 0=Monday, 1=Tuesday, ..., 6=Sunday
    Returns the variation of the number of people over time for all dates of that weekday
    """
    try:
        db = get_db()
        if not db:
            return jsonify({'error': 'Database not initialized'}), 503
        
        if weekday < 0 or weekday > 6:
            return jsonify({'error': 'Weekday parameter ERROR, should be 0-6'}), 400
        
        # Get all records for that weekday
        records = db.get_records_by_weekday(weekday)
        
        if not records:
            return jsonify({
                'weekday': weekday,
                'weekday_name': ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'][weekday],
                'records_count': 0,
                'data': [],
                'stats': {
                    'avg_people': 0,
                    'max_people': 0,
                    'min_people': 0
                }
            })
        
        # Get statistical data  
        stats = db.get_weekday_stats(weekday)
        
        # Format record data, sorted by time
        data = []
        person_counts = []
        
        for record in records:
            person_counts.append(record['person_count'])
            data.append({
                'timestamp': record['timestamp'],
                'person_count': record['person_count'],
                'time': record['timestamp'].split('T')[1][:5] if 'T' in record['timestamp'] else ''
            })
        
        # Apply stronger moving average smoothing (window size 21, about 20 minutes)
        smoothed_counts = smooth_data(person_counts, window_size=21)
        
        for i, item in enumerate(data):
            if i < len(smoothed_counts):
                item['person_count'] = smoothed_counts[i]
        
        # Data sampling: take one data point every 10 records to reduce chart density
        # But ensure we have a reasonable number of data points (at least 24 for hourly overview)
        sample_interval = max(1, len(data) // 100)  # Aim for ~100 data points max
        sampled_data = []
        for i in range(0, len(data), sample_interval):
            sampled_data.append(data[i])
        
        # Remove duplicate times (keep the last occurrence)
        seen_times = {}
        deduped_data = []
        for item in sampled_data:
            time_key = item['time']
            seen_times[time_key] = item
        
        # Reconstruct in original order
        for item in sampled_data:
            if item in seen_times.values():
                deduped_data.append(item)
                del seen_times[item['time']]
        
        return jsonify({
            'weekday': weekday,
            'weekday_name': ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'][weekday],
            'records_count': len(records),
            'data': deduped_data,
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
    """Get Database statistics"""
    try:
        db = get_db()
        if not db:
            return jsonify({'error': 'Database not initialized'}), 503
        
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
    """Get real-time detection statistics"""
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
        # Return placeholder
        return jsonify({'error': 'Camera not initialized'}), 503


@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle uploaded photos"""
    if monitor is None:
        return jsonify({'error': 'Monitor not initialized'}), 503
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        result_frame, person_count, density = monitor.process_uploaded_image(filepath)
        
        if result_frame is None:
            return jsonify({'error': 'Unable to read image'}), 400
        
        result_filename = f'result_{datetime.now().strftime("%Y%m%d_%H%M%S")}.jpg'
        result_path = os.path.join(app.config['UPLOAD_FOLDER'], result_filename)
        cv2.imwrite(result_path, result_frame)
        
        return jsonify({
            'success': True,
            'person_count': int(person_count),
            'density': float(density),
            'image_url': f'/static/{result_filename}'
        })
    
    return jsonify({'error': 'File format not supported'}), 400


@app.route('/get_image/<filename>')
def get_image(filename):
    """Get processed image"""
    try:
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
    except:
        return jsonify({'error': 'File not found'}), 404

if __name__ == '__main__':
    print("=" * 70)
    print("Starting integrated Flask server (MC + Frontend)")
    print("=" * 70)
    print(f"Template folder: {TEMPLATE_FOLDER}")
    print(f"Static folder: {STATIC_FOLDER}")
    
    # Try to print configuration info
    try:
        print_routes_info()
        startup_info = get_startup_info()
        print("\nAccess URLs:")
        for key, url in startup_info.items():
            print(f"  - {key:15}: {url}")
    except:
        print("\nAccess URLs:")
        print(f"  - Home: http://localhost:5000")
        print(f"  - History: http://localhost:5000/history")
    
    print("=" * 70)
    
    try:
        init_monitor()
        port = FLASK_CONFIG.get('PORT', 5000)
        host = FLASK_CONFIG.get('HOST', '0.0.0.0')
        debug = FLASK_CONFIG.get('DEBUG', False)
        threaded = FLASK_CONFIG.get('THREADED', True)
        
        print("[OK] Starting Flask server...")
        app.run(host=host, port=port, debug=debug, threaded=threaded)
    except KeyboardInterrupt:
        print("\n[KeyboardInterrupt] Shutting down...")
        cleanup_gpio()
        if monitor:
            monitor.stop_detection_thread()
        print("✓ Safely shut down")
    except Exception as e:
        print(f"\n[ERROR] Application error: {e}")
        cleanup_gpio()
        if monitor:
            monitor.stop_detection_thread()