"""
应用配置文件 - 支持多种访问方式和路由管理
"""

# Flask应用配置
FLASK_CONFIG = {
    'DEBUG': False,
    'HOST': '0.0.0.0',
    'PORT': 5000,
    'THREADED': True,
}

# 路由配置
ROUTES_CONFIG = {
    # 主应用路由（前端UI）
    '/': {
        'name': '首页 - 实时取餐预估',
        'type': 'frontend',
        'template': 'index.html'
    },
    '/history': {
        'name': '历史数据',
        'type': 'frontend',
        'template': 'history.html'
    },
    
    # API路由
    '/api/realtime': {
        'name': '实时数据API',
        'type': 'api',
        'description': '获取实时统计数据'
    },
    '/api/history': {
        'name': '历史数据API',
        'type': 'api',
        'description': '获取历史统计数据'
    },
    '/api/stats': {
        'name': '详细统计API',
        'type': 'api',
        'description': '获取详细的检测统计信息'
    },
    
    # 媒体路由
    '/video_feed': {
        'name': '实时视频流',
        'type': 'stream',
        'description': '实时摄像头视频流'
    },
    '/upload': {
        'name': '图片上传',
        'type': 'api',
        'methods': ['POST']
    },
}

# 不同域名访问配置（如果需要）
DOMAIN_ROUTES = {
    'localhost:5000': {
        'name': '本地开发服务器',
        'routes': ['/', '/history', '/api/realtime', '/api/history', '/video_feed']
    },
    'default': {
        'name': '默认配置',
        'routes': 'all'  # 所有路由都可用
    }
}

# 摄像头配置
CAMERA_CONFIG = {
    'enabled': True,
    'camera_id': 0,
    'width': 1280,
    'height': 720,
    'fps': 30,
    'quality': 70  # JPEG质量 (1-100)
}

# YOLO模型配置
MODEL_CONFIG = {
    'enabled': True,
    'model_name': 'yolov8n.pt',
    'confidence_threshold': 0.1,
    'detection_interval': 3,  # 每N帧进行一次检测
    'class_id': 0,  # 只检测人（COCO数据集中的类别0）
}

# 数据统计配置
STATS_CONFIG = {
    'history_maxlen': 100,  # 保留最近100条检测结果
    'update_interval': 2000,  # 前端更新间隔（毫秒）
    'enable_hourly_stats': True,  # 是否启用小时统计
    'enable_daily_stats': True,  # 是否启用日统计
}

# 安全配置
SECURITY_CONFIG = {
    'max_file_size': 500 * 1024 * 1024,  # 最大文件大小 (500MB)
    'allowed_image_extensions': {'png', 'jpg', 'jpeg', 'gif', 'bmp'},
    'allowed_video_extensions': {'mp4', 'avi', 'mov', 'mkv', 'flv', 'wmv'},
}

# 日志配置
LOG_CONFIG = {
    'level': 'INFO',
    'format': '[%(asctime)s] %(levelname)s: %(message)s',
}


def get_route_info(path):
    """获取指定路由的信息"""
    return ROUTES_CONFIG.get(path, None)


def get_enabled_routes():
    """获取所有启用的路由"""
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
    """打印所有可用的路由信息"""
    print("\n" + "="*60)
    print("可用的路由和API")
    print("="*60)
    
    routes = get_enabled_routes()
    
    # 按类型分组
    frontend_routes = [r for r in routes if r['type'] == 'frontend']
    api_routes = [r for r in routes if r['type'] == 'api']
    stream_routes = [r for r in routes if r['type'] == 'stream']
    
    if frontend_routes:
        print("\n【前端UI路由】")
        for route in frontend_routes:
            print(f"  ✓ {route['path']:20} - {route['name']}")
    
    if api_routes:
        print("\n【API路由】")
        for route in api_routes:
            print(f"  ✓ {route['path']:20} - {route['name']}")
    
    if stream_routes:
        print("\n【媒体流路由】")
        for route in stream_routes:
            print(f"  ✓ {route['path']:20} - {route['name']}")
    
    print("\n" + "="*60)


def get_startup_info():
    """获取启动信息"""
    port = FLASK_CONFIG['PORT']
    host = FLASK_CONFIG['HOST'] if FLASK_CONFIG['HOST'] != '0.0.0.0' else 'localhost'
    
    return {
        'home': f'http://{host}:{port}/',
        'history': f'http://{host}:{port}/history',
        'api_realtime': f'http://{host}:{port}/api/realtime',
        'api_history': f'http://{host}:{port}/api/history',
        'video_stream': f'http://{host}:{port}/video_feed',
    }
