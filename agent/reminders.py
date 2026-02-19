import os
import sys
import sqlite3
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

_lib_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "python_libs")
if os.path.exists(_lib_path):
    sys.path.insert(0, _lib_path)

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    OpenAI = None

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def get_db_path() -> str:
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    user_data_dir = os.path.join(base_dir, "userData")
    os.makedirs(user_data_dir, exist_ok=True)
    return os.path.join(user_data_dir, "experiments.db")


def init_reminders_db():
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            datetime TEXT,
            recurring TEXT DEFAULT 'none',
            completed BOOLEAN DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()


def get_llm_client():
    if not OPENAI_AVAILABLE:
        return None
    
    llm_provider = os.getenv("LLM_PROVIDER", "deepseek")
    
    if llm_provider == "deepseek":
        api_key = os.getenv("DEEPSEEK_API_KEY")
        base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
    else:
        api_key = os.getenv("OPENAI_API_KEY")
        base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    
    if not api_key or api_key == "your_api_key_here":
        return None
    
    return OpenAI(api_key=api_key, base_url=base_url)


def simple_parse_reminder(note: str) -> Dict[str, Any]:
    import re
    
    title = note
    reminder_time = None
    recurring = "none"
    
    now = datetime.now()
    
    time_patterns = [
        (r'明天\s*(上午|下午|早上|晚上)?\s*(\d+)[点时]\s*(\d+)?分?', 'tomorrow'),
        (r'今天\s*(上午|下午|早上|晚上)?\s*(\d+)[点时]\s*(\d+)?分?', 'today'),
        (r'后天\s*(上午|下午|早上|晚上)?\s*(\d+)[点时]\s*(\d+)?分?', 'day_after'),
        (r'(\d+)[月/-](\d+)[日/-]?\s*(上午|下午|早上|晚上)?\s*(\d+)[点时]\s*(\d+)?分?', 'date_with_period'),
        (r'(\d+)[月/-](\d+)[日/-]?\s*(\d+)[点时]\s*(\d+)?分?', 'date'),
    ]
    
    for pattern, time_type in time_patterns:
        match = re.search(pattern, note)
        if match:
            groups = match.groups()
            
            if time_type == 'tomorrow':
                base_date = now + timedelta(days=1)
                period = groups[0] if groups[0] else ''
                hour = int(groups[1]) if len(groups) > 1 else 12
                minute = int(groups[2]) if (len(groups) > 2 and groups[2]) else 0
            elif time_type == 'today':
                base_date = now
                period = groups[0] if groups[0] else ''
                hour = int(groups[1]) if len(groups) > 1 else 12
                minute = int(groups[2]) if (len(groups) > 2 and groups[2]) else 0
            elif time_type == 'day_after':
                base_date = now + timedelta(days=2)
                period = groups[0] if groups[0] else ''
                hour = int(groups[1]) if len(groups) > 1 else 12
                minute = int(groups[2]) if (len(groups) > 2 and groups[2]) else 0
            elif time_type == 'date_with_period':
                month = int(groups[0])
                day = int(groups[1])
                period = groups[2] if groups[2] else ''
                hour = int(groups[3]) if len(groups) > 3 else 12
                minute = int(groups[4]) if (len(groups) > 4 and groups[4]) else 0
                base_date = datetime(now.year, month, day)
            elif time_type == 'date':
                month = int(groups[0])
                day = int(groups[1])
                hour = int(groups[2]) if len(groups) > 2 else 12
                minute = int(groups[3]) if (len(groups) > 3 and groups[3]) else 0
                period = ''
                base_date = datetime(now.year, month, day)
            else:
                base_date = now
                hour = 12
                minute = 0
                period = ''
            
            if '下午' in period or '晚上' in period:
                if hour < 12:
                    hour += 12
            
            reminder_time = base_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
            break
    
    if not reminder_time:
        reminder_time = now + timedelta(hours=1)
    
    if '每天' in note or 'daily' in note.lower():
        recurring = 'daily'
    elif '每周' in note or 'weekly' in note.lower():
        recurring = 'weekly'
    
    return {
        "title": title,
        "datetime": reminder_time.isoformat(),
        "recurring": recurring
    }


async def parse_reminder_note(note: str) -> Dict[str, Any]:
    client = get_llm_client()
    
    simple_result = simple_parse_reminder(note)
    
    if not client:
        return {
            "success": True,
            "data": simple_result,
            "note": "使用简单规则解析"
        }
    
    system_prompt = """你是一个日程提醒解析器。将用户的自然语言提醒转换为结构化JSON格式。

请提取以下字段：
- title: 提醒事项的标题
- datetime: ISO格式的日期时间，如 2026-02-15T15:00:00
- recurring: 重复类型，可选值: none, daily, weekly

如果某个字段无法确定，请合理推测。
只返回JSON，不要包含其他文字。"""

    now = datetime.now().isoformat()
    user_prompt = f"当前时间: {now}\n解析这条提醒：\n{note}\n\n返回JSON格式："
    
    try:
        response = client.chat.completions.create(
            model="deepseek-chat" if os.getenv("LLM_PROVIDER") == "deepseek" else "gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        
        content = response.choices[0].message.content
        result = json.loads(content)
        
        return {
            "success": True,
            "data": {
                "title": result.get("title") or simple_result.get("title"),
                "datetime": result.get("datetime") or simple_result.get("datetime"),
                "recurring": result.get("recurring") or simple_result.get("recurring")
            }
        }
    except Exception as e:
        return {
            "success": True,
            "data": simple_result,
            "note": f"LLM解析失败，使用规则解析: {str(e)}"
        }


async def add_reminder(note: str) -> Dict[str, Any]:
    init_reminders_db()
    
    parse_result = await parse_reminder_note(note)
    
    if not parse_result.get("success"):
        return {
            "success": False,
            "error": parse_result.get("error")
        }
    
    data = parse_result["data"]
    
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO reminders (title, datetime, recurring, completed)
            VALUES (?, ?, ?, 0)
        ''', (
            data.get("title"),
            data.get("datetime"),
            data.get("recurring", "none")
        ))
        
        reminder_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return {
            "success": True,
            "id": reminder_id,
            "data": data,
            "message": "提醒已添加"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"数据库错误: {str(e)}"
        }


async def list_reminders(time_range: str = "all") -> Dict[str, Any]:
    init_reminders_db()
    
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        now = datetime.now()
        
        if time_range == "today":
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end = now.replace(hour=23, minute=59, second=59, microsecond=999999)
            cursor.execute('''
                SELECT * FROM reminders 
                WHERE datetime >= ? AND datetime <= ?
                ORDER BY datetime ASC
            ''', (start.isoformat(), end.isoformat()))
        elif time_range == "upcoming":
            cursor.execute('''
                SELECT * FROM reminders 
                WHERE datetime >= ? AND completed = 0
                ORDER BY datetime ASC
                LIMIT 10
            ''', (now.isoformat(),))
        else:
            cursor.execute('''
                SELECT * FROM reminders 
                ORDER BY datetime DESC
                LIMIT 20
            ''')
        
        rows = cursor.fetchall()
        
        reminders = []
        for row in rows:
            reminders.append({
                "id": row["id"],
                "title": row["title"],
                "datetime": row["datetime"],
                "recurring": row["recurring"],
                "completed": bool(row["completed"]),
                "created_at": row["created_at"]
            })
        
        conn.close()
        
        return {
            "success": True,
            "total": len(reminders),
            "reminders": reminders
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"查询错误: {str(e)}"
        }


async def delete_reminder(reminder_id: int) -> Dict[str, Any]:
    init_reminders_db()
    
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM reminders WHERE id = ?', (reminder_id,))
        
        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()
        
        if deleted:
            return {
                "success": True,
                "message": f"提醒 {reminder_id} 已删除"
            }
        else:
            return {
                "success": False,
                "error": f"未找到提醒 {reminder_id}"
            }
    except Exception as e:
        return {
            "success": False,
            "error": f"删除错误: {str(e)}"
        }


async def complete_reminder(reminder_id: int) -> Dict[str, Any]:
    init_reminders_db()
    
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute('UPDATE reminders SET completed = 1 WHERE id = ?', (reminder_id,))
        
        updated = cursor.rowcount > 0
        conn.commit()
        conn.close()
        
        if updated:
            return {
                "success": True,
                "message": f"提醒 {reminder_id} 已标记为完成"
            }
        else:
            return {
                "success": False,
                "error": f"未找到提醒 {reminder_id}"
            }
    except Exception as e:
        return {
            "success": False,
            "error": f"更新错误: {str(e)}"
        }


async def get_due_reminders() -> Dict[str, Any]:
    init_reminders_db()
    
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        now = datetime.now().isoformat()
        
        cursor.execute('''
            SELECT * FROM reminders 
            WHERE datetime <= ? AND completed = 0
            ORDER BY datetime ASC
        ''', (now,))
        
        rows = cursor.fetchall()
        
        reminders = []
        for row in rows:
            reminders.append({
                "id": row["id"],
                "title": row["title"],
                "datetime": row["datetime"],
                "recurring": row["recurring"],
                "completed": bool(row["completed"])
            })
        
        conn.close()
        
        return {
            "success": True,
            "total": len(reminders),
            "reminders": reminders
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"查询错误: {str(e)}"
        }
