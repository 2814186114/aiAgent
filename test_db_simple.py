import asyncio
import os
import sys
import sqlite3

_lib_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "python_libs")
if os.path.exists(_lib_path):
    sys.path.insert(0, _lib_path)

from agent.experiments import get_db_path, init_db


def test_db_basics():
    print("=" * 50)
    print("测试 1: 数据库基础功能")
    print("=" * 50)
    
    init_db()
    db_path = get_db_path()
    print(f"数据库路径: {db_path}")
    print(f"数据库存在: {os.path.exists(db_path)}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    print(f"表: {tables}")
    
    test_data = [
        ("BERT", "SST-2", "准确率", 92.3, "测试记录1"),
        ("GPT-2", "WikiText", "困惑度", 18.5, "测试记录2"),
    ]
    
    for model, dataset, metric, value, notes in test_data:
        cursor.execute('''
            INSERT INTO experiments (model, dataset, metric, value, notes)
            VALUES (?, ?, ?, ?, ?)
        ''', (model, dataset, metric, value, notes))
    
    conn.commit()
    
    cursor.execute("SELECT * FROM experiments")
    rows = cursor.fetchall()
    print(f"\n插入后记录数: {len(rows)}")
    
    for row in rows:
        print(f"  {row}")
    
    conn.close()
    
    print("\n✅ 数据库基础功能测试通过！")
    print()


if __name__ == "__main__":
    test_db_basics()
