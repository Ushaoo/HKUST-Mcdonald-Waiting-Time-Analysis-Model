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
    
    # Define crowd distribution (by hour)
    # Morning: 7-9 am (small peak)
    # Lunch: 11-1 pm (big peak) 
    # Evening: 5-7 pm (medium peak)
    
    def get_base_people_count(hour, weekday):
        """
        Get base people count based on hour and weekday
        weekday: 0=Monday, 1=Tuesday, ..., 6=Sunday
        """
        
        # Base time factor (reduced normal distribution standard deviation for smoother fluctuation)
        if 7 <= hour < 8:  # 7-8 am
            base = 35 + np.random.normal(0, 2)
        elif 8 <= hour < 9:  # 8-9 am (increased flow)
            base = 50 + np.random.normal(0, 2.5)
        elif 9 <= hour < 11:  # Morning
            base = 20 + np.random.normal(0, 1)
        elif 11 <= hour < 13:  # Lunch 11am-1pm (peak)
            base = 85 + np.random.normal(0, 4)
        elif 13 <= hour < 17:  # Afternoon
            base = 22 + np.random.normal(0, 1.5)
        elif 17 <= hour < 19:  # Evening 5-7pm (medium peak)
            base = 65 + np.random.normal(0, 3)
        elif 19 <= hour < 22:  # Night
            base = 28 + np.random.normal(0, 1.5)
        else:  # After 10pm
            base = 10 + np.random.normal(0, 0.5)
        
        # Weekend traffic is relatively lower (Saturday, Sunday)
        if weekday >= 5:  # Saturday, Sunday
            base = base * 0.65
        # Wednesday, Thursday has more traffic
        elif weekday in [2, 3]:  # Wednesday, Thursday
            base = base * 1.18
        # Monday, Tuesday, Friday are normal
        
        return max(int(base), 0)
    
    # Generate data
    current_time = start_date
    record_count = 0
    
    print("=" * 60)
    print("Starting historical crowd data generation...")
    print(f"Time range: {start_date.strftime('%Y-%m-%d %H:%M')} ~ {end_date.strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)
    
    while current_time <= end_date:
        hour = current_time.hour
        weekday = current_time.weekday()
        
        # Only generate data during business hours (7:00 - 23:55)
        if 7 <= hour <= 23:
            person_count = get_base_people_count(hour, weekday)
            
            # Random fluctuation ±5% (reduced fluctuation for smoother curves)
            person_count = int(person_count * np.random.uniform(0.95, 1.05))
            person_count = max(person_count, 0)
            
            # Add to database
            try:
                db.add_record(current_time, person_count, weekday)
                record_count += 1
                
                if record_count % 500 == 0:
                    print(f"✓ Generated {record_count:5d} records | Time: {current_time.strftime('%Y-%m-%d %H:%M')} | People: {person_count:3d}")
            
            except Exception as e:
                print(f"✗ Add record failed: {e}")
        
        # Advance by 1 minute (more realistic data interval)
        current_time += timedelta(minutes=1)
    
    print("=" * 60)
    print("✓ Data generation complete!")
    print(f"  - Total records: {record_count}")
    print(f"  - Database location: {DB_PATH}")
    print(f"  - Database size: {db.get_database_size():.2f} MB")
    print("=" * 60)
    
    # Print statistics
    print("\nStatistics by day of week:")
    print("-" * 60)
    
    weekday_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    
    for weekday in range(7):
        stats = db.get_weekday_stats(weekday)
        
        if stats and stats['record_count'] > 0:
            print(f"{weekday_names[weekday]}")
            print(f"  Records: {stats['record_count']}")
            print(f"  Average: {stats['avg_people']:.1f} people")
            print(f"  Peak: {stats['max_people']} people")
            print(f"  Minimum: {stats['min_people']} people")
            print()


if __name__ == '__main__':
    generate_historical_data()
