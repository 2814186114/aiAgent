import os
import sys

_lib_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "python_libs")
if os.path.exists(_lib_path):
    sys.path.insert(0, _lib_path)

import json
import re
import asyncio
from typing import Callable, Optional, Dict, Any, List

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

from .tools import get_tool_schemas, execute_tool, is_async_tool, execute_async_tool
from .memory import get_memory_manager

class ReActAgent:
    def __init__(self):
        self.llm_provider = os.getenv("LLM_PROVIDER", "deepseek")
        self.client = self._init_client()
        self.model = self._get_model()
        self.max_iterations = 10
        self.max_retries = 2
        
    def _init_client(self):
        if not OPENAI_AVAILABLE:
            print("Warning: openai package not available")
            return None
            
        if self.llm_provider == "deepseek":
            api_key = os.getenv("DEEPSEEK_API_KEY")
            base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
        else:
            api_key = os.getenv("OPENAI_API_KEY")
            base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        
        print(f"LLM Provider: {self.llm_provider}")
        print(f"API Key configured: {bool(api_key and api_key != 'your_api_key_here')}")
        
        if not api_key or api_key == "your_api_key_here":
            print("Warning: No valid API key found")
            return None
            
        return OpenAI(api_key=api_key, base_url=base_url)
    
    def _get_model(self) -> str:
        if self.llm_provider == "deepseek":
            return "deepseek-chat"
        return "gpt-4o-mini"
    
    def _detect_intent(self, task: str) -> Dict[str, Any]:
        """预判用户意图，返回推荐的工具和参数"""
        task_lower = task.lower()
        
        experiment_keywords = ['跑了', '测试了', '实验结果', '准确率', 'loss', '精度', 'f1', 
                             'recall', 'precision', '训练了', '模型在', '数据集上', '记录实验',
                             '实验记录', '实验：', '记录：']
        reminder_keywords = ['提醒我', '别忘了', '记得', '明天', '下周', '今天下午', 
                            '今天上午', '组会', '开会', '截止', '提交', '添加日程', 
                            '日程：', '提醒：', '安排']
        query_keywords = ['查看', '查询', '最近', '历史', '所有实验', '所有日程', 
                         '找一下', '有没有', '查询：', '查看：']
        paper_keywords = ['搜索论文', '找论文', '查论文', '文献', '论文：', 
                         'semantic scholar', 'arxiv']
        review_keywords = ['文献综述', '研究进展', '领域分析', '综述', '研究现状', 
                          '领域概述', '研究概况']
        trend_keywords = ['研究趋势', '发展趋势', '发展趋势', '演变', '发展历程']
        gap_keywords = ['研究空白', '研究方向', '未来方向', '研究机会', '研究问题', 
                        '待研究', '未解决']
        
        for kw in experiment_keywords:
            if kw in task_lower:
                return {
                    "intent": "record_experiment",
                    "recommended_tool": "add_experiment",
                    "confidence": 0.9,
                    "hint": f"检测到实验记录意图（关键词：{kw}）"
                }
        
        for kw in reminder_keywords:
            if kw in task_lower:
                return {
                    "intent": "add_reminder",
                    "recommended_tool": "add_reminder",
                    "confidence": 0.9,
                    "hint": f"检测到日程提醒意图（关键词：{kw}）"
                }
        
        for kw in query_keywords:
            if kw in task_lower:
                return {
                    "intent": "query_history",
                    "recommended_tool": "query_experiments" if '实验' in task_lower else "list_reminders",
                    "confidence": 0.8,
                    "hint": f"检测到查询意图（关键词：{kw}）"
                }
        
        for kw in review_keywords:
            if kw in task_lower:
                return {
                    "intent": "literature_review",
                    "recommended_tool": "generate_literature_review",
                    "confidence": 0.9,
                    "hint": f"检测到文献综述意图（关键词：{kw}）"
                }
        
        for kw in trend_keywords:
            if kw in task_lower:
                return {
                    "intent": "research_trends",
                    "recommended_tool": "analyze_research_trends",
                    "confidence": 0.9,
                    "hint": f"检测到研究趋势分析意图（关键词：{kw}）"
                }
        
        for kw in gap_keywords:
            if kw in task_lower:
                return {
                    "intent": "find_gaps",
                    "recommended_tool": "find_research_gaps",
                    "confidence": 0.9,
                    "hint": f"检测到研究空白分析意图（关键词：{kw}）"
                }
        
        for kw in paper_keywords:
            if kw in task_lower:
                return {
                    "intent": "search_papers",
                    "recommended_tool": "search_semantic_scholar",
                    "confidence": 0.8,
                    "hint": f"检测到论文搜索意图（关键词：{kw}）"
                }
        
        return {
            "intent": "general_chat",
            "recommended_tool": None,
            "confidence": 0.5,
            "hint": "未检测到明确意图，将进行通用处理"
        }
    
    def _get_system_prompt(self, context: str = "", intent_info: Dict = None) -> str:
        intent_hint = ""
        if intent_info and intent_info.get("confidence", 0) >= 0.8:
            intent_hint = f"""
【系统检测到的意图】
- 意图类型: {intent_info.get('intent', '未知')}
- 推荐工具: {intent_info.get('recommended_tool', '无')}
- 检测说明: {intent_info.get('hint', '')}

【重要】请优先使用推荐工具处理此任务！不要先搜索或分析，直接调用工具。
"""
        
        base_prompt = f"""你是一个学术助手智能体，使用ReAct框架来帮助研究生完成学术任务。
{intent_hint}
【核心规则 - 必须遵守】
1. 如果任务包含"请帮我记录实验"或类似表述 → 直接调用 add_experiment，参数 note 为实验描述
2. 如果任务包含"请帮我添加日程"或类似表述 → 直接调用 add_reminder，参数 note 为日程描述  
3. 如果任务包含"请帮我查询"或类似表述 → 直接调用 query_experiments 或 list_reminders
4. 如果任务要求"文献综述"、"研究进展"、"领域分析" → 调用 generate_literature_review
5. 如果任务要求"研究趋势"、"发展趋势" → 调用 analyze_research_trends
6. 如果任务要求"研究空白"、"研究方向"、"未来方向" → 调用 find_research_gaps
7. 不要在记录/查询类任务前进行搜索！直接调用对应工具！

【工具列表】
记录类工具（直接调用，无需搜索）：
- add_experiment(note="实验描述") - 记录实验结果
- add_reminder(note="日程描述") - 添加日程提醒

查询类工具（直接调用，无需搜索）：
- query_experiments(query="查询条件", limit=10) - 查询实验记录
- list_reminders(time_range="all") - 查看日程列表

文献分析工具：
- search_semantic_scholar(query="关键词", limit=5) - 搜索学术论文
- generate_literature_review(query="主题", paper_limit=15) - 生成文献综述
- analyze_research_trends(query="主题", years=5) - 分析研究趋势
- find_research_gaps(query="主题") - 识别研究空白
- get_paper_citations(paper_id="论文ID") - 获取引用列表
- get_paper_references(paper_id="论文ID") - 获取参考文献

论文阅读工具：
- read_pdf(file_path="路径") - 读取PDF并解析结构
- analyze_paper(file_path="路径") - 深度分析论文

【思考格式】
Thought: 简短分析（一句话）
Action: 工具名称
Action Input: {{"参数名": "参数值"}}

最终答案格式：
Answer: 回答内容

【示例】
用户: 请帮我记录实验：BERT在SST-2上准确率92.3%
Thought: 用户要记录实验结果，直接调用add_experiment
Action: add_experiment
Action Input: {{"note": "BERT在SST-2上准确率92.3%"}}

用户: 请帮我添加日程：明天下午3点组会
Thought: 用户要添加日程，直接调用add_reminder
Action: add_reminder
Action Input: {{"note": "明天下午3点组会"}}

用户: 请帮我查询最近的实验记录
Thought: 用户要查询实验历史，直接调用query_experiments
Action: query_experiments
Action Input: {{"query": "最近的实验", "limit": 10}}

用户: 帮我生成一篇关于Transformer的文献综述
Thought: 用户要生成文献综述，调用generate_literature_review
Action: generate_literature_review
Action Input: {{"query": "Transformer", "paper_limit": 15}}

用户: 分析一下大语言模型的研究趋势
Thought: 用户要分析研究趋势，调用analyze_research_trends
Action: analyze_research_trends
Action Input: {{"query": "large language model", "years": 5}}
"""
        
        if context:
            return f"{base_prompt}\n\n【相关历史任务上下文】\n{context}\n\n请参考以上历史任务来更好地完成当前任务。"
        
        return base_prompt

    async def run(
        self, 
        task: str, 
        callback: Optional[Callable[[Dict[str, Any]], None]] = None
    ) -> Dict[str, Any]:
        import uuid
        task_id = str(uuid.uuid4())
        
        memory_manager = get_memory_manager()
        context = ""
        
        if memory_manager.is_available():
            recall_result = memory_manager.recall_task_history(task, top_k=3)
            if recall_result.get("success") and recall_result.get("results"):
                context_parts = []
                for i, result in enumerate(recall_result["results"], 1):
                    context_parts.append(f"--- 历史任务 {i} ---\n{result['document']}")
                context = "\n\n".join(context_parts)
        
        intent_info = self._detect_intent(task)
        
        if not self.client:
            result = await self._simulate_react(task, callback, intent_info)
        else:
            messages = [
                {"role": "system", "content": self._get_system_prompt(context, intent_info)},
                {"role": "user", "content": task}
            ]
            
            steps = []
            iteration = 0
            final_answer = None
            last_error = None
            
            while iteration < self.max_iterations:
                iteration += 1
                
                try:
                    response = self.client.chat.completions.create(
                        model=self.model,
                        messages=messages,
                        tools=get_tool_schemas(),
                        tool_choice="auto"
                    )
                    
                    assistant_message = response.choices[0].message
                    
                    if assistant_message.content:
                        thought_match = re.search(r'Thought:\s*(.+?)(?=Action:|Answer:|$)', assistant_message.content, re.DOTALL)
                        thought = thought_match.group(1).strip() if thought_match else assistant_message.content
                        
                        step = {
                            "type": "thought",
                            "content": thought,
                            "iteration": iteration
                        }
                        steps.append(step)
                        if callback:
                            await callback(step)
                    
                    if assistant_message.tool_calls:
                        for tool_call in assistant_message.tool_calls:
                            tool_name = tool_call.function.name
                            try:
                                tool_args = json.loads(tool_call.function.arguments)
                            except json.JSONDecodeError:
                                tool_args = {}
                            
                            action_step = {
                                "type": "action",
                                "tool": tool_name,
                                "arguments": tool_args,
                                "iteration": iteration
                            }
                            steps.append(action_step)
                            if callback:
                                await callback(action_step)
                            
                            retry_count = 0
                            observation_result = None
                            
                            while retry_count <= self.max_retries:
                                try:
                                    if is_async_tool(tool_name):
                                        observation_result = await execute_async_tool(tool_name, tool_args)
                                    else:
                                        obs_str = execute_tool(tool_name, tool_args)
                                        observation_result = {
                                            "success": True,
                                            "message": obs_str
                                        }
                                    break
                                except Exception as e:
                                    retry_count += 1
                                    last_error = str(e)
                                    if retry_count <= self.max_retries:
                                        await asyncio.sleep(0.5)
                            
                            if observation_result is None:
                                observation_result = {
                                    "success": False,
                                    "error": f"工具执行失败（重试{self.max_retries}次后）: {last_error}"
                                }
                            
                            observation_content = observation_result.get("message", str(observation_result))
                            
                            if not observation_result.get("success"):
                                observation_content = f"❌ 执行失败: {observation_result.get('error', '未知错误')}"
                            
                            observation_step = {
                                "type": "observation",
                                "content": observation_content,
                                "tool_result": observation_result,
                                "iteration": iteration
                            }
                            steps.append(observation_step)
                            if callback:
                                await callback(observation_step)
                            
                            messages.append(assistant_message)
                            messages.append({
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "content": observation_content
                            })
                    
                    elif assistant_message.content and "Answer:" in assistant_message.content:
                        answer_match = re.search(r'Answer:\s*(.+)', assistant_message.content, re.DOTALL)
                        final_answer = answer_match.group(1).strip() if answer_match else assistant_message.content
                        break
                    
                    else:
                        if assistant_message.content:
                            final_answer = assistant_message.content
                        break
                        
                except Exception as e:
                    error_step = {
                        "type": "error",
                        "content": f"LLM调用错误: {str(e)}",
                        "iteration": iteration
                    }
                    steps.append(error_step)
                    if callback:
                        await callback(error_step)
                    break
            
            if not final_answer:
                if intent_info.get("recommended_tool"):
                    final_answer = f"抱歉，处理您的请求时遇到了问题。您可以尝试直接使用「{intent_info.get('recommended_tool')}」功能。"
                else:
                    final_answer = "抱歉，我无法完成这个任务。请尝试重新描述您的需求。"
            
            result = {
                "task": task,
                "steps": steps,
                "answer": final_answer,
                "iterations": iteration,
                "detected_intent": intent_info
            }
        
        if memory_manager.is_available():
            steps_summary = ""
            for step in result.get("steps", []):
                step_type = step.get("type", "")
                step_content = step.get("content", "")
                if step_type == "thought":
                    steps_summary += f"思考: {step_content}\n"
                elif step_type == "action":
                    steps_summary += f"行动: {step.get('tool')}\n"
                elif step_type == "observation":
                    steps_summary += f"观察: {step_content[:100]}...\n"
            
            memory_manager.store_task_history(
                task_id=task_id,
                task_description=task,
                steps_summary=steps_summary,
                result=result.get("answer", ""),
                success=True
            )
        
        return result
    
    async def _simulate_react(
        self, 
        task: str, 
        callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        intent_info: Dict = None
    ) -> Dict[str, Any]:
        steps = []
        intent = intent_info or {"intent": "unknown", "recommended_tool": None}
        
        steps.append({
            "type": "thought",
            "content": f"收到任务：{task}",
            "iteration": 1
        })
        if callback:
            await callback(steps[-1])
        
        if intent.get("recommended_tool") == "add_experiment":
            steps.append({
                "type": "thought",
                "content": f"检测到实验记录意图，将调用 add_experiment",
                "iteration": 2
            })
            if callback:
                await callback(steps[-1])
            
            steps.append({
                "type": "action",
                "tool": "add_experiment",
                "arguments": {"note": task.replace("请帮我记录实验：", "").replace("请帮我记录实验:", "")},
                "iteration": 3
            })
            if callback:
                await callback(steps[-1])
            
            steps.append({
                "type": "observation",
                "content": "✅ 实验记录已保存（模拟）",
                "tool_result": {"success": True, "message": "实验记录已保存"},
                "iteration": 4
            })
            if callback:
                await callback(steps[-1])
            
            final_answer = "✅ 实验记录已成功保存！您的实验数据已被记录，可以随时查询。"
            
        elif intent.get("recommended_tool") == "add_reminder":
            steps.append({
                "type": "thought",
                "content": f"检测到日程提醒意图，将调用 add_reminder",
                "iteration": 2
            })
            if callback:
                await callback(steps[-1])
            
            steps.append({
                "type": "action",
                "tool": "add_reminder",
                "arguments": {"note": task.replace("请帮我添加日程：", "").replace("请帮我添加日程:", "")},
                "iteration": 3
            })
            if callback:
                await callback(steps[-1])
            
            steps.append({
                "type": "observation",
                "content": "✅ 日程提醒已添加（模拟）",
                "tool_result": {"success": True, "message": "日程提醒已添加"},
                "iteration": 4
            })
            if callback:
                await callback(steps[-1])
            
            final_answer = "✅ 日程提醒已成功添加！到时间我会提醒您。"
            
        elif intent.get("recommended_tool") in ["query_experiments", "list_reminders"]:
            tool_name = intent.get("recommended_tool")
            steps.append({
                "type": "thought",
                "content": f"检测到查询意图，将调用 {tool_name}",
                "iteration": 2
            })
            if callback:
                await callback(steps[-1])
            
            steps.append({
                "type": "action",
                "tool": tool_name,
                "arguments": {"query": task} if tool_name == "query_experiments" else {"time_range": "all"},
                "iteration": 3
            })
            if callback:
                await callback(steps[-1])
            
            steps.append({
                "type": "observation",
                "content": "📋 查询结果（模拟）：找到相关记录",
                "tool_result": {"success": True, "message": "查询完成"},
                "iteration": 4
            })
            if callback:
                await callback(steps[-1])
            
            final_answer = "📋 查询完成！找到了相关记录（模拟模式）。"
            
        else:
            simulated_steps = [
                {"type": "thought", "content": "这是一个学术相关的任务，我应该使用可用的工具来帮助完成。"},
                {"type": "action", "tool": "search_web", "arguments": {"query": task[:50]}},
                {"type": "observation", "content": f"模拟搜索结果：找到3篇与'{task[:30]}'相关的论文"},
                {"type": "thought", "content": "搜索结果已获取，现在我可以基于这些信息给出回答。"},
            ]
            
            for i, step in enumerate(simulated_steps):
                step["iteration"] = len(steps) + 1
                steps.append(step)
                if callback:
                    await callback(step)
                await asyncio.sleep(0.3)
            
            final_answer = f"基于模拟分析，对于您的任务「{task}」，我建议：\n\n1. 首先进行文献调研，了解相关领域的研究现状\n2. 整理关键概念和方法论\n3. 根据需要制定实验计划或写作大纲\n\n如需更详细的帮助，请配置API密钥以启用完整的AI功能。"
        
        answer_step = {
            "type": "answer",
            "content": final_answer,
            "iteration": len(steps) + 1
        }
        steps.append(answer_step)
        if callback:
            await callback(answer_step)
        
        return {
            "task": task,
            "steps": steps,
            "answer": final_answer,
            "iterations": len(steps),
            "detected_intent": intent_info
        }
