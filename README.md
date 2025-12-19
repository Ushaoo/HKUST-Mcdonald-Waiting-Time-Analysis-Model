# HKUST-Mcdonald-Waiting-Time-Analysis-Model


## Project Overview

A real-time crowd density monitoring system for McDonald's restaurants, powered by YOLOv8 deep learning model. The system provides instant wait time estimations based on real-time crowd detection and maintains historical data analysis for traffic pattern insights.

**Key Features:**
- 🎯 Real-time person detection with YOLOv8n
- 📊 Wait time estimation based on crowd density
- 📈 Historical data analysis and peak time identification
- 🎮 Interactive web dashboard with live video stream
- 🔘 Hardware control with GPIO buttons and LEDs
- 💾 SQLite database for historical records
- 🚀 Multi-threaded architecture for high performance

---

## System Architecture

### Hardware IO System (RDK X5 Control Board)

```
┌─────────────────────────────────────────────────────────────────┐
│                         RDK X5 Control Board                     │
│                       (ARMv8 8-Core CPU)                         │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                 GPIO Interface                            │   │
│  │                                                            │   │
│  │  Button 1 ─────► Pin 31  ◄─── Save Data + LED Feedback  │   │
│  │  LED 1    ◄───── Pin 13  ◄─── Data Save Indicator        │   │
│  │                                                            │   │
│  │  Button 2 ─────► Pin 29  ◄─── Drawing Enable/Disable    │   │
│  │  LED 2    ◄───── Pin 11  ◄─── Drawing Status Indicator   │   │
│  └──────────────────────────────────────────────────────────┘   │
│                            ▲                                      │
│                            │ GPIO Data                            │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              Camera Interface (USB)                       │   │
│  │                                                            │   │
│  │  USB Camera ────────► Camera Capture Port                │   │
│  │  (1280×720@30fps)      YOLOv8 Inference Engine           │   │
│  └──────────────────────────────────────────────────────────┘   │
│                            ▲                                      │
│                            │ Video Data                           │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │           Storage & Networking                            │   │
│  │                                                            │   │
│  │  ┌─────────────────┐  ┌──────────────────────────┐       │   │
│  │  │ SQLite Database │  │   Flask Web Server       │       │   │
│  │  │  crowd_data.db  │  │  (HTTP/HTTPS Port 5000)  │       │   │
│  │  │                 │  │                          │       │   │
│  │  │ - Real-time     │  │ - Frontend UI (HTML/JS)  │       │   │
│  │  │   records       │  │ - REST APIs              │       │   │
│  │  │ - Historical    │  │ - Video streaming        │       │   │
│  │  │   analysis      │  │ - Real-time stats        │       │   │
│  │  └─────────────────┘  └──────────────────────────┘       │   │
│  └──────────────────────────────────────────────────────────┘   │
│                            ▲                                      │
│                            │ Ethernet                             │
└──────────────────────────────────────────────────────────────────┘
         ▲                                      
         │ Network Connection                  
         │                                      
    ┌────┴──────────────┐                     
    │   WiFi/Ethernet   │                     
    │    Router/Hub     │                     
    └───────────────────┘                     
         ▲                                      
         │                                      
    ┌────┴──────────────────────────────────────────┐
    │      Client Devices                           │
    │  ┌─────────────────┐  ┌─────────────────┐   │
    │  │  Web Browser    │  │   Mobile App    │   │
    │  │  (Dashboard)    │  │   (Monitoring)  │   │
    │  └─────────────────┘  └─────────────────┘   │
    └───────────────────────────────────────────────┘
```

### Software Architecture

```
┌──────────────────────────────────────────────────────┐
│          Flask Web Application (app.py)              │
├──────────────────────────────────────────────────────┤
│  ┌────────────────────────────────────────────────┐  │
│  │     CrowdDensityMonitor Main Class             │  │
│  │  • YOLOv8 Model & Inference                    │  │
│  │  • Real-time Camera Capture                    │  │
│  │  • Multi-threaded Detection Worker             │  │
│  │  • GPIO Button/LED Control                     │  │
│  │  • Data Statistics & History                   │  │
│  └────────────────────────────────────────────────┘  │
│              │              │              │          │
│    ┌─────────┴────┬────────┴───┬──────────┴───────┐ │
│    ▼              ▼             ▼                  ▼ │
│ ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌──────────┐│
│ │Database │  │   GUI   │  │  GPIO   │  │Statistics││
│ │ Manager │  │ Routes  │  │ Control │  │ Tracking ││
│ │(db.py)  │  │(routes) │  │ (pins)  │  │(analysis)││
│ └─────────┘  └─────────┘  └─────────┘  └──────────┘│
│    Data        UI          Hardware      Analytics   │
└──────────────────────────────────────────────────────┘
```

---

## File Structure

```
MC/
├── app.py                          # Main Flask app (847 lines)
│   ├── CrowdDensityMonitor         # Core detection class
│   ├── Video frame generation      # MJPEG stream
│   ├── GPIO handlers               # Button/LED mgmt
│   └── REST API routes             # API endpoints
│
├── database.py                     # SQLite management (159 lines)
│   └── CrowdDatabase class         # CRUD operations
│
├── config.py                       # Configuration module
│   ├── Flask settings
│   ├── Camera parameters
│   ├── Model config
│   └── Route definitions
│
├── generate_historical_data.py     # Test data generation
│
├── requirements.txt                # Python dependencies
├── yolov8n.pt                      # YOLOv8 Nano model
│
├── templates/
│   ├── index.html                  # Real-time dashboard
│   └── history.html                # Historical analysis
│
├── static/
│   └── chart.js                    # Charting library
│
└── README.md                       # This file
```

---

## Technical Specifications

### Hardware Requirements

- **Control Board**: RDK X5 (ARMv8 8-Core, 4GB+ RAM)
- **Camera**: USB Camera (1280×720@30fps recommended)
- **GPIO Components**:
  - Button 1 (Pin 31) - Data Save
  - LED 1 (Pin 13) - Save Indicator
  - Button 2 (Pin 29) - Drawing Toggle
  - LED 2 (Pin 11) - Drawing Status
- **Storage**: 512MB+ for SQLite database

### Software Stack

| Component | Version | Purpose |
|-----------|---------|---------|
| Python | 3.8+ | Runtime |
| Flask | 2.3.3 | Web Framework |
| OpenCV | 4.8.1.78 | Video Processing |
| YOLOv8 | 8.0.194 | Detection Engine |
| NumPy | 1.24.3 | Numerical Computing |
| SQLite | Built-in | Database |

### Performance Metrics

- **Inference Speed**: ~100-150ms per frame (RDK X5)
- **Detection Rate**: Every 3 frames (optimal balance)
- **Video Quality**: 1280×720 @ 30 FPS
- **Database Save**: Every 60 seconds

---

## Installation & Setup

### Step 1: Clone Repository

```bash
cd /home/sunrise
git clone <repository-url>
cd MC
```

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 3: Verify Model File

```bash
# Check if yolov8n.pt exists
ls -lh yolov8n.pt

# If missing, download:
# wget https://github.com/ultralytics/assets/releases/download/v8.0.0/yolov8n.pt
```

### Step 4: Install GPIO (Optional)

```bash
# For RDK X5 with Hobot GPIO
pip install hobot-gpio
```

### Step 5: Generate Test Data (Optional)

```bash
python generate_historical_data.py
```

### Step 6: Run Application

```bash
python app.py
```

Expected output:
```
======================================================================
Starting integrated Flask server (MC + Frontend)
======================================================================
[OK] GPIO initialized
[OK] Database initialized
[OK] Starting Flask server...

Access URLs:
  - Home: http://localhost:5000
  - History: http://localhost:5000/history
======================================================================
```

---

## API Documentation

### 1. Real-time Data API

```
GET /api/realtime
```

**Response:**
```json
{
  "pickup_time": "5-10 minutes",
  "crowd_level": "Medium",
  "crowd_range": "Approximately 15 people (current)"
}
```

### 2. Server Time API

```
GET /api/time
```

**Response:**
```json
{
  "timestamp": "2025-12-19T14:30:45.123456",
  "formatted": "2025-12-19 14:30:45",
  "hour": 14,
  "minute": 30,
  "second": 45,
  "weekday": 4
}
```

### 3. Historical Data by Weekday

```
GET /api/weekday/<int:weekday>
```

Weekday: 0=Monday, 1=Tuesday, ..., 6=Sunday

**Response:**
```json
{
  "weekday": 4,
  "weekday_name": "Friday",
  "records_count": 1440,
  "data": [
    {
      "timestamp": "2025-12-19T07:00:00",
      "person_count": 35,
      "time": "07:00"
    }
  ],
  "stats": {
    "avg_people": 42.5,
    "max_people": 95,
    "min_people": 8
  }
}
```

### 4. Real-time Video Stream

```
GET /video_feed
```

Returns MJPEG stream with detection boxes and overlays.

---

## Hardware Control

### GPIO Configuration

| Set | Button | LED | Function |
|-----|--------|-----|----------|
| 1 | Pin 31 | Pin 13 | Data Save |
| 2 | Pin 29 | Pin 11 | Drawing Toggle |

### Button Behavior

**Button 1 (Pin 31):**
- Manually save crowd data to database
- LED blinks 3 times on success
- Debounce: 0.5 seconds
- Time window: 7:00 - 23:55 only

**Button 2 (Pin 29):**
- Toggle detection box drawing
- LED state indicates: HIGH=Drawing ON, LOW=Drawing OFF
- Default: Enabled (LED HIGH)

---

## Wait Time Estimation Logic

| Person Count | Wait Time | Level |
|--------------|-----------|-------|
| < 10 | 2-5 min | Low |
| 10-19 | 5-10 min | Medium |
| 20-29 | 10-30 min | High |
| ≥ 30 | 30+ min | Very High |

---


### Function Call Chain

```
app.run()
  ├── init_monitor()
  │   └── CrowdDensityMonitor.__init__()
  │       ├── YOLO(model_name)
  │       ├── cv2.VideoCapture(camera_id)
  │       └── init_db()
  │
  ├── monitor.start_detection_thread()
  │   ├── _detection_worker()
  │   │   ├── model.inference()
  │   │   ├── update statistics
  │   │   └── db.add_record()
  │   ├── _button_worker()
  │   │   ├── save_button_data()
  │   │   └── blink_led()
  │   └── _button2_worker()
  │       └── toggle drawing_enabled
  │
  └── Flask routes
      ├── @app.route('/') → index()
      ├── @app.route('/history') → history()
      ├── @app.route('/api/realtime') → api_realtime()
      ├── @app.route('/api/weekday/<int:weekday>') → api_weekday_data()
      ├── @app.route('/api/time') → api_time()
      └── @app.route('/video_feed') → video_feed()
```

