import os
import sys
import json
from typing import Dict, Any, List
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

try:
    from .experiments import list_reminders, list_experiments
    from .reading_history import get_recent_readings
    DATA_AVAILABLE = True
except ImportError:
    DATA_AVAILABLE = False


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


async def generate_ppt_outline(
    user_request: str,
    experiments: List[Dict[str, Any]] = None,
    readings: List[Dict[str, Any]] = None
) -> Dict[str, Any]:
    client = get_llm_client()
    
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    experiments_text = ""
    if experiments:
        experiments_text = "最近实验记录：\n"
        for exp in experiments[:5]:
            line = f"- {exp.get('model', 'N/A')} on {exp.get('dataset', 'N/A')}"
            if exp.get('metric') and exp.get('value') is not None:
                line += f": {exp['metric']} = {exp['value']}"
            experiments_text += line + "\n"
    
    readings_text = ""
    if readings:
        readings_text = "最近阅读文献：\n"
        for reading in readings[:5]:
            readings_text += f"- {reading.get('title', 'N/A')}\n"
    
    system_prompt = """你是一个PPT大纲生成器。根据用户的请求和提供的实验记录、文献阅读记录，生成一个PPT大纲。

请返回JSON格式，包含以下字段：
{
  "title": "PPT标题",
  "sections": [
    {
      "title": "章节标题",
      "bullets": ["要点1", "要点2", "要点3"]
    }
  ]
}

常见的章节结构：
- 封面/目录
- 本周工作总结
- 文献调研进展
- 实验结果展示
- 遇到的问题
- 下一步计划

只返回JSON，不要包含其他文字。"""

    user_prompt = f"""当前日期：{today_str}

用户请求：{user_request}

{experiments_text}

{readings_text}

请生成PPT大纲。"""
    
    if not client:
        return {
            "success": True,
            "outline": {
                "title": f"工作汇报 - {today_str}",
                "sections": [
                    {
                        "title": "本周工作总结",
                        "bullets": ["完成了相关实验工作", "阅读了相关文献", "进行了数据整理"]
                    },
                    {
                        "title": "实验进展",
                        "bullets": [f"{exp.get('model', '实验')} on {exp.get('dataset', '数据集')}" for exp in (experiments or [])[:3]] or ["实验进行中"]
                    },
                    {
                        "title": "下一步计划",
                        "bullets": ["继续优化实验", "补充相关实验", "整理结果文档"]
                    }
                ]
            },
            "note": "使用默认大纲（LLM不可用）"
        }
    
    try:
        response = client.chat.completions.create(
            model="deepseek-chat" if os.getenv("LLM_PROVIDER") == "deepseek" else "gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            response_format={"type": "json_object"}
        )
        
        content = response.choices[0].message.content
        result = json.loads(content)
        
        return {
            "success": True,
            "outline": result
        }
    except Exception as e:
        return {
            "success": True,
            "outline": {
                "title": f"工作汇报 - {today_str}",
                "sections": [
                    {
                        "title": "本周工作总结",
                        "bullets": ["完成了相关实验工作", "阅读了相关文献", "进行了数据整理"]
                    },
                    {
                        "title": "实验进展",
                        "bullets": ["实验进行中"]
                    },
                    {
                        "title": "下一步计划",
                        "bullets": ["继续优化实验", "补充相关实验", "整理结果文档"]
                    }
                ]
            },
            "note": f"使用默认大纲（LLM调用失败: {str(e)}）"
        }


async def generate_ppt(user_request: str) -> Dict[str, Any]:
    experiments = []
    readings = []
    
    try:
        if DATA_AVAILABLE:
            from .experiments import list_experiments_query
            from .reading_history import get_recent_readings
            
            try:
                exp_result = await list_experiments_query("", limit=20)
                if exp_result.get("success"):
                    experiments = exp_result.get("experiments", [])
            except:
                pass
            
            try:
                read_result = await get_recent_readings(days=7)
                if read_result.get("success"):
                    readings = read_result.get("readings", [])
            except:
                pass
    except:
        pass
    
    outline_result = await generate_ppt_outline(user_request, experiments, readings)
    
    if not outline_result.get("success"):
        return outline_result
    
    return {
        "success": True,
        "outline": outline_result.get("outline"),
        "experiments_used": len(experiments),
        "readings_used": len(readings),
        "note": outline_result.get("note")
    }
