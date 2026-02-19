import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional


def get_db_path() -> str:
    import sys
    if sys.platform == "win32":
        app_data = Path.home() / "AppData" / "Roaming" / "AcademicAssistant"
    else:
        app_data = Path.home() / ".academicassistant"
    
    app_data.mkdir(parents=True, exist_ok=True)
    return str(app_data / "tasks.db")


def init_db():
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id TEXT PRIMARY KEY,
            task TEXT NOT NULL,
            answer TEXT,
            task_type TEXT,
            plan TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS task_steps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT NOT NULL,
            step_index INTEGER NOT NULL,
            step_type TEXT NOT NULL,
            content TEXT,
            tool_name TEXT,
            tool_arguments TEXT,
            tool_result TEXT,
            iteration INTEGER,
            created_at TEXT NOT NULL,
            FOREIGN KEY (task_id) REFERENCES tasks (id)
        )
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_task_steps_task_id ON task_steps (task_id)
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_tasks_created_at ON tasks (created_at DESC)
    ''')
    
    conn.commit()
    conn.close()


def save_task(task_id: str, task: str, answer: Optional[str], steps: List[Dict[str, Any]], 
              task_type: Optional[str] = None, plan: Optional[List] = None) -> Dict[str, Any]:
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        now = datetime.now().isoformat()
        plan_json = json.dumps(plan) if plan else None
        
        cursor.execute('''
            INSERT OR REPLACE INTO tasks (id, task, answer, task_type, plan, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, COALESCE((SELECT created_at FROM tasks WHERE id = ?), ?), ?)
        ''', (task_id, task, answer, task_type, plan_json, task_id, now, now))
        
        cursor.execute('DELETE FROM task_steps WHERE task_id = ?', (task_id,))
        
        for i, step in enumerate(steps):
            cursor.execute('''
                INSERT INTO task_steps 
                (task_id, step_index, step_type, content, tool_name, tool_arguments, tool_result, iteration, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                task_id,
                i,
                step.get('type', ''),
                step.get('content'),
                step.get('tool'),
                json.dumps(step.get('arguments')) if step.get('arguments') else None,
                json.dumps(step.get('tool_result')) if step.get('tool_result') else None,
                step.get('iteration', 0),
                now
            ))
        
        conn.commit()
        conn.close()
        
        return {"success": True, "task_id": task_id}
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_task(task_id: str) -> Optional[Dict[str, Any]]:
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT id, task, answer, task_type, plan, created_at, updated_at FROM tasks WHERE id = ?', (task_id,))
        task_row = cursor.fetchone()
        
        if not task_row:
            conn.close()
            return None
        
        cursor.execute('''
            SELECT step_index, step_type, content, tool_name, tool_arguments, tool_result, iteration, created_at
            FROM task_steps WHERE task_id = ? ORDER BY step_index
        ''', (task_id,))
        step_rows = cursor.fetchall()
        
        steps = []
        for row in step_rows:
            step = {
                "type": row[1],
                "content": row[2],
                "iteration": row[6]
            }
            if row[3]:
                step["tool"] = row[3]
            if row[4]:
                step["arguments"] = json.loads(row[4])
            if row[5]:
                step["tool_result"] = json.loads(row[5])
            steps.append(step)
        
        plan = None
        if task_row[4]:
            try:
                plan = json.loads(task_row[4])
            except:
                pass
        
        task = {
            "id": task_row[0],
            "task": task_row[1],
            "answer": task_row[2],
            "task_type": task_row[3],
            "plan": plan,
            "created_at": task_row[5],
            "updated_at": task_row[6],
            "steps": steps
        }
        
        conn.close()
        return task
    except Exception as e:
        print(f"Error getting task: {e}")
        return None


def list_tasks(limit: int = 50) -> List[Dict[str, Any]]:
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, task, answer, task_type, plan, created_at, updated_at
            FROM tasks ORDER BY created_at DESC LIMIT ?
        ''', (limit,))
        rows = cursor.fetchall()
        
        tasks = []
        for row in rows:
            plan = None
            if row[4]:
                try:
                    plan = json.loads(row[4])
                except:
                    pass
            tasks.append({
                "id": row[0],
                "task": row[1],
                "answer": row[2],
                "task_type": row[3],
                "plan": plan,
                "created_at": row[5],
                "updated_at": row[6]
            })
        
        conn.close()
        return tasks
    except Exception as e:
        print(f"Error listing tasks: {e}")
        return []


def delete_task(task_id: str) -> Dict[str, Any]:
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM task_steps WHERE task_id = ?', (task_id,))
        cursor.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
        
        conn.commit()
        conn.close()
        
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


init_db()