"""
Generate historical crowd data for McDonald's crowd monitoring system.
Creates realistic records across two weeks with time-based traffic patterns.
"""

import sqlite3
import os
from datetime import datetime, timedelta
import numpy as np

# Import database module
from database import CrowdDatabase, DB_PATH

def generate_historical_data():
    """
    Generate historical crowd data for the system.
    Time range: 2025-12-01 to 2025-12-14 (two weeks)
    Opening time: 07:00 daily
    Closing time: 23:55 daily
    Recording interval: 1 minute (realistic data frequency)
    """
    
    db = CrowdDatabase(DB_PATH)
    
    # Clear old data
    db.clear_all()
    
    start_date = datetime(2025, 12, 1, 7, 0, 0)
    end_date = datetime(2025, 12, 14, 23, 55, 0)
    
    # 定义人流分布 (按小时)
    # 早上：7-9点 (小peak)
    # 中午：11-13点 (大peak) 
    # 傍晚：17-19点 (中peak)
    
    def get_base_people_count(hour, weekday):
        """
        根据小时和day of week几获取基础人流量
        weekday: 0=Monday, 1=Tuesday, ..., 6=Sunday
        """
        
        # 基础time因子（降低正态分布的标准差，使波动更平缓）
        if 7 <= hour < 8:  # 早上7-8点
            base = 35 + np.random.normal(0, 2)  # 降低波动
        elif 8 <= hour < 9:  # 早上8-9点 (增加人流)
            base = 50 + np.random.normal(0, 2.5)  # 降低波动
        elif 9 <= hour < 11:  # 上午
            base = 20 + np.random.normal(0, 1)
        elif 11 <= hour < 13:  # 中午11-13点 (高峰)
            base = 85 + np.random.normal(0, 4)  # 降低波动
        elif 13 <= hour < 17:  # 下午
            base = 22 + np.random.normal(0, 1.5)
        elif 17 <= hour < 19:  # 傍晚17-19点 (中peak)
            base = 65 + np.random.normal(0, 3)  # 降低波动
        elif 19 <= hour < 22:  # 晚上
            base = 28 + np.random.normal(0, 1.5)
        else:  # 22点后
            base = 10 + np.random.normal(0, 0.5)
        
        # weekendpeople相对较少（周六、周日）
        if weekday >= 5:  # 周六、周日
            base = base * 0.65
        # 周三、周四相对较多
        elif weekday in [2, 3]:  # 周三、周四
            base = base * 1.18
        # 周一、周二、周五为正常
        
        return max(int(base), 0)
    
    # Generatedata
    current_time = start_date
    record_count = 0
    
    print("=" * 60)
    print("startGeneratehistorical人流data...")
    print(f"Time range: {start_date.strftime('%Y-%m-%d %H:%M')} ~ {end_date.strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)
    
    while current_time <= end_date:
        hour = current_time.hour
        weekday = current_time.weekday()
        
        # 只在businesstimewithinGeneratedata (7:00 - 23:55)
        if 7 <= hour < 24:
            person_count = get_base_people_count(hour, weekday)
            
            # 随机波动 ±5%（减少波动，使曲线更平滑）
            person_count = int(person_count * np.random.uniform(0.95, 1.05))
            person_count = max(person_count, 0)
            
            # add到data库
            try:
                db.add_record(current_time, person_count, weekday)
                record_count += 1
                
                if record_count % 500 == 0:
                    print(f"✓ 已Generate {record_count} 条records | time: {current_time.strftime('%Y-%m-%d %H:%M')} | people: {person_count}")
            
            except Exception as e:
                print(f"✗ addrecordsfailed: {e}")
        
        # 每1minute推进一次（更实际的datainterval）
        current_time += timedelta(minutes=1)
    
    print("=" * 60)
    print(f"✓ dataGeneratecomplete！")
    print(f"  - totalrecords数: {record_count}")
    print(f"  - data库location: {DB_PATH}")
    print(f"  - data库size: {db.get_database_size():.2f} MB")
    print("=" * 60)
    
    # 打印statistics信息
    print("\n各day of week的datastatistics:")
    print("-" * 60)
    
    weekday_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    
    for weekday in range(7):
        stats = db.get_weekday_stats(weekday)
        
        if stats and stats['record_count'] > 0:
            print(f"{weekday_names[weekday]}")
            print(f"  records数: {stats['record_count']}")
            print(f"  average: {stats['avg_people']:.1f} 人")
            print(f"  peak: {stats['max_people']} 人")
            print(f"  minimum: {stats['min_people']} 人")
            print()


if __name__ == '__main__':
    generate_historical_data()
