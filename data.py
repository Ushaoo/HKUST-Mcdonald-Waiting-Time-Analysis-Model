"""
Data statistics module - fetches real-time and historical statistics
This module gets data from the global monitor object and formats it as API response
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

# Global monitor object (initialized in app.py)
monitor = None

def set_monitor(m):
    """Set global monitor object"""
    global monitor
    monitor = m

def get_realtime_data():
    """Get real-time statistics
    
    Returns:
        dict: Data containing estimated pickup time, crowd level, and crowd range
    """
    if monitor is None:
        return {
            "pickup_time": "8-12 minutes",
            "crowd_level": "Medium",
            "crowd_range": "~35-50 people"
        }
    
    return monitor.get_realtime_stats()

def get_history_data():
    """Get historical statistics
    
    Returns:
        dict: Data containing weekly flow, peak times, and heatmap
    """
    if monitor is None:
        return {
            "weekly_flow": [30, 45, 60, 50, 70, 80, 65],
            "peak_times": {"Morning": 20, "Lunch": 60, "Evening": 40},
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
