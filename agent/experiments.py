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


def init_db():
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS experiments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            model TEXT,
            dataset TEXT,
            metric TEXT,
            value REAL,
            notes TEXT
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


def simple_parse_experiment(note: str) -> Dict[str, Any]:
    import re
    
    model = None
    dataset = None
    metric = None
    value = None
    
    model_keywords = ['BERT', 'GPT', 'ResNet', 'Transformer', 'CNN', 'RNN', 'LSTM', 'ViT', 'T5', 'LLaMA']
    for keyword in model_keywords:
        if keyword.lower() in note.lower():
            pattern = rf'({keyword}[-]?\d*)'
            match = re.search(pattern, note, re.IGNORECASE)
            if match:
                model = match.group(1)
                break
    
    dataset_keywords = ['SST-2', 'ImageNet', 'MNLI', 'COCO', 'WikiText', 'CIFAR', 'GLUE']
    for keyword in dataset_keywords:
        if keyword.lower() in note.lower():
            dataset = keyword
            break
    
    metric_patterns = [
        (r'准确率[：:]\s*([\d.]+)', '准确率'),
        (r'accuracy[：:]\s*([\d.]+)', 'accuracy'),
        (r'loss[：:]\s*([\d.]+)', 'loss'),
        (r'困惑度[：:]\s*([\d.]+)', '困惑度'),
        (r'困惑度是\s*([\d.]+)', '困惑度'),
        (r'perplexity[：:]\s*([\d.]+)', 'perplexity'),
        (r'F1[：:]\s*([\d.]+)', 'F1'),
        (r'([\d.]+)%', '准确率'),
    ]
    
    for pattern, metric_name in metric_patterns:
        match = re.search(pattern, note)
        if match:
            try:
                value = float(match.group(1))
                metric = metric_name
                break
            except ValueError:
                continue
    
    if value is None:
        num_match = re.search(r'[：:是]\s*([\d.]+)', note)
        if num_match:
            try:
                value = float(num_match.group(1))
                if '困惑' in note or 'perplexity' in note.lower():
                    metric = '困惑度'
                elif 'loss' in note.lower():
                    metric = 'loss'
                elif 'F1' in note:
                    metric = 'F1'
                else:
                    metric = '结果'
            except ValueError:
                pass
    
    return {
        "model": model,
        "dataset": dataset,
        "metric": metric,
        "value": value,
        "notes": note
    }


async def parse_experiment_note(note: str) -> Dict[str, Any]:
    client = get_llm_client()
    
    simple_result = simple_parse_experiment(note)
    
    if not client:
        return {
            "success": True,
            "data": simple_result,
            "note": "使用简单规则解析"
        }
    
    system_prompt = """你是一个实验记录解析器。将用户的自然语言实验记录转换为结构化JSON格式。

请提取以下字段：
- model: 模型名称（如 BERT, GPT-4, ResNet 等）
- dataset: 数据集名称（如 SST-2, ImageNet, MNLI 等）
- metric: 评估指标（如 准确率, accuracy, F1, loss, perplexity 等）
- value: 数值结果（浮点数）
- notes: 原始记录文本或补充备注

如果某个字段无法确定，请设为 null。
只返回JSON，不要包含其他文字。"""

    user_prompt = f"解析这条实验记录：\n{note}\n\n返回JSON格式："
    
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
                "model": result.get("model") or simple_result.get("model"),
                "dataset": result.get("dataset") or simple_result.get("dataset"),
                "metric": result.get("metric") or simple_result.get("metric"),
                "value": result.get("value") or simple_result.get("value"),
                "notes": result.get("notes") or note
            }
        }
    except Exception as e:
        return {
            "success": True,
            "data": simple_result,
            "note": f"LLM解析失败，使用规则解析: {str(e)}"
        }


async def add_experiment(note: str) -> Dict[str, Any]:
    init_db()
    
    parse_result = await parse_experiment_note(note)
    
    if parse_result.get("success"):
        data = parse_result["data"]
    else:
        data = parse_result.get("fallback", {
            "model": None,
            "dataset": None,
            "metric": None,
            "value": None,
            "notes": note
        })
    
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO experiments (model, dataset, metric, value, notes)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            data.get("model"),
            data.get("dataset"),
            data.get("metric"),
            data.get("value"),
            data.get("notes")
        ))
        
        exp_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return {
            "success": True,
            "id": exp_id,
            "data": data,
            "message": "实验记录已添加"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"数据库错误: {str(e)}"
        }


async def parse_query_to_conditions(query: str) -> Dict[str, Any]:
    client = get_llm_client()
    
    if not client:
        return {
            "success": False,
            "error": "LLM不可用，使用关键词匹配",
            "fallback": query
        }
    
    system_prompt = """你是一个实验查询解析器。将用户的自然语言查询转换为SQL查询条件。

请返回JSON格式，包含以下字段：
- conditions: 条件列表，每个条件包含 field（字段名）, operator（操作符）, value（值）
  可用字段: model, dataset, metric, value, timestamp
  可用操作符: =, !=, >, <, >=, <=, LIKE
- time_range: 时间范围（可选），可选值: today, yesterday, week, month, all
- limit: 返回数量限制（可选，默认10）

示例1：
查询: "BERT的实验"
返回: {"conditions": [{"field": "model", "operator": "LIKE", "value": "%BERT%"}], "limit": 10}

示例2：
查询: "上周的准确率超过90%的实验"
返回: {"conditions": [{"field": "metric", "operator": "LIKE", "value": "%准确率%"}, {"field": "value", "operator": ">", "value": 90}], "time_range": "week", "limit": 10}

只返回JSON，不要包含其他文字。"""

    try:
        response = client.chat.completions.create(
            model="deepseek-chat" if os.getenv("LLM_PROVIDER") == "deepseek" else "gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"解析查询：{query}"}
            ],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        
        content = response.choices[0].message.content
        result = json.loads(content)
        
        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"解析失败: {str(e)}",
            "fallback": query
        }


def get_time_condition(time_range: str) -> Optional[str]:
    now = datetime.now()
    
    if time_range == "today":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        return f"timestamp >= '{start.isoformat()}'"
    elif time_range == "yesterday":
        yesterday = now - timedelta(days=1)
        start = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
        end = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)
        return f"timestamp BETWEEN '{start.isoformat()}' AND '{end.isoformat()}'"
    elif time_range == "week":
        week_ago = now - timedelta(days=7)
        return f"timestamp >= '{week_ago.isoformat()}'"
    elif time_range == "month":
        month_ago = now - timedelta(days=30)
        return f"timestamp >= '{month_ago.isoformat()}'"
    
    return None


async def query_experiments(query: str = "", limit: int = 10) -> Dict[str, Any]:
    init_db()
    
    parse_result = await parse_query_to_conditions(query)
    
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        sql = "SELECT * FROM experiments"
        conditions = []
        params = []
        
        if parse_result.get("success"):
            data = parse_result["data"]
            
            for cond in data.get("conditions", []):
                field = cond.get("field")
                operator = cond.get("operator")
                value = cond.get("value")
                
                if field in ["model", "dataset", "metric", "value", "timestamp"]:
                    conditions.append(f"{field} {operator} ?")
                    params.append(value)
            
            time_range = data.get("time_range")
            if time_range:
                time_cond = get_time_condition(time_range)
                if time_cond:
                    conditions.append(time_cond)
            
            limit = data.get("limit", limit)
        else:
            keywords = query.lower().split()
            for keyword in keywords:
                if keyword:
                    conditions.append("(model LIKE ? OR dataset LIKE ? OR metric LIKE ? OR notes LIKE ?)")
                    pattern = f"%{keyword}%"
                    params.extend([pattern, pattern, pattern, pattern])
        
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        
        sql += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        
        experiments = []
        for row in rows:
            experiments.append({
                "id": row["id"],
                "timestamp": row["timestamp"],
                "model": row["model"],
                "dataset": row["dataset"],
                "metric": row["metric"],
                "value": row["value"],
                "notes": row["notes"]
            })
        
        conn.close()
        
        return {
            "success": True,
            "total": len(experiments),
            "experiments": experiments
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"查询错误: {str(e)}"
        }


async def get_experiment(exp_id: int) -> Dict[str, Any]:
    init_db()
    
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM experiments WHERE id = ?', (exp_id,))
        row = cursor.fetchone()
        
        if not row:
            conn.close()
            return {
                "success": False,
                "error": "实验记录不存在"
            }
        
        experiment = {
            "id": row["id"],
            "timestamp": row["timestamp"],
            "model": row["model"],
            "dataset": row["dataset"],
            "metric": row["metric"],
            "value": row["value"],
            "notes": row["notes"]
        }
        
        conn.close()
        
        return {
            "success": True,
            "experiment": experiment
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"获取错误: {str(e)}"
        }


async def update_experiment(
    exp_id: int,
    model: Optional[str] = None,
    dataset: Optional[str] = None,
    metric: Optional[str] = None,
    value: Optional[float] = None,
    notes: Optional[str] = None
) -> Dict[str, Any]:
    init_db()
    
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        updates = []
        params = []
        
        if model is not None:
            updates.append("model = ?")
            params.append(model)
        if dataset is not None:
            updates.append("dataset = ?")
            params.append(dataset)
        if metric is not None:
            updates.append("metric = ?")
            params.append(metric)
        if value is not None:
            updates.append("value = ?")
            params.append(value)
        if notes is not None:
            updates.append("notes = ?")
            params.append(notes)
        
        if not updates:
            conn.close()
            return {
                "success": False,
                "error": "没有提供要更新的字段"
            }
        
        params.append(exp_id)
        
        sql = f"UPDATE experiments SET {', '.join(updates)} WHERE id = ?"
        cursor.execute(sql, params)
        
        if cursor.rowcount == 0:
            conn.close()
            return {
                "success": False,
                "error": "实验记录不存在"
            }
        
        conn.commit()
        conn.close()
        
        return {
            "success": True,
            "message": "实验记录已更新"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"更新错误: {str(e)}"
        }


async def delete_experiment(exp_id: int) -> Dict[str, Any]:
    init_db()
    
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM experiments WHERE id = ?', (exp_id,))
        
        if cursor.rowcount == 0:
            conn.close()
            return {
                "success": False,
                "error": "实验记录不存在"
            }
        
        conn.commit()
        conn.close()
        
        return {
            "success": True,
            "message": "实验记录已删除"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"删除错误: {str(e)}"
        }


async def list_all_experiments(
    model_filter: Optional[str] = None,
    dataset_filter: Optional[str] = None,
    metric_filter: Optional[str] = None,
    limit: int = 100
) -> Dict[str, Any]:
    init_db()
    
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        sql = "SELECT * FROM experiments"
        conditions = []
        params = []
        
        if model_filter:
            conditions.append("model LIKE ?")
            params.append(f"%{model_filter}%")
        if dataset_filter:
            conditions.append("dataset LIKE ?")
            params.append(f"%{dataset_filter}%")
        if metric_filter:
            conditions.append("metric LIKE ?")
            params.append(f"%{metric_filter}%")
        
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        
        sql += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        
        experiments = []
        for row in rows:
            experiments.append({
                "id": row["id"],
                "timestamp": row["timestamp"],
                "model": row["model"],
                "dataset": row["dataset"],
                "metric": row["metric"],
                "value": row["value"],
                "notes": row["notes"]
            })
        
        conn.close()
        
        return {
            "success": True,
            "total": len(experiments),
            "experiments": experiments
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"查询错误: {str(e)}"
        }
