import os
import sys
import sqlite3
import json
from typing import Dict, Any, List, Optional
from datetime import datetime

_lib_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "python_libs")
if os.path.exists(_lib_path):
    sys.path.insert(0, _lib_path)


def get_db_path() -> str:
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    user_data_dir = os.path.join(base_dir, "userData")
    os.makedirs(user_data_dir, exist_ok=True)
    return os.path.join(user_data_dir, "literature.db")


def init_db():
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS papers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            paper_id TEXT UNIQUE,
            title TEXT NOT NULL,
            authors TEXT,
            year INTEGER,
            abstract TEXT,
            url TEXT,
            pdf_url TEXT,
            added_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            last_read_at DATETIME,
            read_count INTEGER DEFAULT 0
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            paper_id TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (paper_id) REFERENCES papers (paper_id) ON DELETE CASCADE
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS paper_tags (
            paper_id TEXT NOT NULL,
            tag_id INTEGER NOT NULL,
            PRIMARY KEY (paper_id, tag_id),
            FOREIGN KEY (paper_id) REFERENCES papers (paper_id) ON DELETE CASCADE,
            FOREIGN KEY (tag_id) REFERENCES tags (id) ON DELETE CASCADE
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS folders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            description TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS folder_papers (
            folder_id INTEGER NOT NULL,
            paper_id TEXT NOT NULL,
            PRIMARY KEY (folder_id, paper_id),
            FOREIGN KEY (folder_id) REFERENCES folders (id) ON DELETE CASCADE,
            FOREIGN KEY (paper_id) REFERENCES papers (paper_id) ON DELETE CASCADE
        )
    ''')
    
    conn.commit()
    conn.close()


def add_paper(
    paper_id: str,
    title: str,
    authors: Optional[List[str]] = None,
    year: Optional[int] = None,
    abstract: Optional[str] = None,
    url: Optional[str] = None,
    pdf_url: Optional[str] = None
) -> Dict[str, Any]:
    init_db()
    
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        authors_str = json.dumps(authors) if authors else None
        
        cursor.execute('''
            INSERT OR REPLACE INTO papers 
            (paper_id, title, authors, year, abstract, url, pdf_url, added_at, last_read_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, NULL)
        ''', (
            paper_id, title, authors_str, year, abstract, url, pdf_url
        ))
        
        conn.commit()
        conn.close()
        
        return {
            "success": True,
            "paper_id": paper_id,
            "message": "论文已收藏"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"数据库错误: {str(e)}"
        }


def remove_paper(paper_id: str) -> Dict[str, Any]:
    init_db()
    
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM papers WHERE paper_id = ?', (paper_id,))
        
        if cursor.rowcount == 0:
            conn.close()
            return {
                "success": False,
                "error": "论文不存在"
            }
        
        conn.commit()
        conn.close()
        
        return {
            "success": True,
            "message": "论文已从收藏中移除"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"删除错误: {str(e)}"
        }


def is_paper_saved(paper_id: str) -> Dict[str, Any]:
    init_db()
    
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT id FROM papers WHERE paper_id = ?', (paper_id,))
        row = cursor.fetchone()
        
        conn.close()
        
        return {
            "success": True,
            "saved": row is not None
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"查询错误: {str(e)}",
            "saved": False
        }


def list_saved_papers(
    tag_filter: Optional[str] = None,
    folder_filter: Optional[int] = None,
    limit: int = 100
) -> Dict[str, Any]:
    init_db()
    
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        sql = '''
            SELECT DISTINCT p.* FROM papers p
        '''
        params = []
        
        if tag_filter:
            sql += '''
                JOIN paper_tags pt ON p.paper_id = pt.paper_id
                JOIN tags t ON pt.tag_id = t.id
                WHERE t.name = ?
            '''
            params.append(tag_filter)
        
        if folder_filter:
            if tag_filter:
                sql += ' AND '
            else:
                sql += ' WHERE '
            sql += '''
                p.paper_id IN (
                    SELECT paper_id FROM folder_papers WHERE folder_id = ?
                )
            '''
            params.append(folder_filter)
        
        if not tag_filter and not folder_filter:
            sql += ' WHERE 1=1'
        
        sql += ' ORDER BY p.added_at DESC LIMIT ?'
        params.append(limit)
        
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        
        papers = []
        for row in rows:
            paper = {
                "id": row["id"],
                "paper_id": row["paper_id"],
                "title": row["title"],
                "authors": json.loads(row["authors"]) if row["authors"] else [],
                "year": row["year"],
                "abstract": row["abstract"],
                "url": row["url"],
                "pdf_url": row["pdf_url"],
                "added_at": row["added_at"],
                "last_read_at": row["last_read_at"],
                "read_count": row["read_count"]
            }
            
            cursor.execute('''
                SELECT t.name FROM tags t
                JOIN paper_tags pt ON t.id = pt.tag_id
                WHERE pt.paper_id = ?
            ''', (paper["paper_id"],))
            tags = [t[0] for t in cursor.fetchall()]
            paper["tags"] = tags
            
            cursor.execute('''
                SELECT f.id, f.name FROM folders f
                JOIN folder_papers fp ON f.id = fp.folder_id
                WHERE fp.paper_id = ?
            ''', (paper["paper_id"],))
            folders = [{"id": f[0], "name": f[1]} for f in cursor.fetchall()]
            paper["folders"] = folders
            
            cursor.execute('SELECT id, content, created_at, updated_at FROM notes WHERE paper_id = ? ORDER BY created_at DESC', (paper["paper_id"],))
            notes = []
            for note_row in cursor.fetchall():
                notes.append({
                    "id": note_row[0],
                    "content": note_row[1],
                    "created_at": note_row[2],
                    "updated_at": note_row[3]
                })
            paper["notes"] = notes
            
            papers.append(paper)
        
        conn.close()
        
        return {
            "success": True,
            "total": len(papers),
            "papers": papers
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"查询错误: {str(e)}",
            "papers": []
        }


def add_tag(name: str) -> Dict[str, Any]:
    init_db()
    
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute('INSERT OR IGNORE INTO tags (name) VALUES (?)', (name,))
        
        conn.commit()
        conn.close()
        
        return {
            "success": True,
            "message": "标签已添加"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"添加错误: {str(e)}"
        }


def remove_tag(name: str) -> Dict[str, Any]:
    init_db()
    
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM tags WHERE name = ?', (name,))
        
        conn.commit()
        conn.close()
        
        return {
            "success": True,
            "message": "标签已删除"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"删除错误: {str(e)}"
        }


def list_tags() -> Dict[str, Any]:
    init_db()
    
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT name FROM tags ORDER BY name')
        rows = cursor.fetchall()
        
        tags = [row[0] for row in rows]
        
        conn.close()
        
        return {
            "success": True,
            "tags": tags
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"查询错误: {str(e)}",
            "tags": []
        }


def add_tag_to_paper(paper_id: str, tag_name: str) -> Dict[str, Any]:
    init_db()
    
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute('INSERT OR IGNORE INTO tags (name) VALUES (?)', (tag_name,))
        
        cursor.execute('SELECT id FROM tags WHERE name = ?', (tag_name,))
        tag_id = cursor.fetchone()[0]
        
        cursor.execute('INSERT OR IGNORE INTO paper_tags (paper_id, tag_id) VALUES (?, ?)', (paper_id, tag_id))
        
        conn.commit()
        conn.close()
        
        return {
            "success": True,
            "message": "标签已添加到论文"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"添加错误: {str(e)}"
        }


def remove_tag_from_paper(paper_id: str, tag_name: str) -> Dict[str, Any]:
    init_db()
    
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT id FROM tags WHERE name = ?', (tag_name,))
        tag_row = cursor.fetchone()
        
        if not tag_row:
            conn.close()
            return {
                "success": False,
                "error": "标签不存在"
            }
        
        cursor.execute('DELETE FROM paper_tags WHERE paper_id = ? AND tag_id = ?', (paper_id, tag_row[0]))
        
        conn.commit()
        conn.close()
        
        return {
            "success": True,
            "message": "标签已从论文移除"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"移除错误: {str(e)}"
        }


def add_note(paper_id: str, content: str) -> Dict[str, Any]:
    init_db()
    
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO notes (paper_id, content, created_at, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        ''', (paper_id, content))
        
        note_id = cursor.lastrowid
        
        conn.commit()
        conn.close()
        
        return {
            "success": True,
            "note_id": note_id,
            "message": "笔记已添加"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"添加错误: {str(e)}"
        }


def update_note(note_id: int, content: str) -> Dict[str, Any]:
    init_db()
    
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE notes SET content = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (content, note_id))
        
        if cursor.rowcount == 0:
            conn.close()
            return {
                "success": False,
                "error": "笔记不存在"
            }
        
        conn.commit()
        conn.close()
        
        return {
            "success": True,
            "message": "笔记已更新"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"更新错误: {str(e)}"
        }


def delete_note(note_id: int) -> Dict[str, Any]:
    init_db()
    
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM notes WHERE id = ?', (note_id,))
        
        if cursor.rowcount == 0:
            conn.close()
            return {
                "success": False,
                "error": "笔记不存在"
            }
        
        conn.commit()
        conn.close()
        
        return {
            "success": True,
            "message": "笔记已删除"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"删除错误: {str(e)}"
        }


def add_folder(name: str, description: Optional[str] = None) -> Dict[str, Any]:
    init_db()
    
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute('INSERT INTO folders (name, description) VALUES (?, ?)', (name, description))
        
        folder_id = cursor.lastrowid
        
        conn.commit()
        conn.close()
        
        return {
            "success": True,
            "folder_id": folder_id,
            "message": "文件夹已创建"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"创建错误: {str(e)}"
        }


def delete_folder(folder_id: int) -> Dict[str, Any]:
    init_db()
    
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM folders WHERE id = ?', (folder_id,))
        
        if cursor.rowcount == 0:
            conn.close()
            return {
                "success": False,
                "error": "文件夹不存在"
            }
        
        conn.commit()
        conn.close()
        
        return {
            "success": True,
            "message": "文件夹已删除"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"删除错误: {str(e)}"
        }


def list_folders() -> Dict[str, Any]:
    init_db()
    
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT id, name, description, created_at FROM folders ORDER BY created_at DESC')
        rows = cursor.fetchall()
        
        folders = []
        for row in rows:
            folder = {
                "id": row["id"],
                "name": row["name"],
                "description": row["description"],
                "created_at": row["created_at"]
            }
            
            cursor.execute('SELECT COUNT(*) FROM folder_papers WHERE folder_id = ?', (folder["id"],))
            folder["paper_count"] = cursor.fetchone()[0]
            
            folders.append(folder)
        
        conn.close()
        
        return {
            "success": True,
            "folders": folders
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"查询错误: {str(e)}",
            "folders": []
        }


def add_paper_to_folder(paper_id: str, folder_id: int) -> Dict[str, Any]:
    init_db()
    
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute('INSERT OR IGNORE INTO folder_papers (folder_id, paper_id) VALUES (?, ?)', (folder_id, paper_id))
        
        conn.commit()
        conn.close()
        
        return {
            "success": True,
            "message": "论文已添加到文件夹"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"添加错误: {str(e)}"
        }


def remove_paper_from_folder(paper_id: str, folder_id: int) -> Dict[str, Any]:
    init_db()
    
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM folder_papers WHERE folder_id = ? AND paper_id = ?', (folder_id, paper_id))
        
        conn.commit()
        conn.close()
        
        return {
            "success": True,
            "message": "论文已从文件夹移除"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"移除错误: {str(e)}"
        }


def mark_paper_read(paper_id: str) -> Dict[str, Any]:
    init_db()
    
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE papers 
            SET last_read_at = CURRENT_TIMESTAMP, read_count = read_count + 1
            WHERE paper_id = ?
        ''', (paper_id,))
        
        if cursor.rowcount == 0:
            conn.close()
            return {
                "success": False,
                "error": "论文不存在"
            }
        
        conn.commit()
        conn.close()
        
        return {
            "success": True,
            "message": "阅读记录已更新"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"更新错误: {str(e)}"
        }
