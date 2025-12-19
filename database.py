"""
Database initialization and management module
SQLite database designed for storing crowd monitoring data

Table structure description:
- crowd_records: Real-time crowd records (each record contains: person count, time, day of week)
  Minimalist design, only recording necessary information
"""

import sqlite3
import os
from datetime import datetime, timedelta
from pathlib import Path

# Database file path
DB_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(DB_DIR, 'crowd_data.db')

class CrowdDatabase:
    """Crowd data database management class"""
    
    def __init__(self, db_path=DB_PATH):
        """Initialize database connection"""
        self.db_path = db_path
        self.init_database()
    
    def get_connection(self):
        """Get database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_database(self):
        """Initialize database tables"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Create crowd records table (minimalist design)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS crowd_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME NOT NULL UNIQUE,
                person_count INTEGER NOT NULL,
                weekday INTEGER NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create index to speed up queries
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_timestamp ON crowd_records(timestamp)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_weekday ON crowd_records(weekday)
        ''')
        
        conn.commit()
        conn.close()
        print(f"[✓] Database initialized: {self.db_path}")
    
    def add_record(self, timestamp, person_count, weekday=None):
        """Add a crowd record"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        dt = datetime.fromisoformat(timestamp) if isinstance(timestamp, str) else timestamp
        if weekday is None:
            weekday = dt.weekday()  # 0=Monday, 6=Sunday
        
        try:
            cursor.execute('''
                INSERT INTO crowd_records 
                (timestamp, person_count, weekday)
                VALUES (?, ?, ?)
            ''', (dt.isoformat(), person_count, weekday))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            # Duplicate timestamp, update record
            cursor.execute('''
                UPDATE crowd_records 
                SET person_count=?
                WHERE timestamp=?
            ''', (person_count, dt.isoformat()))
            conn.commit()
            return False
        finally:
            conn.close()
    
    def get_records_by_weekday(self, weekday):
        """Get all records for specified day of week"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM crowd_records 
            WHERE weekday = ?
            ORDER BY timestamp
        ''', (weekday,))
        
        records = cursor.fetchall()
        conn.close()
        return records
    
    def get_weekday_stats(self, weekday):
        """Get statistics for specified weekday"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                AVG(person_count) as avg_people,
                MAX(person_count) as max_people,
                MIN(person_count) as min_people,
                COUNT(*) as record_count
            FROM crowd_records 
            WHERE weekday = ?
        ''', (weekday,))
        
        result = cursor.fetchone()
        conn.close()
        return result


# Global database instance
db = None

def init_db(db_path=DB_PATH):
    """Initialize global database instance"""
    global db
    db = CrowdDatabase(db_path)
    return db

def get_db():
    """Get global database instance"""
    global db
    if db is None:
        db = init_db()
    return db

