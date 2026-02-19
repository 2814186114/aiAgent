import os
import sys
import sqlite3
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

_lib_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "python_libs")
if os.path.exists(_lib_path):
    sys.path.insert(0, _lib_path)


def get_db_path() -> str:
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    user_data_dir = os.path.join(base_dir, "userData")
    os.makedirs(user_data_dir, exist_ok=True)
    return os.path.join(user_data_dir, "experiments.db")


def init_reading_history_db():
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reading_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_path TEXT,
            title TEXT,
            summary TEXT,
            read_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            total_pages INTEGER,
            source TEXT
        )
    ''')
    
    conn.commit()
    conn.close()


async def add_reading_history(
    file_path: str, 
    title: Optional[str] = None, 
    summary: Optional[str] = None,
    total_pages: Optional[int] = None,
    source: str = "pdf"
) -> Dict[str, Any]:
    init_reading_history_db()
    
    if not title:
        title = os.path.basename(file_path)
    
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO reading_history (file_path, title, summary, total_pages, source)
            VALUES (?, ?, ?, ?, ?)
        ''', (file_path, title, summary, total_pages, source))
        
        history_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return {
            "success": True,
            "id": history_id,
            "message": "阅读历史已记录"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"记录阅读历史失败: {str(e)}"
        }


async def get_recent_readings(days: int = 7) -> Dict[str, Any]:
    init_reading_history_db()
    
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        since_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        cursor.execute('''
            SELECT * FROM reading_history 
            WHERE read_at >= ?
            ORDER BY read_at DESC
            LIMIT 20
        ''', (since_date,))
        
        rows = cursor.fetchall()
        
        readings = []
        for row in rows:
            readings.append({
                "id": row["id"],
                "file_path": row["file_path"],
                "title": row["title"],
                "summary": row["summary"],
                "read_at": row["read_at"],
                "total_pages": row["total_pages"],
                "source": row["source"]
            })
        
        conn.close()
        
        return {
            "success": True,
            "total": len(readings),
            "readings": readings
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"查询阅读历史失败: {str(e)}"
        }
