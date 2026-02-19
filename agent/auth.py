import sqlite3
import json
import hashlib
import secrets
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple


def get_db_path() -> str:
    import sys
    if sys.platform == "win32":
        app_data = Path.home() / "AppData" / "Roaming" / "AcademicAssistant"
    else:
        app_data = Path.home() / ".academicassistant"
    
    app_data.mkdir(parents=True, exist_ok=True)
    return str(app_data / "academic.db")


def init_db():
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            created_at TEXT NOT NULL,
            last_login TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversations (
            id TEXT PRIMARY KEY,
            user_id INTEGER,
            title TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY,
            conversation_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            metadata TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (conversation_id) REFERENCES conversations (id)
        )
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages (conversation_id)
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations (user_id)
    ''')
    
    conn.commit()
    conn.close()


def hash_password(password: str, salt: str = None) -> Tuple[str, str]:
    if salt is None:
        salt = secrets.token_hex(16)
    password_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000).hex()
    return password_hash, salt


def verify_password(password: str, password_hash: str, salt: str) -> bool:
    computed_hash, _ = hash_password(password, salt)
    return computed_hash == password_hash


def create_user(username: str, password: str, email: str = None) -> Dict[str, Any]:
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        password_hash, salt = hash_password(password)
        now = datetime.now().isoformat()
        
        cursor.execute('''
            INSERT INTO users (username, email, password_hash, salt, created_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (username, email, password_hash, salt, now))
        
        user_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return {"success": True, "user_id": user_id, "username": username}
    except sqlite3.IntegrityError as e:
        if "username" in str(e):
            return {"success": False, "error": "用户名已存在"}
        elif "email" in str(e):
            return {"success": False, "error": "邮箱已被注册"}
        return {"success": False, "error": str(e)}
    except Exception as e:
        return {"success": False, "error": str(e)}


def authenticate_user(username: str, password: str) -> Dict[str, Any]:
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT id, username, password_hash, salt FROM users WHERE username = ?', (username,))
        row = cursor.fetchone()
        
        if not row:
            conn.close()
            return {"success": False, "error": "用户名或密码错误"}
        
        user_id, username, password_hash, salt = row
        
        if not verify_password(password, password_hash, salt):
            conn.close()
            return {"success": False, "error": "用户名或密码错误"}
        
        now = datetime.now().isoformat()
        cursor.execute('UPDATE users SET last_login = ? WHERE id = ?', (now, user_id))
        conn.commit()
        conn.close()
        
        return {
            "success": True,
            "user": {
                "id": user_id,
                "username": username
            }
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_user(user_id: int) -> Optional[Dict[str, Any]]:
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT id, username, email, created_at, last_login FROM users WHERE id = ?', (user_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        return {
            "id": row[0],
            "username": row[1],
            "email": row[2],
            "created_at": row[3],
            "last_login": row[4]
        }
    except Exception as e:
        print(f"Error getting user: {e}")
        return None


def create_conversation(user_id: int = None, title: str = None) -> Dict[str, Any]:
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        conversation_id = secrets.token_hex(8)
        now = datetime.now().isoformat()
        
        cursor.execute('''
            INSERT INTO conversations (id, user_id, title, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (conversation_id, user_id, title, now, now))
        
        conn.commit()
        conn.close()
        
        return {
            "success": True,
            "conversation": {
                "id": conversation_id,
                "user_id": user_id,
                "title": title,
                "created_at": now,
                "updated_at": now
            }
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def save_message(conversation_id: str, role: str, content: str, metadata: Dict = None) -> Dict[str, Any]:
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        message_id = secrets.token_hex(8)
        now = datetime.now().isoformat()
        metadata_json = json.dumps(metadata) if metadata else None
        
        cursor.execute('''
            INSERT INTO messages (id, conversation_id, role, content, metadata, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (message_id, conversation_id, role, content, metadata_json, now))
        
        cursor.execute('''
            UPDATE conversations SET updated_at = ? WHERE id = ?
        ''', (now, conversation_id))
        
        conn.commit()
        conn.close()
        
        return {
            "success": True,
            "message": {
                "id": message_id,
                "conversation_id": conversation_id,
                "role": role,
                "content": content,
                "metadata": metadata,
                "created_at": now
            }
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_conversation(conversation_id: str) -> Optional[Dict[str, Any]]:
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, user_id, title, created_at, updated_at 
            FROM conversations WHERE id = ?
        ''', (conversation_id,))
        row = cursor.fetchone()
        
        if not row:
            conn.close()
            return None
        
        conversation = {
            "id": row[0],
            "user_id": row[1],
            "title": row[2],
            "created_at": row[3],
            "updated_at": row[4],
            "messages": []
        }
        
        cursor.execute('''
            SELECT id, role, content, metadata, created_at 
            FROM messages WHERE conversation_id = ? ORDER BY created_at
        ''', (conversation_id,))
        
        for msg_row in cursor.fetchall():
            metadata = None
            if msg_row[3]:
                try:
                    metadata = json.loads(msg_row[3])
                except:
                    pass
            
            conversation["messages"].append({
                "id": msg_row[0],
                "role": msg_row[1],
                "content": msg_row[2],
                "metadata": metadata,
                "created_at": msg_row[4]
            })
        
        conn.close()
        return conversation
    except Exception as e:
        print(f"Error getting conversation: {e}")
        return None


def list_conversations(user_id: int = None, limit: int = 50) -> List[Dict[str, Any]]:
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        if user_id:
            cursor.execute('''
                SELECT id, user_id, title, created_at, updated_at 
                FROM conversations WHERE user_id = ? 
                ORDER BY updated_at DESC LIMIT ?
            ''', (user_id, limit))
        else:
            cursor.execute('''
                SELECT id, user_id, title, created_at, updated_at 
                FROM conversations 
                ORDER BY updated_at DESC LIMIT ?
            ''', (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        conversations = []
        for row in rows:
            conversations.append({
                "id": row[0],
                "user_id": row[1],
                "title": row[2],
                "created_at": row[3],
                "updated_at": row[4]
            })
        
        return conversations
    except Exception as e:
        print(f"Error listing conversations: {e}")
        return []


def delete_conversation(conversation_id: str) -> Dict[str, Any]:
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM messages WHERE conversation_id = ?', (conversation_id,))
        cursor.execute('DELETE FROM conversations WHERE id = ?', (conversation_id,))
        
        conn.commit()
        conn.close()
        
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


def search_conversations(query: str, user_id: int = None, limit: int = 20) -> List[Dict[str, Any]]:
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        search_pattern = f"%{query}%"
        
        if user_id:
            cursor.execute('''
                SELECT DISTINCT c.id, c.user_id, c.title, c.created_at, c.updated_at 
                FROM conversations c
                LEFT JOIN messages m ON c.id = m.conversation_id
                WHERE c.user_id = ? AND (c.title LIKE ? OR m.content LIKE ?)
                ORDER BY c.updated_at DESC LIMIT ?
            ''', (user_id, search_pattern, search_pattern, limit))
        else:
            cursor.execute('''
                SELECT DISTINCT c.id, c.user_id, c.title, c.created_at, c.updated_at 
                FROM conversations c
                LEFT JOIN messages m ON c.id = m.conversation_id
                WHERE c.title LIKE ? OR m.content LIKE ?
                ORDER BY c.updated_at DESC LIMIT ?
            ''', (search_pattern, search_pattern, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        conversations = []
        for row in rows:
            conversations.append({
                "id": row[0],
                "user_id": row[1],
                "title": row[2],
                "created_at": row[3],
                "updated_at": row[4]
            })
        
        return conversations
    except Exception as e:
        print(f"Error searching conversations: {e}")
        return []


init_db()
