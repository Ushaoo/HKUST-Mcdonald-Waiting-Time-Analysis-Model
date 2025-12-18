"""
数据统计模块 - 获取实时和历史统计数据
这个模块从全局的monitor对象获取数据，并格式化为API响应格式
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

# 全局monitor对象（在app.py中初始化）
monitor = None

def set_monitor(m):
    """设置全局monitor对象"""
    global monitor
    monitor = m

def get_realtime_data():
    """获取实时统计数据
    
    Returns:
        dict: 包含预计取餐时间、人流量等级、人流量范围的数据
    """
    if monitor is None:
        return {
            "pickup_time": "8-12分钟",
            "crowd_level": "中等",
            "crowd_range": "约35-50人"
        }
    
    return monitor.get_realtime_stats()

def get_history_data():
    """获取历史统计数据
    
    Returns:
        dict: 包含周人流量、高峰时段、热力图的数据
    """
    if monitor is None:
        return {
            "weekly_flow": [30, 45, 60, 50, 70, 80, 65],
            "peak_times": {"早上": 20, "中午": 60, "晚上": 40},
            "heatmap": [
                [10, 20, 30, 40],
                [15, 25, 35, 45],
                [20, 30, 40, 50]
            ]
        }
    
    return monitor.get_history_stats()

def get_detailed_stats():
    """获取详细的统计信息"""
    if monitor is None:
        return {
            "status": "离线",
            "current_people": 0,
            "average_people": 0,
            "total_detections": 0
        }
    
    with monitor.lock:
        avg_count = 0
        if len(monitor.person_count_history) > 0:
            import numpy as np
            avg_count = int(np.mean(list(monitor.person_count_history)))
        
        return {
            "status": "在线",
            "current_people": monitor.person_count,
            "average_people": avg_count,
            "max_people": max(monitor.person_count_history) if monitor.person_count_history else 0,
            "total_detections": len(monitor.person_count_history),
            "inference_time_ms": monitor.inference_time * 1000,
            "frame_count": monitor.frame_count
        }
