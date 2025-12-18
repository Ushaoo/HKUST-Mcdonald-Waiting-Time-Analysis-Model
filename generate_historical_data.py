"""
生成历史人流数据脚本（简化版）
生成一周各个工作日和周末的数据，用于展示历史趋势
"""

import sqlite3
import os
from datetime import datetime, timedelta
import numpy as np

# 导入数据库模块
from database import CrowdDatabase, DB_PATH

def generate_historical_data():
    """
    生成历史数据
    时间范围：2025-12-01 到 2025-12-14 (两周)
    开门时间：每日07:00
    关门时间：每日23:55
    间隔：1分钟（更合理的数据记录频率）
    """
    
    db = CrowdDatabase(DB_PATH)
    
    # 先清空旧数据
    db.clear_all()
    
    start_date = datetime(2025, 12, 1, 7, 0, 0)
    end_date = datetime(2025, 12, 14, 23, 55, 0)
    
    # 定义人流分布 (按小时)
    # 早上：7-9点 (小峰值)
    # 中午：11-13点 (大峰值) 
    # 傍晚：17-19点 (中峰值)
    
    def get_base_people_count(hour, weekday):
        """
        根据小时和星期几获取基础人流量
        weekday: 0=Monday, 1=Tuesday, ..., 6=Sunday
        """
        
        # 基础时间因子（降低正态分布的标准差，使波动更平缓）
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
        elif 17 <= hour < 19:  # 傍晚17-19点 (中峰值)
            base = 65 + np.random.normal(0, 3)  # 降低波动
        elif 19 <= hour < 22:  # 晚上
            base = 28 + np.random.normal(0, 1.5)
        else:  # 22点后
            base = 10 + np.random.normal(0, 0.5)
        
        # 周末人数相对较少（周六、周日）
        if weekday >= 5:  # 周六、周日
            base = base * 0.65
        # 周三、周四相对较多
        elif weekday in [2, 3]:  # 周三、周四
            base = base * 1.18
        # 周一、周二、周五为正常
        
        return max(int(base), 0)
    
    # 生成数据
    current_time = start_date
    record_count = 0
    
    print("=" * 60)
    print("开始生成历史人流数据...")
    print(f"时间范围: {start_date.strftime('%Y-%m-%d %H:%M')} ~ {end_date.strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)
    
    while current_time <= end_date:
        hour = current_time.hour
        weekday = current_time.weekday()
        
        # 只在营业时间内生成数据 (7:00 - 23:55)
        if 7 <= hour < 24:
            person_count = get_base_people_count(hour, weekday)
            
            # 随机波动 ±5%（减少波动，使曲线更平滑）
            person_count = int(person_count * np.random.uniform(0.95, 1.05))
            person_count = max(person_count, 0)
            
            # 添加到数据库
            try:
                db.add_record(current_time, person_count, weekday)
                record_count += 1
                
                if record_count % 500 == 0:
                    print(f"✓ 已生成 {record_count} 条记录 | 时间: {current_time.strftime('%Y-%m-%d %H:%M')} | 人数: {person_count}")
            
            except Exception as e:
                print(f"✗ 添加记录失败: {e}")
        
        # 每1分钟推进一次（更实际的数据间隔）
        current_time += timedelta(minutes=1)
    
    print("=" * 60)
    print(f"✓ 数据生成完成！")
    print(f"  - 总记录数: {record_count}")
    print(f"  - 数据库位置: {DB_PATH}")
    print(f"  - 数据库大小: {db.get_database_size():.2f} MB")
    print("=" * 60)
    
    # 打印统计信息
    print("\n各星期的数据统计:")
    print("-" * 60)
    
    weekday_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    
    for weekday in range(7):
        stats = db.get_weekday_stats(weekday)
        
        if stats and stats['record_count'] > 0:
            print(f"{weekday_names[weekday]}")
            print(f"  记录数: {stats['record_count']}")
            print(f"  平均: {stats['avg_people']:.1f} 人")
            print(f"  峰值: {stats['max_people']} 人")
            print(f"  最低: {stats['min_people']} 人")
            print()


if __name__ == '__main__':
    generate_historical_data()
