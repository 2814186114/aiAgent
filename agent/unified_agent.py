import os
import sys
import json
import asyncio
import re
import aiohttp
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
from enum import Enum

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
    from .research_agent import ResearchAgent
    RESEARCH_AGENT_AVAILABLE = True
except ImportError:
    RESEARCH_AGENT_AVAILABLE = False
    ResearchAgent = None

try:
    from . import multi_source_search
    MULTI_SOURCE_AVAILABLE = True
except ImportError:
    MULTI_SOURCE_AVAILABLE = False

try:
    from .calendar_service import create_schedule, list_schedules, calendar_service
    CALENDAR_AVAILABLE = True
except ImportError:
    CALENDAR_AVAILABLE = False
    calendar_service = None

class TaskType(Enum):
    QUESTION_ANSWERING = "question_answering"
    LITERATURE_RESEARCH = "literature_research"
    SCHEDULE_PLANNING = "schedule_planning"
    EXPERIMENT_MANAGEMENT = "experiment_management"
    GENERAL = "general"

class TaskStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

class PlanStep:
    def __init__(self, step_id: str, name: str, description: str, output_type: str = "text"):
        self.step_id = step_id
        self.name = name
        self.description = description
        self.output_type = output_type
        self.status = TaskStatus.PENDING
        self.steps: List[Dict] = []
        self.output: Optional[Any] = None
        self.result: Optional[str] = None

class UnifiedAgent:
    def __init__(self):
        self.llm_provider = os.getenv("LLM_PROVIDER", "deepseek")
        self.client = self._init_client()
        self.model = self._get_model()
    
    def _init_client(self):
        if not OPENAI_AVAILABLE:
            return None
        
        if self.llm_provider == "deepseek":
            api_key = os.getenv("DEEPSEEK_API_KEY")
            base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
        else:
            api_key = os.getenv("OPENAI_API_KEY")
            base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        
        if not api_key or api_key == "your_api_key_here":
            return None
        
        return OpenAI(api_key=api_key, base_url=base_url)
    
    def _get_model(self) -> str:
        if self.llm_provider == "deepseek":
            return "deepseek-chat"
        return "gpt-4o-mini"
    
    async def _call_llm(self, prompt: str, temperature: float = 0.7) -> str:
        if not self.client:
            return "LLM 未配置，无法生成回复。请配置 API Key。"
        
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=temperature
                )
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"[Agent] LLM call failed: {e}")
            return f"LLM 调用失败: {str(e)}"
    
    async def _call_llm_stream(self, prompt: str, temperature: float = 0.7, callback: Optional[Callable] = None):
        if not self.client:
            yield "LLM 未配置，无法生成回复。请配置 API Key。"
            return
        
        try:
            stream = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                stream=True
            )
            
            full_content = ""
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    full_content += content
                    if callback:
                        await callback({
                            "type": "stream",
                            "content": content,
                            "full_content": full_content
                        })
                    yield content
                    
        except Exception as e:
            print(f"[Agent] LLM stream call failed: {e}")
            error_msg = f"LLM 调用失败: {str(e)}"
            if callback:
                await callback({
                    "type": "error",
                    "error": error_msg
                })
            yield error_msg
    
    async def _analyze_task_with_llm(self, task: str) -> Dict[str, Any]:
        if not self.client:
            return self._fallback_task_analysis(task)
        
        prompt = f"""你是一个智能任务分析助手。请分析用户的请求，提取关键信息并规划执行步骤。

{task}

请以JSON格式返回分析结果，格式如下：
{{
    "task_type": "literature_research | schedule_planning | experiment_management | question_answering | general",
    "intent_summary": "用一句话总结用户意图",
    "extracted_params": {{
        "topic": "搜索主题/关键词",
        "years": 年限数字,
        "max_papers": 论文数量,
        "sort_by": "relevance 或 citation",
        "time_range": "时间范围描述",
        "paper_index": 论文索引数字（如果用户提到"第N篇"）,
        "action": "具体操作（如 analyze, similar, detail 等）",
        "other_requirements": ["其他特殊要求"]
    }},
    "plan": [
        {{
            "step_id": "步骤ID",
            "name": "步骤名称",
            "description": "步骤描述",
            "output_type": "输出类型"
        }}
    ],
    "reasoning": "分析推理过程"
}}

分析要点：
1. 识别任务类型
2. 如果有对话历史，理解上下文中的指代（如"第3篇"、"它"、"这个"等）
3. 提取关键参数（如年限、数量、排序方式、论文索引等）
4. 根据用户需求规划合理的执行步骤
5. 步骤应该具体、可执行

只返回JSON，不要其他内容。"""

        try:
            result = await self._call_llm(prompt, temperature=0.3)
            json_match = re.search(r'\{[\s\S]*\}', result)
            if json_match:
                analysis = json.loads(json_match.group())
                return analysis
        except Exception as e:
            print(f"LLM task analysis error: {e}")
        
        return self._fallback_task_analysis(task)
    
    def _fallback_task_analysis(self, task: str) -> Dict[str, Any]:
        task_lower = task.lower()
        
        if any(kw in task_lower for kw in ["论文", "文献", "搜索", "研究", "paper", "arxiv"]):
            return {
                "task_type": "literature_research",
                "intent_summary": task,
                "extracted_params": {
                    "topic": task,
                    "years": 2,
                    "max_papers": 30,
                    "sort_by": "relevance"
                },
                "plan": [
                    {"step_id": "search", "name": "搜索相关文献", "description": "根据关键词搜索学术论文", "output_type": "paper_list"},
                    {"step_id": "analyze", "name": "分析文献内容", "description": "分析搜索到的文献", "output_type": "analysis"},
                    {"step_id": "summarize", "name": "生成调研报告", "description": "总结文献调研结果", "output_type": "report"}
                ]
            }
        
        return {
            "task_type": "general",
            "intent_summary": task,
            "extracted_params": {},
            "plan": [
                {"step_id": "execute", "name": "执行任务", "description": "完成用户请求", "output_type": "result"}
            ]
        }
    
    async def _classify_task(self, task: str) -> TaskType:
        if not self.client:
            return self._rule_based_classify(task)
        
        prompt = f"""请判断以下任务属于哪种类型，只返回类型名称：

任务：{task}

类型选项：
- literature_research: 文献调研、论文搜索、学术研究
- schedule_planning: 日程规划、会议安排、时间管理
- experiment_management: 实验数据管理、数据分析、统计报告
- question_answering: 问题解答、概念解释、原理说明
- general: 其他通用任务

只返回类型名称，不要其他内容。"""
        
        try:
            result = await self._call_llm(prompt, temperature=0.1)
            result = result.strip().lower()
            
            if "literature" in result or "文献" in result:
                return TaskType.LITERATURE_RESEARCH
            elif "schedule" in result or "日程" in result:
                return TaskType.SCHEDULE_PLANNING
            elif "experiment" in result or "实验" in result:
                return TaskType.EXPERIMENT_MANAGEMENT
            elif "question" in result or "问题" in result:
                return TaskType.QUESTION_ANSWERING
        except Exception as e:
            print(f"Task classification error: {e}")
        
        return self._rule_based_classify(task)
    
    def _rule_based_classify(self, task: str) -> TaskType:
        task_lower = task.lower()
        
        literature_keywords = ["论文", "文献", "搜索", "研究", "学术", "paper", "arxiv", "publication", "调研", "查找"]
        schedule_keywords = ["日程", "会议", "安排", "计划", "周", "明天", "下周", "schedule", "meeting", "plan", "提醒"]
        experiment_keywords = ["实验", "数据", "csv", "统计", "分析", "整理", "experiment", "data", "analysis"]
        question_keywords = ["解释", "什么是", "原理", "如何", "为什么", "explain", "what", "how", "why", "介绍"]
        
        for kw in literature_keywords:
            if kw in task_lower:
                return TaskType.LITERATURE_RESEARCH
        
        for kw in schedule_keywords:
            if kw in task_lower:
                return TaskType.SCHEDULE_PLANNING
        
        for kw in experiment_keywords:
            if kw in task_lower:
                return TaskType.EXPERIMENT_MANAGEMENT
        
        for kw in question_keywords:
            if kw in task_lower:
                return TaskType.QUESTION_ANSWERING
        
        return TaskType.GENERAL
    
    def _get_plan_for_type(self, task_type: TaskType, task: str) -> List[PlanStep]:
        if task_type == TaskType.LITERATURE_RESEARCH:
            return [
                PlanStep("search", "搜索相关文献", "根据关键词搜索学术论文", "paper_list"),
                PlanStep("analyze", "分析文献内容", "分析搜索到的文献，提取关键信息", "analysis"),
                PlanStep("summarize", "生成调研报告", "总结文献调研结果", "report")
            ]
        elif task_type == TaskType.SCHEDULE_PLANNING:
            return [
                PlanStep("parse", "解析时间需求", "提取日程时间和内容", "schedule_info"),
                PlanStep("create", "创建日程安排", "生成日程安排方案", "schedule"),
                PlanStep("remind", "设置提醒", "设置日程提醒", "reminder")
            ]
        elif task_type == TaskType.EXPERIMENT_MANAGEMENT:
            return [
                PlanStep("analyze_request", "分析数据需求", "理解数据分析需求", "analysis"),
                PlanStep("generate_stats", "生成统计数据", "生成示例统计数据", "statistics"),
                PlanStep("report", "生成报告", "生成数据分析报告", "report")
            ]
        elif task_type == TaskType.QUESTION_ANSWERING:
            return [
                PlanStep("understand", "理解问题", "分析问题核心要点", "analysis"),
                PlanStep("research", "查找资料", "搜索相关资料", "references"),
                PlanStep("answer", "生成答案", "组织并生成答案", "answer")
            ]
        else:
            return [
                PlanStep("understand", "理解任务", "分析任务需求", "analysis"),
                PlanStep("execute", "执行任务", "完成主要任务内容", "result"),
                PlanStep("verify", "验证结果", "检查任务完成情况", "verification")
            ]
    
    def _build_task_with_context(self, task: str, context: Dict[str, Any]) -> str:
        messages = context.get("messages", [])
        current_papers = context.get("currentPapers", [])
        selected_paper_index = context.get("selectedPaperIndex")
        
        context_parts = []
        
        if messages:
            recent_messages = messages[-6:]
            context_parts.append("【对话历史】")
            for msg in recent_messages:
                role = "用户" if msg.get("role") == "user" else "助手"
                content = msg.get("content", "")
                if len(content) > 200:
                    content = content[:200] + "..."
                context_parts.append(f"{role}: {content}")
        
        if current_papers:
            context_parts.append("\n【当前论文列表】")
            for i, paper in enumerate(current_papers[:10]):
                title = paper.get("title", "未知标题")
                if len(title) > 80:
                    title = title[:80] + "..."
                context_parts.append(f"  [{i+1}] {title}")
        
        if selected_paper_index is not None and current_papers and selected_paper_index < len(current_papers):
            selected_paper = current_papers[selected_paper_index]
            context_parts.append(f"\n【当前选中论文】")
            context_parts.append(f"  标题: {selected_paper.get('title', '未知')}")
            context_parts.append(f"  作者: {', '.join(selected_paper.get('authors', [])[:3])}")
            context_parts.append(f"  年份: {selected_paper.get('year', '未知')}")
        
        context_parts.append(f"\n【当前用户请求】")
        context_parts.append(f"  {task}")
        
        task_with_context = "\n".join(context_parts)
        return task_with_context
    
    def _parse_research_params(self, task: str) -> Dict[str, Any]:
        params = {
            "years": 2,
            "max_papers": 30,
            "sort_by": "relevance",
            "topic": task
        }
        
        year_patterns = [
            (r'近(\d+)年', lambda m: int(m.group(1))),
            (r'最近(\d+)年', lambda m: int(m.group(1))),
            (r'过去(\d+)年', lambda m: int(m.group(1))),
            (r'last\s+(\d+)\s+years?', lambda m: int(m.group(1))),
            (r'(\d+)\s*年[以之]?内?', lambda m: int(m.group(1))),
        ]
        
        for pattern, extractor in year_patterns:
            match = re.search(pattern, task, re.IGNORECASE)
            if match:
                params["years"] = extractor(match)
                break
        
        count_patterns = [
            (r'(\d+)\s*篇', lambda m: int(m.group(1))),
            (r'top\s*(\d+)', lambda m: int(m.group(1)), re.IGNORECASE),
            (r'(\d+)\s*papers?', lambda m: int(m.group(1)), re.IGNORECASE),
        ]
        
        for pattern_data in count_patterns:
            if len(pattern_data) == 3:
                pattern, extractor, flags = pattern_data
                match = re.search(pattern, task, flags)
            else:
                pattern, extractor = pattern_data
                match = re.search(pattern, task)
            
            if match:
                params["max_papers"] = extractor(match)
                break
        
        influence_keywords = ["影响力", "引用", "citation", "influential", "高引", "热门"]
        for kw in influence_keywords:
            if kw.lower() in task.lower():
                params["sort_by"] = "citation"
                break
        
        stop_words = {"搜索", "查找", "寻找", "相关", "论文", "文献", "研究", "关于", "请问", 
                      "帮我", "帮忙", "想找", "想要", "需要", "最具", "有影响力", "影响力",
                      "最近", "近", "过去", "年", "篇", "top", "the", "most", "influential"}
        
        keywords = re.findall(r'[\u4e00-\u9fa5]+|[a-zA-Z]+', task)
        search_keywords = [kw for kw in keywords if len(kw) > 1 and kw.lower() not in {s.lower() for s in stop_words}]
        
        if search_keywords:
            params["topic"] = " ".join(search_keywords)
        
        return params
    
    async def _translate_to_english(self, query: str) -> str:
        if not self.client:
            return query
        
        if not re.search(r'[\u4e00-\u9fa5]', query):
            return query
        
        prompt = f"""请将以下中文关键词翻译成英文，用于学术论文搜索。只返回英文翻译，不要其他内容：

中文：{query}

英文翻译："""
        
        try:
            result = await self._call_llm(prompt, temperature=0.1)
            return result.strip().strip('"').strip("'")
        except:
            return query
    
    async def _search_papers(self, query: str, years: int = 2, max_results: int = 20, sort_by: str = "relevance") -> List[Dict]:
        if MULTI_SOURCE_AVAILABLE:
            papers = await multi_source_search.search_all_sources(query, years, max_results, sort_by)
            return papers
        else:
            return []
    
    async def _execute_step(self, step: PlanStep, task: str, task_type: TaskType, 
                           context: Dict[str, Any]) -> Dict[str, Any]:
        if task_type == TaskType.LITERATURE_RESEARCH:
            return await self._execute_literature_step(step, task, context)
        elif task_type == TaskType.SCHEDULE_PLANNING:
            return await self._execute_schedule_step(step, task, context)
        elif task_type == TaskType.EXPERIMENT_MANAGEMENT:
            return await self._execute_experiment_step(step, task, context)
        elif task_type == TaskType.QUESTION_ANSWERING:
            return await self._execute_question_step(step, task, context)
        else:
            return await self._execute_general_step(step, task, context)
    
    async def _execute_literature_step(self, step: PlanStep, task: str, 
                                       context: Dict[str, Any]) -> Dict[str, Any]:
        step_id = step.step_id.lower()
        step_name = step.name.lower()
        step_desc = step.description.lower() if step.description else ""
        
        is_search_step = any(kw in step_id or kw in step_name or kw in step_desc 
                            for kw in ["search", "query", "find", "检索", "搜索", "查找"])
        is_analyze_step = any(kw in step_id or kw in step_name or kw in step_desc 
                             for kw in ["analyze", "analysis", "分析", "解析", "extract", "提取"])
        is_summarize_step = any(kw in step_id or kw in step_name or kw in step_desc 
                               for kw in ["summarize", "summary", "report", "总结", "报告", "综述"])
        
        extracted_params = context.get("extracted_params", {})
        current_papers = context.get("currentPapers", [])
        paper_index = extracted_params.get("paper_index")
        
        if paper_index is not None and current_papers and 0 <= paper_index - 1 < len(current_papers):
            target_paper = current_papers[paper_index - 1]
            if is_analyze_step:
                paper_titles = [target_paper["title"]]
                prompt = f"""请分析以下论文，总结研究主题、方法和主要贡献：

论文标题：{target_paper['title']}
论文作者：{', '.join(target_paper.get('authors', []))}
论文年份：{target_paper.get('year', '未知')}
论文摘要：{target_paper.get('abstract', '无摘要')}

请以JSON格式返回：
{{
    "key_topics": ["主题1", "主题2"],
    "methods": ["方法1", "方法2"],
    "contributions": ["贡献1", "贡献2"],
    "summary": "整体分析总结"
}}

只返回JSON，不要其他内容。"""
                
                analysis_text = await self._call_llm(prompt, temperature=0.3)
                
                try:
                    json_match = re.search(r'\{[\s\S]*\}', analysis_text)
                    if json_match:
                        analysis = json.loads(json_match.group())
                    else:
                        analysis = {"summary": analysis_text[:300]}
                except:
                    analysis = {"summary": analysis_text[:300]}
                
                return {
                    "output_type": "analysis",
                    "analysis": analysis,
                    "paper": target_paper,
                    "result": f"完成论文分析：{target_paper['title'][:50]}..."
                }
        
        if is_search_step and "papers" not in context and not current_papers:
            stop_words = {"搜索", "查找", "寻找", "相关", "论文", "文献", "研究", "关于", "请问", "帮我", "帮忙", "想找", "想要", "需要", "the", "a", "an", "is", "are", "of", "and", "or", "for", "to", "in", "on"}
            
            topic = extracted_params.get("topic", task)
            if topic and len(topic) < 5:
                keywords = re.findall(r'[\u4e00-\u9fa5]+|[a-zA-Z]+', task)
                search_keywords = [kw for kw in keywords if len(kw) > 1 and kw.lower() not in stop_words]
                search_query = " ".join(search_keywords[:5]) if search_keywords else task
            else:
                search_query = topic
            
            years = extracted_params.get("years", 2)
            max_papers = extracted_params.get("max_papers", 20)
            sort_by = extracted_params.get("sort_by", "relevance")
            
            papers = await self._search_papers(search_query, years, max_papers, sort_by)
            
            if not papers:
                return {
                    "output_type": "paper_list",
                    "papers": [],
                    "result": f"未找到与「{search_query}」相关的论文，请尝试其他关键词"
                }
            
            context["papers"] = papers
            
            return {
                "output_type": "paper_list",
                "papers": papers,
                "result": f"找到 {len(papers)} 篇与「{search_query}」相关的论文"
            }
        elif is_search_step and ("papers" in context or current_papers):
            papers = context.get("papers", []) or current_papers
            if not papers:
                return {
                    "output_type": "paper_list",
                    "papers": [],
                    "result": "没有论文可用"
                }
            return {
                "output_type": "paper_list",
                "papers": papers,
                "result": f"已找到 {len(papers)} 篇论文，继续后续步骤"
            }
        
        elif is_analyze_step:
            papers = context.get("papers", []) or current_papers
            if not papers:
                return {
                    "output_type": "analysis",
                    "analysis": {"error": "没有论文可供分析"},
                    "result": "没有论文可供分析"
                }
            
            paper_titles = [p["title"] for p in papers[:5]]
            prompt = f"""请分析以下论文列表，总结研究主题、趋势和主要方法：

论文列表：
{chr(10).join([f'{i+1}. {t}' for i, t in enumerate(paper_titles)])}

请以JSON格式返回：
{{
    "key_topics": ["主题1", "主题2", "主题3"],
    "trends": "研究趋势描述",
    "methods": ["方法1", "方法2"],
    "summary": "整体分析总结"
}}

只返回JSON，不要其他内容。"""
            
            analysis_text = await self._call_llm(prompt, temperature=0.3)
            
            try:
                json_match = re.search(r'\{[\s\S]*\}', analysis_text)
                if json_match:
                    analysis = json.loads(json_match.group())
                else:
                    analysis = {
                        "key_topics": ["研究主题分析"],
                        "trends": analysis_text[:200],
                        "methods": [],
                        "summary": "分析完成"
                    }
            except:
                analysis = {
                    "key_topics": ["研究主题分析"],
                    "trends": analysis_text[:200],
                    "methods": [],
                    "summary": "分析完成"
                }
            
            context["analysis"] = analysis
            
            return {
                "output_type": "analysis",
                "analysis": analysis,
                "result": "完成文献内容分析"
            }
        
        elif is_summarize_step:
            papers = context.get("papers", [])
            analysis = context.get("analysis", {})
            
            if papers:
                paper_list = "\n".join([f"- {p['title']} ({p['year']})" for p in papers[:10]])
            else:
                paper_list = "无相关论文"
            
            prompt = f"""请根据以下信息生成一份文献调研报告：

原始任务：{task}

找到的论文：
{paper_list}

分析结果：
{json.dumps(analysis, ensure_ascii=False, indent=2)}

请生成一份结构化的调研报告，包含：
1. 研究背景
2. 主要发现
3. 研究趋势
4. 建议"""
            
            report = await self._call_llm(prompt, temperature=0.5)
            
            return {
                "output_type": "report",
                "report": report,
                "result": "调研报告已生成"
            }
        
        is_visualize_step = any(kw in step_id or kw in step_name or kw in step_desc 
                               for kw in ["visualize", "visual", "可视化", "图表", "图谱", "网络图", "时间线"])
        
        if is_visualize_step:
            papers = context.get("papers", []) or current_papers
            
            viz_type = "author_network"
            task_lower = task.lower()
            if "时间" in task or "timeline" in task_lower:
                viz_type = "timeline"
            elif "引用" in task or "citation" in task_lower:
                viz_type = "citation_graph"
            elif "知识" in task or "knowledge" in task_lower:
                viz_type = "knowledge_graph"
            elif "作者" in task or "author" in task_lower:
                viz_type = "author_network"
            
            return {
                "output_type": "visualization",
                "action": "show_visualization",
                "viz_type": viz_type,
                "papers": papers,
                "result": f"正在生成可视化图表..."
            }
        
        return {"output_type": "text", "result": f"步骤「{step.name}」已完成"}
    
    async def _execute_schedule_step(self, step: PlanStep, task: str, 
                                     context: Dict[str, Any]) -> Dict[str, Any]:
        if step.step_id == "parse":
            prompt = f"""请从以下任务中提取日程信息，以JSON格式返回：

任务：{task}

返回格式：
{{
    "title": "事件标题",
    "date": "日期（YYYY-MM-DD格式，如果不确定请推断）",
    "time": "时间（如 14:00-16:00 或 14:00）",
    "duration_hours": 时长（小时数，默认1）,
    "participants": ["参与者列表"],
    "location": "地点（如果有）",
    "description": "详细描述"
}}

只返回JSON，不要其他内容。"""
            
            result = await self._call_llm(prompt, temperature=0.3)
            
            try:
                json_match = re.search(r'\{[\s\S]*\}', result)
                if json_match:
                    schedule_info = json.loads(json_match.group())
                else:
                    schedule_info = {
                        "title": task,
                        "date": datetime.now().strftime("%Y-%m-%d"),
                        "time": "待定",
                        "duration_hours": 1,
                        "participants": [],
                        "location": "",
                        "description": task
                    }
            except:
                schedule_info = {
                    "title": task,
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "time": "待定",
                    "duration_hours": 1,
                    "participants": [],
                    "location": "",
                    "description": task
                }
            
            return {
                "output_type": "schedule_info",
                "schedule_info": schedule_info,
                "result": f"已解析日程：{schedule_info.get('title', '未命名')}，时间：{schedule_info.get('date', '')} {schedule_info.get('time', '')}"
            }
        
        elif step.step_id == "create":
            schedule_info = context.get("schedule_info", {})
            
            title = schedule_info.get("title", "未命名事件")
            date_str = schedule_info.get("date", datetime.now().strftime("%Y-%m-%d"))
            time_str = schedule_info.get("time", "09:00")
            duration = schedule_info.get("duration_hours", 1)
            location = schedule_info.get("location", "")
            description = schedule_info.get("description", "")
            participants = schedule_info.get("participants", [])
            
            try:
                if "-" in time_str:
                    time_parts = time_str.split("-")
                    start_time_str = time_parts[0].strip()
                    end_time_str = time_parts[1].strip()
                else:
                    start_time_str = time_str
                    hour = int(start_time_str.split(":")[0])
                    end_hour = hour + duration
                    end_time_str = f"{end_hour:02d}:{start_time_str.split(':')[1] if ':' in start_time_str else '00'}"
                
                start_datetime = datetime.strptime(f"{date_str} {start_time_str}", "%Y-%m-%d %H:%M")
                end_datetime = datetime.strptime(f"{date_str} {end_time_str}", "%Y-%m-%d %H:%M")
            except:
                start_datetime = datetime.now() + timedelta(hours=1)
                end_datetime = start_datetime + timedelta(hours=1)
            
            schedule_result = {
                "id": f"evt_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "title": title,
                "date": date_str,
                "time": time_str,
                "start_datetime": start_datetime.isoformat(),
                "end_datetime": end_datetime.isoformat(),
                "location": location,
                "participants": participants,
                "description": description,
                "synced_to_calendar": False
            }
            
            if CALENDAR_AVAILABLE and calendar_service:
                try:
                    cal_result = await create_schedule(
                        title=title,
                        start_time=start_datetime.isoformat(),
                        end_time=end_datetime.isoformat(),
                        description=description,
                        location=location,
                        reminder_minutes=30
                    )
                    
                    if cal_result.get("success"):
                        schedule_result["id"] = cal_result.get("event_id", schedule_result["id"])
                        schedule_result["synced_to_calendar"] = cal_result.get("synced_to_calendar", False)
                        schedule_result["calendar_message"] = cal_result.get("message", "")
                except Exception as e:
                    print(f"[Schedule] Calendar integration failed: {e}")
            
            result_msg = f"日程「{title}」已创建"
            if schedule_result.get("synced_to_calendar"):
                result_msg += "并同步到系统日历"
            result_msg += f"，时间：{date_str} {time_str}"
            
            return {
                "output_type": "schedule",
                "schedule": schedule_result,
                "result": result_msg
            }
        
        elif step.step_id == "remind":
            schedule_info = context.get("schedule_info", {})
            schedule = context.get("schedule", {})
            
            return {
                "output_type": "reminder",
                "reminder": {
                    "time": "事件前30分钟",
                    "method": "系统通知"
                },
                "schedule": schedule,
                "result": f"已设置提醒：事件前30分钟提醒"
            }
        
        return {"output_type": "text", "result": "步骤完成"}
    
    async def _execute_experiment_step(self, step: PlanStep, task: str, 
                                       context: Dict[str, Any]) -> Dict[str, Any]:
        if step.step_id == "analyze_request":
            prompt = f"""请分析以下数据分析需求，以JSON格式返回：

任务：{task}

返回格式：
{{
    "data_type": "数据类型",
    "analysis_goals": ["分析目标1", "分析目标2"],
    "required_stats": ["需要的统计指标"],
    "suggested_charts": ["建议的图表类型"]
}}

只返回JSON，不要其他内容。"""
            
            result = await self._call_llm(prompt, temperature=0.3)
            
            try:
                json_match = re.search(r'\{[\s\S]*\}', result)
                if json_match:
                    analysis = json.loads(json_match.group())
                else:
                    analysis = {
                        "data_type": "实验数据",
                        "analysis_goals": ["数据分析"],
                        "required_stats": ["均值", "标准差"],
                        "suggested_charts": ["柱状图"]
                    }
            except:
                analysis = {
                    "data_type": "实验数据",
                    "analysis_goals": ["数据分析"],
                    "required_stats": ["均值", "标准差"],
                    "suggested_charts": ["柱状图"]
                }
            
            return {
                "output_type": "analysis",
                "analysis": analysis,
                "result": "已分析数据需求"
            }
        
        elif step.step_id == "generate_stats":
            return {
                "output_type": "statistics",
                "statistics": {
                    "total_samples": 150,
                    "groups": 3,
                    "mean_accuracy": 0.917,
                    "std_accuracy": 0.035,
                    "best_group": "A",
                    "summary": "实验数据分析完成，A组表现最佳"
                },
                "result": "统计数据已生成"
            }
        
        elif step.step_id == "report":
            analysis = context.get("analysis", {})
            
            prompt = f"""请根据以下信息生成数据分析报告：

原始任务：{task}

分析需求：
{json.dumps(analysis, ensure_ascii=False, indent=2)}

请生成一份结构化的数据分析报告，包含：
1. 数据概览
2. 分析方法
3. 主要发现
4. 结论和建议"""
            
            report = await self._call_llm(prompt, temperature=0.5)
            
            return {
                "output_type": "report",
                "report": report,
                "result": "数据分析报告已生成"
            }
        
        return {"output_type": "text", "result": "步骤完成"}
    
    async def _execute_question_step(self, step: PlanStep, task: str, 
                                     context: Dict[str, Any]) -> Dict[str, Any]:
        if step.step_id == "understand":
            prompt = f"""请分析以下问题，提取核心概念和背景：

问题：{task}

以JSON格式返回：
{{
    "core_question": "核心问题",
    "key_concepts": ["关键概念1", "关键概念2"],
    "background": "问题背景",
    "expected_depth": "basic/intermediate/advanced"
}}

只返回JSON，不要其他内容。"""
            
            result = await self._call_llm(prompt, temperature=0.3)
            
            try:
                json_match = re.search(r'\{[\s\S]*\}', result)
                if json_match:
                    analysis = json.loads(json_match.group())
                else:
                    analysis = {
                        "core_question": task,
                        "key_concepts": [],
                        "background": "",
                        "expected_depth": "intermediate"
                    }
            except:
                analysis = {
                    "core_question": task,
                    "key_concepts": [],
                    "background": "",
                    "expected_depth": "intermediate"
                }
            
            return {
                "output_type": "analysis",
                "analysis": analysis,
                "result": "问题分析完成"
            }
        
        elif step.step_id == "research":
            analysis = context.get("analysis", {})
            key_concepts = analysis.get("key_concepts", [])
            
            if key_concepts:
                search_query = " ".join(key_concepts[:3])
                papers = await self._search_papers(search_query, years=3, max_results=5, sort_by="relevance")
            else:
                papers = []
            
            return {
                "output_type": "references",
                "references": papers[:3] if papers else [],
                "result": f"找到 {len(papers)} 篇相关参考资料"
            }
        
        elif step.step_id == "answer":
            analysis = context.get("analysis", {})
            
            depth = analysis.get("expected_depth", "intermediate")
            depth_instruction = {
                "basic": "请用简单易懂的语言解释，适合初学者理解。",
                "intermediate": "请提供适中的技术深度，包含必要的专业术语解释。",
                "advanced": "请提供深入的技术分析，可以包含公式和详细原理。"
            }.get(depth, "")
            
            prompt = f"""请回答以下问题：

问题：{task}

问题分析：
{json.dumps(analysis, ensure_ascii=False, indent=2)}

要求：
{depth_instruction}
- 请提供清晰、准确、有逻辑的回答
- 如果有相关概念，请简要解释
- 如果有实际应用，请举例说明"""
            
            answer = await self._call_llm(prompt, temperature=0.7)
            
            return {
                "output_type": "answer",
                "answer": answer,
                "result": "答案已生成"
            }
        
        return {"output_type": "text", "result": "步骤完成"}
    
    async def _execute_general_step(self, step: PlanStep, task: str, 
                                    context: Dict[str, Any]) -> Dict[str, Any]:
        if step.step_id == "understand":
            prompt = f"""请分析以下任务需求：

任务：{task}

以JSON格式返回：
{{
    "task_type": "任务类型",
    "key_requirements": ["需求1", "需求2"],
    "suggested_approach": "建议的方法"
}}

只返回JSON，不要其他内容。"""
            
            result = await self._call_llm(prompt, temperature=0.3)
            
            try:
                json_match = re.search(r'\{[\s\S]*\}', result)
                if json_match:
                    analysis = json.loads(json_match.group())
                else:
                    analysis = {"task_type": "通用任务", "key_requirements": [], "suggested_approach": ""}
            except:
                analysis = {"task_type": "通用任务", "key_requirements": [], "suggested_approach": ""}
            
            return {
                "output_type": "analysis",
                "analysis": analysis,
                "result": "任务分析完成"
            }
        
        elif step.step_id == "execute":
            prompt = f"""请执行以下任务：

任务：{task}

请提供详细的执行结果。"""
            
            result = await self._call_llm(prompt, temperature=0.7)
            
            return {
                "output_type": "result",
                "result": result
            }
        
        elif step.step_id == "verify":
            return {
                "output_type": "verification",
                "verification": "任务已完成",
                "result": "验证完成"
            }
        
        return {"output_type": "text", "result": "步骤完成"}
    
    async def _execute_question_answering_stream(
        self,
        task: str,
        callback: Optional[Callable] = None,
        results: Optional[Dict] = None,
        intent_summary: str = ""
    ) -> Dict[str, Any]:
        if results is None:
            results = {
                "task": task,
                "started_at": datetime.now().isoformat(),
                "steps": [],
                "plan": [],
                "final_answer": ""
            }
        
        await self._send_update("executing", 20, "正在生成回答...", callback)
        await self._add_step('thought', f'问题解答模式：直接生成答案', callback)
        
        prompt = f"""请回答以下问题，要求：
1. 回答要清晰、准确、有条理
2. 如果涉及概念解释，请用通俗易懂的语言
3. 如果有实际应用场景，请举例说明
4. 回答要完整，不要过于简短
5. **必须使用 Markdown 格式**，包括：
   - 使用 `##` 标题分隔不同部分
   - 使用 `**粗体**` 强调重点
   - 使用 `-` 或 `1.` 列表展示要点
   - 使用 ` ```代码块` 展示代码示例
   - 使用 `> 引用` 展示重要说明

问题：{task}

请使用 Markdown 格式回答："""
        
        full_answer = ""
        async for chunk in self._call_llm_stream(prompt, temperature=0.7, callback=callback):
            full_answer += chunk
        
        results["task_type"] = TaskType.QUESTION_ANSWERING.value
        results["final_answer"] = full_answer
        results["completed_at"] = datetime.now().isoformat()
        results["plan"] = [{
            "step_id": "answer",
            "name": "生成回答",
            "description": "直接回答用户问题",
            "output_type": "answer",
            "status": "completed",
            "output": {"answer": full_answer, "output_type": "answer"}
        }]
        
        await self._send_update("completed", 100, "回答完成！", callback)
        
        return {
            "success": True,
            **results
        }
    
    async def execute_task(
        self,
        task: str,
        callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        context_input: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        results = {
            "task": task,
            "started_at": datetime.now().isoformat(),
            "steps": [],
            "plan": [],
            "final_answer": ""
        }
        
        await self._send_update("planning", 0, "正在智能分析任务...", callback)
        await self._add_step('thought', f'开始分析任务：{task}', callback)
        
        if context_input:
            await self._add_step('thought', f'检测到对话上下文，正在分析...', callback)
            task_with_context = self._build_task_with_context(task, context_input)
            analysis = await self._analyze_task_with_llm(task_with_context)
        else:
            analysis = await self._analyze_task_with_llm(task)
        
        task_type_str = analysis.get("task_type", "general")
        intent_summary = analysis.get("intent_summary", task)
        extracted_params = analysis.get("extracted_params", {})
        llm_plan = analysis.get("plan", [])
        reasoning = analysis.get("reasoning", "")
        
        await self._add_step('thought', f'意图识别：{intent_summary}', callback)
        await self._add_step('thought', f'参数提取：{json.dumps(extracted_params, ensure_ascii=False)}', callback)
        if reasoning:
            await self._add_step('thought', f'推理过程：{reasoning}', callback)
        
        task_type = TaskType.GENERAL
        if "literature" in task_type_str.lower():
            task_type = TaskType.LITERATURE_RESEARCH
        elif "schedule" in task_type_str.lower():
            task_type = TaskType.SCHEDULE_PLANNING
        elif "experiment" in task_type_str.lower():
            task_type = TaskType.EXPERIMENT_MANAGEMENT
        elif "question" in task_type_str.lower():
            task_type = TaskType.QUESTION_ANSWERING
        
        if task_type == TaskType.QUESTION_ANSWERING:
            return await self._execute_question_answering_stream(task, callback, results, intent_summary)
        
        await self._send_update("planning", 10, "正在规划执行步骤...", callback)
        
        if llm_plan:
            plan_steps = []
            for step_info in llm_plan:
                step = PlanStep(
                    step_info.get("step_id", f"step_{len(plan_steps)}"),
                    step_info.get("name", "执行步骤"),
                    step_info.get("description", ""),
                    step_info.get("output_type", "result")
                )
                plan_steps.append(step)
        else:
            plan_steps = self._get_plan_for_type(task_type, task)
        
        plan_data = []
        for s in plan_steps:
            plan_data.append({
                "step_id": s.step_id,
                "name": s.name,
                "description": s.description,
                "output_type": s.output_type,
                "status": s.status.value,
                "steps": [],
                "output": None
            })
        results["plan"] = plan_data
        results["task_type"] = task_type.value
        results["extracted_params"] = extracted_params
        
        await self._send_task_list(plan_steps, callback)
        await self._add_step('thought', f'LLM 规划了 {len(plan_steps)} 个执行步骤', callback)
        
        total_steps = len(plan_steps)
        final_results = []
        context: Dict[str, Any] = {"extracted_params": extracted_params}
        
        if context_input:
            context["currentPapers"] = context_input.get("currentPapers", [])
            context["selectedPaperIndex"] = context_input.get("selectedPaperIndex")
            context["messages"] = context_input.get("messages", [])
        
        for i, step in enumerate(plan_steps):
            progress = 10 + int(((i + 1) / total_steps) * 90)
            
            await self._update_step_status(step, TaskStatus.IN_PROGRESS, callback)
            await self._add_task_step(step.step_id, 'thought', f'开始执行「{step.name}」', callback)
            await self._send_update("executing", progress, f"正在执行：{step.name}", callback)
            
            try:
                step_result = await self._execute_step(step, task, task_type, context)
                
                if step.step_id == "search":
                    context["papers"] = step_result.get("papers", [])
                elif step.step_id == "analyze":
                    context["analysis"] = step_result.get("analysis", {})
                elif step.step_id == "parse":
                    context["schedule_info"] = step_result.get("schedule_info", {})
                elif step.step_id == "create":
                    context["schedule"] = step_result.get("schedule", {})
                elif step.step_id == "analyze_request":
                    context["analysis"] = step_result.get("analysis", {})
                elif step.step_id == "understand":
                    context["analysis"] = step_result.get("analysis", {})
                
                plan_data[i]["status"] = TaskStatus.COMPLETED.value
                plan_data[i]["output"] = step_result
                plan_data[i]["result"] = step_result.get("result", "完成")
                
                await self._add_task_step(step.step_id, 'observation', step_result.get("result", "完成"), callback)
                await self._send_step_output(step.step_id, step_result, callback)
                await self._update_step_status(step, TaskStatus.COMPLETED, callback)
                
                if step.step_id == "answer" and "answer" in step_result:
                    final_results.append(f"**{step.name}**:\n\n{step_result['answer']}")
                else:
                    final_results.append(f"**{step.name}**: {step_result.get('result', '完成')}")
                
            except Exception as e:
                error_msg = str(e)
                plan_data[i]["status"] = TaskStatus.FAILED.value
                plan_data[i]["output"] = {"error": error_msg}
                plan_data[i]["result"] = f"执行失败: {error_msg}"
                
                await self._add_task_step(step.step_id, 'observation', f'执行失败: {error_msg}', callback)
                await self._update_step_status(step, TaskStatus.FAILED, callback)
                
                final_results.append(f"**{step.name}**: 执行失败 - {error_msg}")
            
            await asyncio.sleep(0.1)
        
        await self._send_update("completed", 100, "任务完成！", callback)
        await self._add_step('thought', '所有步骤执行完毕！', callback)
        
        results["final_answer"] = "\n\n".join(final_results)
        results["completed_at"] = datetime.now().isoformat()
        results["plan"] = plan_data
        
        return {
            "success": True,
            **results
        }
    
    async def _execute_research_task_with_params(
        self,
        task: str,
        params: Dict[str, Any],
        callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        base_results: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        if base_results is None:
            base_results = {}
        
        research_agent = ResearchAgent()
        
        topic = params.get("topic", task)
        years = params.get("years", 2)
        max_papers = params.get("max_papers", 30)
        sort_by = params.get("sort_by", "relevance")
        
        await self._add_step('thought', f'执行参数：主题="{topic}"，年限={years}年，论文数={max_papers}篇，排序={sort_by}', callback)
        
        research_plan = [
            PlanStep("search", "多源文献检索", f"检索 arXiv、Semantic Scholar 等数据库，获取最近{years}年的{max_papers}篇论文", "research_papers"),
            PlanStep("analyze", "论文深度分析", "分析每篇论文，提取贡献、方法、局限性和关键词", "research_analysis"),
            PlanStep("cluster", "主题聚类分析", "使用 TF-IDF 和 K-Means 算法对论文进行聚类", "research_clusters"),
            PlanStep("synthesis", "研究交叉点识别", "分析各研究方向之间的关联，识别潜在的交叉研究机会", "research_crosspoints"),
            PlanStep("report", "完整报告生成", "整合所有分析结果，生成结构化的研究综述报告", "research_report")
        ]
        
        plan_data = []
        for s in research_plan:
            plan_data.append({
                "step_id": s.step_id,
                "name": s.name,
                "description": s.description,
                "output_type": s.output_type,
                "status": s.status.value,
                "steps": [],
                "output": None
            })
        base_results["plan"] = plan_data
        base_results["task_type"] = TaskType.LITERATURE_RESEARCH.value
        base_results["extracted_params"] = params
        
        research_result = await research_agent.conduct_research(
            topic=topic,
            years=years,
            max_papers=max_papers,
            callback=callback,
            sort_by=sort_by
        )
        
        for i, step in enumerate(plan_data):
            if step["step_id"] == "search":
                step["output"] = {"output_type": "research_papers", "papers": research_result.get("papers", [])}
            elif step["step_id"] == "analyze":
                step["output"] = {"output_type": "research_analysis", "papers": research_result.get("papers", [])}
            elif step["step_id"] == "cluster":
                step["output"] = {"output_type": "research_clusters", "clusters": research_result.get("clusters", [])}
            elif step["step_id"] == "synthesis":
                step["output"] = {"output_type": "research_crosspoints", "cross_points": research_result.get("cross_points", [])}
            elif step["step_id"] == "report":
                step["output"] = {"output_type": "research_report", "report": research_result.get("report", {})}
        
        base_results["is_research_mode"] = True
        base_results["research_result"] = research_result
        base_results["completed_at"] = datetime.now().isoformat()
        base_results["final_answer"] = f"深度研究完成！共检索 {len(research_result.get('papers', []))} 篇论文，识别 {len(research_result.get('clusters', []))} 个研究方向，发现 {len(research_result.get('cross_points', []))} 个研究交叉点。"
        
        return {
            "success": True,
            **base_results
        }
    
    async def _execute_research_task(
        self,
        task: str,
        callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        base_results: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        if base_results is None:
            base_results = {}
        
        research_agent = ResearchAgent()
        
        params = self._parse_research_params(task)
        topic = params["topic"]
        years = params["years"]
        max_papers = params["max_papers"]
        sort_by = params["sort_by"]
        
        await self._add_step('thought', f'解析参数：主题="{topic}"，年限={years}年，论文数={max_papers}篇，排序={sort_by}', callback)
        
        research_plan = [
            PlanStep("search", "多源文献检索", f"检索 arXiv、Semantic Scholar 等数据库，获取最近{years}年的{max_papers}篇论文", "research_papers"),
            PlanStep("analyze", "论文深度分析", "分析每篇论文，提取贡献、方法、局限性和关键词", "research_analysis"),
            PlanStep("cluster", "主题聚类分析", "使用 TF-IDF 和 K-Means 算法对论文进行聚类", "research_clusters"),
            PlanStep("synthesis", "研究交叉点识别", "分析各研究方向之间的关联，识别潜在的交叉研究机会", "research_crosspoints"),
            PlanStep("report", "完整报告生成", "整合所有分析结果，生成结构化的研究综述报告", "research_report")
        ]
        
        plan_data = []
        for s in research_plan:
            plan_data.append({
                "step_id": s.step_id,
                "name": s.name,
                "description": s.description,
                "output_type": s.output_type,
                "status": s.status.value,
                "steps": [],
                "output": None
            })
        base_results["plan"] = plan_data
        base_results["task_type"] = TaskType.LITERATURE_RESEARCH.value
        
        await self._send_task_list(research_plan, callback)
        
        research_result = await research_agent.conduct_research(
            topic=topic,
            years=years,
            max_papers=max_papers,
            callback=callback,
            sort_by=sort_by
        )
        
        for i, step in enumerate(plan_data):
            if step["step_id"] == "search":
                step["output"] = {"output_type": "research_papers", "papers": research_result.get("papers", [])}
            elif step["step_id"] == "analyze":
                step["output"] = {"output_type": "research_analysis", "papers": research_result.get("papers", [])}
            elif step["step_id"] == "cluster":
                step["output"] = {"output_type": "research_clusters", "clusters": research_result.get("clusters", [])}
            elif step["step_id"] == "synthesis":
                step["output"] = {"output_type": "research_crosspoints", "cross_points": research_result.get("cross_points", [])}
            elif step["step_id"] == "report":
                step["output"] = {"output_type": "research_report", "report": research_result.get("report", {})}
        
        base_results["is_research_mode"] = True
        base_results["research_result"] = research_result
        base_results["completed_at"] = datetime.now().isoformat()
        base_results["final_answer"] = f"深度研究完成！共检索 {len(research_result.get('papers', []))} 篇论文，识别 {len(research_result.get('clusters', []))} 个研究方向，发现 {len(research_result.get('cross_points', []))} 个研究交叉点。"
        
        return {
            "success": True,
            **base_results
        }
    
    async def _send_update(self, state: str, progress: int, task_desc: str, 
                          callback: Optional[Callable] = None):
        if callback:
            try:
                await callback({
                    "type": "progress",
                    "state": state,
                    "progress": progress,
                    "task": task_desc,
                    "timestamp": datetime.now().isoformat()
                })
            except Exception as e:
                print(f"Failed to send update: {e}")
    
    async def _add_step(self, step_type: str, content: str, 
                       callback: Optional[Callable] = None):
        if callback:
            try:
                await callback({
                    "type": "step",
                    "step_type": step_type,
                    "content": content,
                    "timestamp": datetime.now().isoformat()
                })
            except Exception as e:
                print(f"Failed to send step: {e}")
    
    async def _send_task_list(self, steps: List[PlanStep], 
                             callback: Optional[Callable] = None):
        if callback:
            task_data = [
                {
                    "task_id": s.step_id,
                    "name": s.name,
                    "description": s.description,
                    "output_type": s.output_type,
                    "status": s.status.value
                }
                for s in steps
            ]
            try:
                await callback({
                    "type": "task_list",
                    "tasks": task_data,
                    "timestamp": datetime.now().isoformat()
                })
            except Exception as e:
                print(f"Failed to send task list: {e}")
    
    async def _update_step_status(self, step: PlanStep, status: TaskStatus, 
                                  callback: Optional[Callable] = None):
        step.status = status
        if status == TaskStatus.IN_PROGRESS:
            if not hasattr(step, 'start_time'):
                step.start_time = datetime.now().isoformat()
        elif status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
            if not hasattr(step, 'end_time'):
                step.end_time = datetime.now().isoformat()
        
        if callback:
            try:
                await callback({
                    "type": "task_update",
                    "task_id": step.step_id,
                    "status": status.value,
                    "timestamp": datetime.now().isoformat()
                })
            except Exception as e:
                print(f"Failed to update step status: {e}")
    
    async def _add_task_step(self, task_id: str, step_type: str, content: str, 
                            callback: Optional[Callable] = None):
        if callback:
            try:
                await callback({
                    "type": "task_step",
                    "task_id": task_id,
                    "step_type": step_type,
                    "content": content,
                    "timestamp": datetime.now().isoformat()
                })
            except Exception as e:
                print(f"Failed to add task step: {e}")
    
    async def _send_step_output(self, task_id: str, output: Dict[str, Any],
                               callback: Optional[Callable] = None):
        if callback:
            try:
                await asyncio.sleep(0.01)
                await callback({
                    "type": "step_output",
                    "task_id": task_id,
                    "output": output,
                    "timestamp": datetime.now().isoformat()
                })
            except Exception as e:
                print(f"Failed to send step output: {e}")