"""
Application configuration file - supports multiple access methods and route management
"""

# Flask application configuration
FLASK_CONFIG = {
    'DEBUG': False,
    'HOST': '0.0.0.0',
    'PORT': 5000,
    'THREADED': True,
}

# Route configuration
ROUTES_CONFIG = {
    # Main application routes (frontend UI)
    '/': {
        'name': 'Home - Real-time Wait Estimation',
        'type': 'frontend',
        'template': 'index.html'
    },
    '/history': {
        'name': 'Historical Data',
        'type': 'frontend',
        'template': 'history.html'
    },
    
    # API routes
    '/api/realtime': {
        'name': 'Real-time Data API',
        'type': 'api',
        'description': 'Get real-time statistics'
    },
    '/api/history': {
        'name': 'Historical Data API',
        'type': 'api',
        'description': 'Get historical statistics'
    },
    '/api/stats': {
        'name': 'Detailed Statistics API',
        'type': 'api',
        'description': 'Get detailed detection statistics'
    },
    
    # Media routes
    '/video_feed': {
        'name': 'Real-time Video Stream',
        'type': 'stream',
        'description': 'Live camera video stream'
    },
    '/upload': {
        'name': 'Image Upload',
        'type': 'api',
        'methods': ['POST']
    },
}

# Domain routing configuration (for multiple domain support)
DOMAIN_ROUTES = {
    'localhost:5000': {
        'name': 'Local development server',
        'routes': ['/', '/history', '/api/realtime', '/api/history', '/video_feed']
    },
    'default': {
        'name': 'Default configuration',
        'routes': 'all'  # All routes are available
    }
}

# Camera configuration
CAMERA_CONFIG = {
    'enabled': True,
    'camera_id': 0,
    'width': 1280,
    'height': 720,
    'fps': 30,
    'quality': 70  # JPEG quality (1-100)
}

# YOLO model configuration
MODEL_CONFIG = {
    'enabled': True,
    'model_name': 'yolov8n.pt',
    'confidence_threshold': 0.1,
    'detection_interval': 3,  # Perform detection every N frames
    'class_id': 0,  # Detect persons only (class 0 in COCO dataset)
}

# Data statistics configuration
STATS_CONFIG = {
    'history_maxlen': 100,  # Keep last 100 detection results
    'update_interval': 2000,  # Frontend update interval (milliseconds)
    'enable_hourly_stats': True,  # Enable hourly statistics
    'enable_daily_stats': True,  # Enable daily statistics
}

# Security configuration
SECURITY_CONFIG = {
    'max_file_size': 500 * 1024 * 1024,  # Maximum file size (500MB)
    'allowed_image_extensions': {'png', 'jpg', 'jpeg', 'gif', 'bmp'},
    'allowed_video_extensions': {'mp4', 'avi', 'mov', 'mkv', 'flv', 'wmv'},
}

# Logging configuration
LOG_CONFIG = {
    'level': 'INFO',
    'format': '[%(asctime)s] %(levelname)s: %(message)s',
}


def get_route_info(path):
    """Get information for specified route"""
    return ROUTES_CONFIG.get(path, None)


def get_enabled_routes():
    """Get all enabled routes"""
    routes = []
    for path, config in ROUTES_CONFIG.items():
        if config.get('type') != 'disabled':
            routes.append({
                'path': path,
                'name': config['name'],
                'type': config['type']
            })
    return routes


def print_routes_info():
    """Print information for all available routes"""
    print("\n" + "="*60)
    print("Available Routes and APIs")
    print("="*60)
    
    routes = get_enabled_routes()
    
    # Group by type
    frontend_routes = [r for r in routes if r['type'] == 'frontend']
    api_routes = [r for r in routes if r['type'] == 'api']
    stream_routes = [r for r in routes if r['type'] == 'stream']
    
    if frontend_routes:
        print("\n[Frontend UI Routes]")
        for route in frontend_routes:
            print(f"  * {route['path']:20} - {route['name']}")
    
    if api_routes:
        print("\n[API Routes]")
        for route in api_routes:
            print(f"  * {route['path']:20} - {route['name']}")
    
    if stream_routes:
        print("\n[Media Stream Routes]")
        for route in stream_routes:
            print(f"  * {route['path']:20} - {route['name']}")
    
    print("\n" + "="*60)


def get_startup_info():
    """Get startup information"""
    port = FLASK_CONFIG['PORT']
    host = FLASK_CONFIG['HOST'] if FLASK_CONFIG['HOST'] != '0.0.0.0' else 'localhost'
    
    return {
        'home': f'http://{host}:{port}/',
        'history': f'http://{host}:{port}/history',
        'api_realtime': f'http://{host}:{port}/api/realtime',
        'api_history': f'http://{host}:{port}/api/history',
        'video_stream': f'http://{host}:{port}/video_feed',
    }
