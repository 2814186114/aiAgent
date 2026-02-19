import json
import asyncio
from typing import Dict, Any, List, Callable

TOOLS: Dict[str, Callable] = {}
ASYNC_TOOLS: Dict[str, Callable] = {}

def register_tool(name: str):
    def decorator(func: Callable):
        TOOLS[name] = func
        return func
    return decorator

def register_async_tool(name: str):
    def decorator(func: Callable):
        ASYNC_TOOLS[name] = func
        return func
    return decorator

@register_tool("search_web")
def search_web(query: str) -> str:
    return f"模拟搜索结果：找到3篇与'{query}'相关的论文\n1. 《深度学习在自然语言处理中的应用》\n2. 《基于Transformer的文本生成研究》\n3. 《学术文献自动摘要方法综述》"

@register_tool("read_file")
def read_file(path: str) -> str:
    return f"模拟文件内容：正在读取文件 '{path}'...\n[文件内容开始]\n这是一篇关于机器学习的论文摘要...\n本文提出了一种新的神经网络架构...\n[文件内容结束]"

@register_tool("send_email")
def send_email(recipient: str, content: str) -> str:
    return f"模拟邮件已发送\n收件人: {recipient}\n内容摘要: {content[:50]}..."

@register_tool("create_schedule")
def create_schedule(date: str, task: str) -> str:
    return f"模拟日程已创建\n日期: {date}\n任务: {task}\n状态: 已添加到日程表"

@register_tool("search_paper")
def search_paper(keyword: str, year: str = "2024") -> str:
    return f"模拟论文搜索结果：\n关键词: {keyword}\n年份: {year}\n找到5篇相关论文：\n1. Attention Is All You Need (2017)\n2. BERT: Pre-training of Deep Bidirectional Transformers (2019)\n3. GPT-4 Technical Report (2023)\n4. Chain-of-Thought Prompting Elicits Reasoning (2022)\n5. ReAct: Synergizing Reasoning and Acting (2023)"

try:
    from .literature import search_semantic_scholar
    @register_async_tool("search_semantic_scholar")
    async def async_search_semantic_scholar(query: str, limit: int = 5) -> Dict[str, Any]:
        result = await search_semantic_scholar(query, limit)
        if result.get("success"):
            papers = result.get("papers", [])
            output = f"搜索到 {len(papers)} 篇论文：\n"
            for i, paper in enumerate(papers, 1):
                authors_str = ", ".join(paper.get("authors", []))
                output += f"{i}. {paper['title']} ({paper.get('year', 'N/A')})\n"
                output += f"   作者: {authors_str}\n"
                output += f"   URL: {paper.get('url', '')}\n"
            return {
                "success": True,
                "papers": result.get("papers", []),
                "message": output
            }
        else:
            return {
                "success": False,
                "error": result.get("error", "未知错误")
            }
except ImportError:
    pass

try:
    from .literature_review import (
        generate_literature_review, 
        analyze_research_trends, 
        find_research_gaps,
        get_paper_citations,
        get_paper_references
    )
    
    @register_async_tool("generate_literature_review")
    async def async_generate_literature_review(query: str, paper_limit: int = 15) -> Dict[str, Any]:
        result = await generate_literature_review(query, paper_limit, include_citations=True)
        if result.get("success"):
            msg = f"文献综述生成完成！\n\n{result['summary']}\n\n"
            if result.get("highly_cited_papers"):
                msg += "**高影响力论文**:\n"
                for p in result["highly_cited_papers"][:3]:
                    msg += f"- {p.get('title')} ({p.get('year')}) - {p.get('citation_count', 0)} 引用\n"
            return {
                "success": True,
                "review": result,
                "message": msg
            }
        else:
            return {
                "success": False,
                "error": result.get("error", "生成失败")
            }
    
    @register_async_tool("analyze_research_trends")
    async def async_analyze_research_trends(query: str, years: int = 5) -> Dict[str, Any]:
        result = await analyze_research_trends(query, years)
        if result.get("success"):
            msg = f"研究趋势分析完成！\n\n"
            msg += f"时间范围: {result.get('year_range')}\n"
            msg += f"论文总数: {result.get('total_papers')}\n\n"
            if result.get("key_concepts"):
                msg += f"**核心概念**: {', '.join(result['key_concepts'][:5])}\n"
            if result.get("top_venues"):
                msg += f"**主要发表期刊**: {', '.join([v['venue'] for v in result['top_venues'][:3]])}\n"
            return {
                "success": True,
                "trends": result,
                "message": msg
            }
        else:
            return {
                "success": False,
                "error": result.get("error", "分析失败")
            }
    
    @register_async_tool("find_research_gaps")
    async def async_find_research_gaps(query: str) -> Dict[str, Any]:
        result = await find_research_gaps(query)
        if result.get("success"):
            msg = f"研究空白分析完成！\n\n"
            msg += f"分析了 {result.get('total_papers_analyzed')} 篇论文\n\n"
            if result.get("potential_gaps"):
                msg += "**潜在研究空白**:\n"
                for gap in result["potential_gaps"][:3]:
                    msg += f"- [{gap.get('type')}]: {gap.get('description')[:100]}...\n"
            return {
                "success": True,
                "gaps": result,
                "message": msg
            }
        else:
            return {
                "success": False,
                "error": result.get("error", "分析失败")
            }
    
    @register_async_tool("get_paper_citations")
    async def async_get_paper_citations(paper_id: str, limit: int = 20) -> Dict[str, Any]:
        result = await get_paper_citations(paper_id, limit)
        if result.get("success"):
            citations = result.get("citations", [])
            msg = f"找到 {len(citations)} 条引用:\n"
            for c in citations[:5]:
                msg += f"- {c.get('title')} ({c.get('year')})\n"
            return {
                "success": True,
                "citations": citations,
                "message": msg
            }
        else:
            return {
                "success": False,
                "error": result.get("error", "获取失败")
            }
    
    @register_async_tool("get_paper_references")
    async def async_get_paper_references(paper_id: str, limit: int = 20) -> Dict[str, Any]:
        result = await get_paper_references(paper_id, limit)
        if result.get("success"):
            references = result.get("references", [])
            msg = f"找到 {len(references)} 条参考文献:\n"
            for r in references[:5]:
                msg += f"- {r.get('title')} ({r.get('year')})\n"
            return {
                "success": True,
                "references": references,
                "message": msg
            }
        else:
            return {
                "success": False,
                "error": result.get("error", "获取失败")
            }
except ImportError:
    pass

try:
    from .pdf_tools import read_pdf, download_pdf, analyze_paper
    @register_async_tool("read_pdf")
    async def async_read_pdf(file_path: str, max_chars: int = 5000, parse_structure: bool = True) -> Dict[str, Any]:
        result = await read_pdf(file_path, max_chars, parse_structure)
        if result.get("success"):
            msg = f"PDF读取成功:\n总页数: {result['total_pages']}\n"
            if result.get("paper_summary"):
                summary = result["paper_summary"]
                if summary.get("title"):
                    msg += f"标题: {summary['title']}\n"
                if summary.get("authors"):
                    msg += f"作者: {', '.join(summary['authors'][:3])}\n"
                if summary.get("key_metrics"):
                    msg += f"关键指标: {', '.join(summary['key_metrics'][:3])}\n"
            return {
                "success": True,
                "total_pages": result['total_pages'],
                "summary": result.get('summary', ''),
                "paper_summary": result.get('paper_summary'),
                "abstract": result.get('abstract'),
                "message": msg
            }
        else:
            return {
                "success": False,
                "error": result.get('error')
            }
    
    @register_async_tool("analyze_paper")
    async def async_analyze_paper(file_path: str) -> Dict[str, Any]:
        result = await analyze_paper(file_path)
        if result.get("success"):
            msg = f"论文分析完成:\n"
            if result.get("title"):
                msg += f"标题: {result['title']}\n"
            if result.get("authors"):
                msg += f"作者: {', '.join(result['authors'][:3])}\n"
            if result.get("main_contributions"):
                msg += f"主要贡献: {result['main_contributions'][0][:100]}...\n"
            if result.get("datasets_used"):
                msg += f"数据集: {', '.join(result['datasets_used'])}\n"
            if result.get("metrics_reported"):
                msg += f"指标: {', '.join(result['metrics_reported'][:3])}\n"
            return {
                "success": True,
                "analysis": result,
                "message": msg
            }
        else:
            return {
                "success": False,
                "error": result.get('error')
            }
    
    @register_async_tool("download_pdf")
    async def async_download_pdf(url: str, save_path: str) -> Dict[str, Any]:
        result = await download_pdf(url, save_path)
        if result.get("success"):
            return {
                "success": True,
                "save_path": result['save_path'],
                "file_size": result['file_size'],
                "message": f"下载成功:\n保存到: {result['save_path']}\n文件大小: {result['file_size']} 字节"
            }
        else:
            return {
                "success": False,
                "error": result.get('error')
            }
except ImportError:
    pass

try:
    from .experiments import add_experiment, query_experiments
    @register_async_tool("add_experiment")
    async def async_add_experiment(note: str) -> Dict[str, Any]:
        result = await add_experiment(note)
        if result.get("success"):
            data = result['data']
            message = f"实验记录已添加 (ID: {result['id']})\n"
            if data.get('model'):
                message += f"模型: {data['model']}\n"
            if data.get('dataset'):
                message += f"数据集: {data['dataset']}\n"
            if data.get('metric') and data.get('value') is not None:
                message += f"指标: {data['metric']} = {data['value']}\n"
            return {
                "success": True,
                "data": data,
                "id": result['id'],
                "message": message
            }
        else:
            return {
                "success": False,
                "error": result.get('error')
            }
    
    @register_async_tool("query_experiments")
    async def async_query_experiments(query: str = "", limit: int = 10) -> Dict[str, Any]:
        result = await query_experiments(query, limit)
        if result.get("success"):
            experiments = result['experiments']
            message = f"找到 {result['total']} 条实验记录\n"
            for i, exp in enumerate(experiments[:5], 1):
                message += f"\n{i}. {exp.get('timestamp', '')}\n"
                if exp.get('model'):
                    message += f"   模型: {exp['model']}\n"
                if exp.get('dataset'):
                    message += f"   数据集: {exp['dataset']}\n"
                if exp.get('metric') and exp.get('value') is not None:
                    message += f"   {exp['metric']}: {exp['value']}\n"
            if len(experiments) > 5:
                message += f"\n... 还有 {len(experiments) - 5} 条记录"
            return {
                "success": True,
                "experiments": experiments,
                "total": result['total'],
                "message": message
            }
        else:
            return {
                "success": False,
                "error": result.get('error')
            }
except ImportError:
    pass

try:
    from .reminders import add_reminder, list_reminders, delete_reminder, complete_reminder
    @register_async_tool("add_reminder")
    async def async_add_reminder(note: str) -> Dict[str, Any]:
        result = await add_reminder(note)
        if result.get("success"):
            data = result['data']
            message = f"提醒已添加 (ID: {result['id']})\n"
            message += f"事项: {data['title']}\n"
            message += f"时间: {data['datetime']}\n"
            if data.get('recurring') and data['recurring'] != 'none':
                message += f"重复: {data['recurring']}\n"
            return {
                "success": True,
                "data": data,
                "id": result['id'],
                "message": message
            }
        else:
            return {
                "success": False,
                "error": result.get('error')
            }
    
    @register_async_tool("list_reminders")
    async def async_list_reminders(time_range: str = "all") -> Dict[str, Any]:
        result = await list_reminders(time_range)
        if result.get("success"):
            reminders = result['reminders']
            message = f"找到 {result['total']} 条提醒\n"
            for i, rem in enumerate(reminders[:5], 1):
                status = "✓" if rem.get('completed') else "○"
                message += f"\n{i}. {status} {rem.get('title')}\n"
                message += f"   时间: {rem.get('datetime')}\n"
            if len(reminders) > 5:
                message += f"\n... 还有 {len(reminders) - 5} 条"
            return {
                "success": True,
                "reminders": reminders,
                "total": result['total'],
                "message": message
            }
        else:
            return {
                "success": False,
                "error": result.get('error')
            }
    
    @register_async_tool("delete_reminder")
    async def async_delete_reminder(reminder_id: int) -> Dict[str, Any]:
        result = await delete_reminder(reminder_id)
        return result
    
    @register_async_tool("complete_reminder")
    async def async_complete_reminder(reminder_id: int) -> Dict[str, Any]:
        result = await complete_reminder(reminder_id)
        return result
except ImportError:
    pass

try:
    from .ppt_generator import generate_ppt
    @register_async_tool("generate_ppt")
    async def async_generate_ppt(user_request: str) -> Dict[str, Any]:
        result = await generate_ppt(user_request)
        if result.get("success"):
            outline = result['outline']
            message = f"PPT大纲已生成:\n标题: {outline['title']}\n"
            for i, section in enumerate(outline['sections'], 1):
                message += f"{i}. {section['title']}: {len(section['bullets'])} 要点\n"
            return {
                "success": True,
                "outline": outline,
                "message": message
            }
        else:
            return {
                "success": False,
                "error": result.get('error')
            }
except ImportError:
    pass

try:
    from .memory import get_memory_manager
    @register_async_tool("update_preference")
    async def async_update_preference(key: str, value: str) -> Dict[str, Any]:
        memory_manager = get_memory_manager()
        result = memory_manager.update_preference(key, value)
        if result.get("success"):
            return {
                "success": True,
                "key": key,
                "value": value,
                "message": f"偏好已更新: {key} = {value}"
            }
        else:
            return {
                "success": False,
                "error": result.get('error')
            }
    
    @register_async_tool("get_preference")
    async def async_get_preference(key: str, default: str = None) -> Dict[str, Any]:
        memory_manager = get_memory_manager()
        result = memory_manager.get_preference(key, default)
        if result.get("success"):
            value = result.get("value")
            return {
                "success": True,
                "key": key,
                "value": value,
                "message": f"{key} = {value}" if value is not None else f"{key} 未设置"
            }
        else:
            return {
                "success": False,
                "error": result.get('error'),
                "value": default
            }
except ImportError:
    pass

def get_tool_schemas() -> List[Dict[str, Any]]:
    schemas = [
        {
            "type": "function",
            "function": {
                "name": "search_web",
                "description": "搜索网络获取信息，可以搜索论文、资料等",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "搜索查询关键词"
                        }
                    },
                    "required": ["query"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "读取本地文件内容",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "文件路径"
                        }
                    },
                    "required": ["path"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "send_email",
                "description": "发送邮件给指定收件人",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "recipient": {
                            "type": "string",
                            "description": "收件人邮箱地址"
                        },
                        "content": {
                            "type": "string",
                            "description": "邮件内容"
                        }
                    },
                    "required": ["recipient", "content"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "create_schedule",
                "description": "创建日程安排",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "date": {
                            "type": "string",
                            "description": "日期，格式如 2024-01-15"
                        },
                        "task": {
                            "type": "string",
                            "description": "任务描述"
                        }
                    },
                    "required": ["date", "task"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "search_paper",
                "description": "搜索学术论文数据库",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "keyword": {
                            "type": "string",
                            "description": "论文关键词"
                        },
                        "year": {
                            "type": "string",
                            "description": "发表年份，可选"
                        }
                    },
                    "required": ["keyword"]
                }
            }
        }
    ]
    
    if "search_semantic_scholar" in ASYNC_TOOLS:
        schemas.append({
            "type": "function",
            "function": {
                "name": "search_semantic_scholar",
                "description": "使用Semantic Scholar API搜索学术论文",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "搜索查询关键词"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "返回结果数量，默认5",
                            "default": 5
                        }
                    },
                    "required": ["query"]
                }
            }
        })
    
    if "generate_literature_review" in ASYNC_TOOLS:
        schemas.append({
            "type": "function",
            "function": {
                "name": "generate_literature_review",
                "description": "生成文献综述，自动分析某领域的研究进展、高影响力论文、核心概念和时间线",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "研究主题或关键词，如'transformer attention mechanism'"
                        },
                        "paper_limit": {
                            "type": "integer",
                            "description": "分析论文数量，默认15",
                            "default": 15
                        }
                    },
                    "required": ["query"]
                }
            }
        })
    
    if "analyze_research_trends" in ASYNC_TOOLS:
        schemas.append({
            "type": "function",
            "function": {
                "name": "analyze_research_trends",
                "description": "分析某研究领域的发展趋势，包括论文数量变化、核心概念演变、主要发表期刊等",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "研究主题或关键词"
                        },
                        "years": {
                            "type": "integer",
                            "description": "分析最近几年的数据，默认5年",
                            "default": 5
                        }
                    },
                    "required": ["query"]
                }
            }
        })
    
    if "find_research_gaps" in ASYNC_TOOLS:
        schemas.append({
            "type": "function",
            "function": {
                "name": "find_research_gaps",
                "description": "从文献中识别潜在的研究空白和未来研究方向",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "研究主题或关键词"
                        }
                    },
                    "required": ["query"]
                }
            }
        })
    
    if "get_paper_citations" in ASYNC_TOOLS:
        schemas.append({
            "type": "function",
            "function": {
                "name": "get_paper_citations",
                "description": "获取某篇论文的引用列表，了解哪些后续工作引用了该论文",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "paper_id": {
                            "type": "string",
                            "description": "Semantic Scholar论文ID"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "返回引用数量，默认20",
                            "default": 20
                        }
                    },
                    "required": ["paper_id"]
                }
            }
        })
    
    if "get_paper_references" in ASYNC_TOOLS:
        schemas.append({
            "type": "function",
            "function": {
                "name": "get_paper_references",
                "description": "获取某篇论文的参考文献列表，了解该论文引用了哪些工作",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "paper_id": {
                            "type": "string",
                            "description": "Semantic Scholar论文ID"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "返回参考文献数量，默认20",
                            "default": 20
                        }
                    },
                    "required": ["paper_id"]
                }
            }
        })
    
    if "read_pdf" in ASYNC_TOOLS:
        schemas.append({
            "type": "function",
            "function": {
                "name": "read_pdf",
                "description": "读取PDF文件并提取文本，自动解析论文结构（标题、作者、摘要、方法等）",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "PDF文件完整路径"
                        },
                        "max_chars": {
                            "type": "integer",
                            "description": "提取字符数限制，默认5000",
                            "default": 5000
                        },
                        "parse_structure": {
                            "type": "boolean",
                            "description": "是否解析论文结构，默认true",
                            "default": True
                        }
                    },
                    "required": ["file_path"]
                }
            }
        })
    
    if "download_pdf" in ASYNC_TOOLS:
        schemas.append({
            "type": "function",
            "function": {
                "name": "download_pdf",
                "description": "下载PDF文件到本地",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "PDF文件下载URL"
                        },
                        "save_path": {
                            "type": "string",
                            "description": "保存路径"
                        }
                    },
                    "required": ["url", "save_path"]
                }
            }
        })
    
    if "analyze_paper" in ASYNC_TOOLS:
        schemas.append({
            "type": "function",
            "function": {
                "name": "analyze_paper",
                "description": "深度分析论文PDF，提取标题、作者、摘要、方法、实验结果等结构化信息",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "PDF文件完整路径"
                        }
                    },
                    "required": ["file_path"]
                }
            }
        })
    
    if "add_experiment" in ASYNC_TOOLS:
        schemas.append({
            "type": "function",
            "function": {
                "name": "add_experiment",
                "description": "添加实验记录，使用自然语言描述实验，系统会自动解析并保存到数据库",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "note": {
                            "type": "string",
                            "description": "实验记录的自然语言描述，例如：'今天跑了BERT在SST-2上的实验，准确率92.3%'"
                        }
                    },
                    "required": ["note"]
                }
            }
        })
    
    if "query_experiments" in ASYNC_TOOLS:
        schemas.append({
            "type": "function",
            "function": {
                "name": "query_experiments",
                "description": "查询实验记录，使用自然语言查询，例如：'上周的BERT实验'",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "自然语言查询，留空则返回最近的记录"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "返回记录数量，默认10",
                            "default": 10
                        }
                    },
                    "required": []
                }
            }
        })
    
    if "add_reminder" in ASYNC_TOOLS:
        schemas.append({
            "type": "function",
            "function": {
                "name": "add_reminder",
                "description": "添加日程提醒，使用自然语言描述，例如：'明天下午3点组会'",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "note": {
                            "type": "string",
                            "description": "提醒的自然语言描述"
                        }
                    },
                    "required": ["note"]
                }
            }
        })
    
    if "list_reminders" in ASYNC_TOOLS:
        schemas.append({
            "type": "function",
            "function": {
                "name": "list_reminders",
                "description": "查看日程提醒列表",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "time_range": {
                            "type": "string",
                            "description": "时间范围：all/today/upcoming，默认all",
                            "default": "all"
                        }
                    },
                    "required": []
                }
            }
        })
    
    if "delete_reminder" in ASYNC_TOOLS:
        schemas.append({
            "type": "function",
            "function": {
                "name": "delete_reminder",
                "description": "删除指定的日程提醒",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "reminder_id": {
                            "type": "integer",
                            "description": "提醒的ID"
                        }
                    },
                    "required": ["reminder_id"]
                }
            }
        })
    
    if "complete_reminder" in ASYNC_TOOLS:
        schemas.append({
            "type": "function",
            "function": {
                "name": "complete_reminder",
                "description": "标记提醒为已完成",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "reminder_id": {
                            "type": "integer",
                            "description": "提醒的ID"
                        }
                    },
                    "required": ["reminder_id"]
                }
            }
        })
    
    if "generate_ppt" in ASYNC_TOOLS:
        schemas.append({
            "type": "function",
            "function": {
                "name": "generate_ppt",
                "description": "基于实验记录和文献阅读历史生成PPT大纲",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "user_request": {
                            "type": "string",
                            "description": "用户的PPT生成请求，例如'生成本周组会汇报PPT'"
                        }
                    },
                    "required": ["user_request"]
                }
            }
        })
    
    if "update_preference" in ASYNC_TOOLS:
        schemas.append({
            "type": "function",
            "function": {
                "name": "update_preference",
                "description": "更新用户偏好设置",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "key": {
                            "type": "string",
                            "description": "偏好键，例如'preferred_paper_source'"
                        },
                        "value": {
                            "type": "string",
                            "description": "偏好值，例如'arxiv'"
                        }
                    },
                    "required": ["key", "value"]
                }
            }
        })
    
    if "get_preference" in ASYNC_TOOLS:
        schemas.append({
            "type": "function",
            "function": {
                "name": "get_preference",
                "description": "获取用户偏好设置",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "key": {
                            "type": "string",
                            "description": "偏好键，例如'preferred_paper_source'"
                        },
                        "default": {
                            "type": "string",
                            "description": "默认值，如果偏好未设置则返回此值"
                        }
                    },
                    "required": ["key"]
                }
            }
        })
    
    return schemas

def is_async_tool(tool_name: str) -> bool:
    return tool_name in ASYNC_TOOLS

async def execute_async_tool(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    if tool_name in ASYNC_TOOLS:
        try:
            return await ASYNC_TOOLS[tool_name](**arguments)
        except Exception as e:
            return {
                "success": False,
                "error": f"异步工具执行错误: {str(e)}"
            }
    elif tool_name in TOOLS:
        try:
            result = TOOLS[tool_name](**arguments)
            if isinstance(result, dict):
                return result
            return {
                "success": True,
                "message": result
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"工具执行错误: {str(e)}"
            }
    else:
        return {
            "success": False,
            "error": f"错误：未知工具 '{tool_name}'"
        }

def execute_tool(tool_name: str, arguments: Dict[str, Any]) -> str:
    if tool_name in TOOLS:
        try:
            return TOOLS[tool_name](**arguments)
        except Exception as e:
            return f"工具执行错误: {str(e)}"
    else:
        return f"错误：未知工具 '{tool_name}'"
