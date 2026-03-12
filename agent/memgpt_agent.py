"""
MemGPT 风格的 Agent
让 LLM 自主决定何时读写记忆

核心特点：
1. LLM 通过 tool_calls 主动调用记忆操作
2. 记忆工具作为"系统调用"注册到 LLM
3. LLM 自己决定何时存储、检索、更新记忆
"""

import os
import sys
import json
import asyncio
import uuid
from datetime import datetime
from typing import Callable, Optional, Dict, Any, List

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

from .memory_tools import MemoryTools
from .long_term_memory import get_long_term_memory
from .tools import get_tool_schemas, execute_tool, is_async_tool, execute_async_tool


class MemGPTAgent:
    """
    MemGPT 风格的 Agent
    
    与传统 Agent 的区别：
    - 传统：外部代码决定何时检索记忆（关键词触发）
    - MemGPT：LLM 自己决定何时读写记忆（系统调用）
    
    架构：
    ┌─────────────────────────────────────────────────────────────┐
    │                         LLM                                  │
    │  ┌─────────────────────────────────────────────────────┐    │
    │  │  思考：用户告诉我他的名字，这很重要                    │    │
    │  │  决定：我需要记住这个信息                             │    │
    │  │  行动：调用 core_memory_append("human", "姓名: 小明")  │    │
    │  └─────────────────────────────────────────────────────┘    │
    └─────────────────────────────────────────────────────────────┘
                              │
                              ▼ tool_call
    ┌─────────────────────────────────────────────────────────────┐
    │                    MemoryTools                               │
    │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           │
    │  │ CoreMemory  │ │RecallMemory │ │ArchivalMem  │           │
    │  │ 核心记忆    │ │ 回忆记忆    │ │ 档案记忆    │           │
    │  └─────────────┘ └─────────────┘ └─────────────┘           │
    └─────────────────────────────────────────────────────────────┘
    """
    
    MEMORY_TOOL_NAMES = {
        "core_memory_append",
        "core_memory_replace", 
        "recall_memory_search",
        "archival_memory_insert",
        "archival_memory_search",
        "working_memory_add"
    }
    
    def __init__(self, user_id: str = "anonymous"):
        self.user_id = user_id
        self.llm_provider = os.getenv("LLM_PROVIDER", "deepseek")
        self.client = self._init_client()
        self.model = self._get_model()
        self.max_iterations = 15
        
        self.long_term_memory = get_long_term_memory()
        self.memory_tools = MemoryTools(
            long_term_memory=self.long_term_memory,
            user_id=user_id
        )
    
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
        
        if not api_key or api_key == "your_api_key_here":
            print("Warning: No valid API key found")
            return None
            
        return OpenAI(api_key=api_key, base_url=base_url)
    
    def _get_model(self) -> str:
        if self.llm_provider == "deepseek":
            return "deepseek-chat"
        return "gpt-4o-mini"
    
    def _get_all_tool_schemas(self) -> List[Dict[str, Any]]:
        """
        获取所有工具定义，包括业务工具和记忆工具
        """
        business_tools = get_tool_schemas()
        memory_tools = MemoryTools.get_tool_definitions()
        
        return business_tools + memory_tools
    
    def _get_system_prompt(self) -> str:
        """
        系统提示，包含记忆系统调用的说明
        """
        memory_context = self.memory_tools.build_context_prompt()
        
        return f"""你是一个具有自主记忆管理能力的学术助手智能体。

{memory_context}

【记忆系统调用说明】
你可以通过工具调用来管理自己的记忆：

1. **core_memory_append(section, content)** - 向核心记忆追加内容
   - section: "persona"(关于你自己) 或 "human"(关于用户)
   - 当用户告诉你重要信息时，主动调用此函数记住
   - 示例：用户说"我叫小明"，你应该调用 core_memory_append("human", "用户姓名: 小明")

2. **core_memory_replace(section, old_content, new_content)** - 更新核心记忆
   - 当需要修正或更新已有信息时使用

3. **recall_memory_search(query, n_results)** - 搜索对话历史
   - 当你需要回忆之前的对话内容时调用
   - 示例：用户问"我们之前聊了什么"，调用 recall_memory_search("之前的对话")

4. **archival_memory_insert(content)** - 存档重要信息
   - 用于长期保存重要知识、用户偏好、学到的经验等
   - 示例：用户说"记住我偏好Python"，调用 archival_memory_insert("用户偏好: Python")

5. **archival_memory_search(query, n_results)** - 搜索档案记忆
   - 检索长期保存的信息

6. **working_memory_add(key, content, importance)** - 添加工作记忆
   - 存储当前任务相关的临时信息

【记忆管理原则】
1. 主动记忆：当用户提供个人信息、偏好、重要事实时，主动调用记忆工具
2. 智能检索：当用户问及历史信息时，先检索记忆再回答
3. 及时更新：当信息变化时，更新已有记忆
4. 适度存档：重要但不常用的信息存入档案记忆

【业务工具】
- search_semantic_scholar - 搜索学术论文
- generate_literature_review - 生成文献综述
- analyze_research_trends - 分析研究趋势
- find_research_gaps - 识别研究空白
- add_experiment - 记录实验
- add_reminder - 添加日程
- query_experiments - 查询实验记录
- list_reminders - 查看日程

【思考格式】
Thought: 分析当前情况，决定是否需要记忆操作
Action: 工具名称（可以是记忆工具或业务工具）
Action Input: {{"参数": "值"}}

最终答案格式：
Answer: 回答内容
"""
    
    async def run(
        self,
        task: str,
        callback: Optional[Callable[[Dict[str, Any]], None]] = None
    ) -> Dict[str, Any]:
        """
        执行任务，让 LLM 自主管理记忆
        """
        task_id = str(uuid.uuid4())
        
        self.memory_tools.add_message("user", task)
        
        if not self.client:
            return await self._simulate_execution(task, callback)
        
        messages = [
            {"role": "system", "content": self._get_system_prompt()},
            {"role": "user", "content": task}
        ]
        
        steps = []
        iteration = 0
        final_answer = None
        memory_operations = []
        
        while iteration < self.max_iterations:
            iteration += 1
            
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=self._get_all_tool_schemas(),
                    tool_choice="auto"
                )
                
                assistant_message = response.choices[0].message
                
                if assistant_message.content:
                    import re
                    thought_match = re.search(r'Thought:\s*(.+?)(?=Action:|Answer:|$)', 
                                              assistant_message.content, re.DOTALL)
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
                        
                        if tool_name in self.MEMORY_TOOL_NAMES:
                            observation_result = self.memory_tools.execute_tool(tool_name, tool_args)
                            memory_operations.append({
                                "tool": tool_name,
                                "arguments": tool_args,
                                "result": observation_result
                            })
                        else:
                            if is_async_tool(tool_name):
                                observation_result = await execute_async_tool(tool_name, tool_args)
                            else:
                                obs_str = execute_tool(tool_name, tool_args)
                                observation_result = {
                                    "success": True,
                                    "message": obs_str
                                }
                        
                        observation_content = observation_result.get("message", 
                                    json.dumps(observation_result, ensure_ascii=False))
                        
                        if observation_result.get("success"):
                            observation_content = f"✅ {observation_content}"
                        else:
                            observation_content = f"❌ {observation_result.get('error', '执行失败')}"
                        
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
                
                elif assistant_message.content:
                    import re
                    if "Answer:" in assistant_message.content:
                        answer_match = re.search(r'Answer:\s*(.+)', assistant_message.content, re.DOTALL)
                        final_answer = answer_match.group(1).strip() if answer_match else assistant_message.content
                    else:
                        final_answer = assistant_message.content
                    break
                    
            except Exception as e:
                error_step = {
                    "type": "error",
                    "content": f"执行错误: {str(e)}",
                    "iteration": iteration
                }
                steps.append(error_step)
                if callback:
                    await callback(error_step)
                break
        
        if not final_answer:
            final_answer = "抱歉，我无法完成这个任务。"
        
        self.memory_tools.add_message("assistant", final_answer)
        
        return {
            "task_id": task_id,
            "task": task,
            "steps": steps,
            "answer": final_answer,
            "iterations": iteration,
            "memory_operations": memory_operations,
            "memory_statistics": self.memory_tools.get_memory_statistics()
        }
    
    async def _simulate_execution(
        self,
        task: str,
        callback: Optional[Callable[[Dict[str, Any]], None]] = None
    ) -> Dict[str, Any]:
        """
        模拟执行（无 API 时）
        """
        steps = []
        memory_operations = []
        
        steps.append({
            "type": "thought",
            "content": f"收到任务：{task}",
            "iteration": 1
        })
        if callback:
            await callback(steps[-1])
        
        if "我叫" in task or "我是" in task:
            import re
            name_match = re.search(r"我[叫是](\w+)", task)
            if name_match:
                name = name_match.group(1)
                
                steps.append({
                    "type": "thought",
                    "content": "用户告诉我他的名字，这是重要信息，我应该记住",
                    "iteration": 2
                })
                if callback:
                    await callback(steps[-1])
                
                steps.append({
                    "type": "action",
                    "tool": "core_memory_append",
                    "arguments": {"section": "human", "content": f"用户姓名: {name}"},
                    "iteration": 3
                })
                if callback:
                    await callback(steps[-1])
                
                result = self.memory_tools.execute_tool(
                    "core_memory_append",
                    {"section": "human", "content": f"用户姓名: {name}"}
                )
                memory_operations.append({
                    "tool": "core_memory_append",
                    "arguments": {"section": "human", "content": f"用户姓名: {name}"},
                    "result": result
                })
                
                steps.append({
                    "type": "observation",
                    "content": f"✅ 已记住用户姓名: {name}",
                    "iteration": 4
                })
                if callback:
                    await callback(steps[-1])
                
                final_answer = f"你好{name}！很高兴认识你，我已经记住了你的名字。"
        
        elif "之前" in task or "上次" in task or "历史" in task:
            steps.append({
                "type": "thought",
                "content": "用户询问历史信息，我需要检索记忆",
                "iteration": 2
            })
            if callback:
                await callback(steps[-1])
            
            steps.append({
                "type": "action",
                "tool": "recall_memory_search",
                "arguments": {"query": task},
                "iteration": 3
            })
            if callback:
                await callback(steps[-1])
            
            result = self.memory_tools.execute_tool(
                "recall_memory_search",
                {"query": task, "n_results": 5}
            )
            memory_operations.append({
                "tool": "recall_memory_search",
                "arguments": {"query": task},
                "result": result
            })
            
            steps.append({
                "type": "observation",
                "content": f"✅ 检索到 {len(result.get('results', []))} 条相关记忆",
                "iteration": 4
            })
            if callback:
                await callback(steps[-1])
            
            final_answer = f"我检索了历史记忆，找到了相关信息。（模拟模式）"
        
        elif "记住" in task or "记住我" in task:
            content_to_remember = task.replace("记住", "").replace("请", "").strip()
            
            steps.append({
                "type": "thought",
                "content": "用户要求我记住信息，这应该存入档案记忆",
                "iteration": 2
            })
            if callback:
                await callback(steps[-1])
            
            steps.append({
                "type": "action",
                "tool": "archival_memory_insert",
                "arguments": {"content": content_to_remember},
                "iteration": 3
            })
            if callback:
                await callback(steps[-1])
            
            result = self.memory_tools.execute_tool(
                "archival_memory_insert",
                {"content": content_to_remember}
            )
            memory_operations.append({
                "tool": "archival_memory_insert",
                "arguments": {"content": content_to_remember},
                "result": result
            })
            
            steps.append({
                "type": "observation",
                "content": "✅ 信息已存入档案记忆",
                "iteration": 4
            })
            if callback:
                await callback(steps[-1])
            
            final_answer = f"好的，我已经记住了：「{content_to_remember}」。这个信息会被长期保存。"
        
        else:
            steps.append({
                "type": "thought",
                "content": "这是一个通用任务，我将尝试帮助用户",
                "iteration": 2
            })
            if callback:
                await callback(steps[-1])
            
            final_answer = f"我理解了您的任务：「{task}」。由于未配置API密钥，我正在模拟模式下运行。请配置API密钥以获得完整功能。"
        
        steps.append({
            "type": "answer",
            "content": final_answer,
            "iteration": len(steps) + 1
        })
        if callback:
            await callback(steps[-1])
        
        self.memory_tools.add_message("assistant", final_answer)
        
        return {
            "task_id": str(uuid.uuid4()),
            "task": task,
            "steps": steps,
            "answer": final_answer,
            "iterations": len(steps),
            "memory_operations": memory_operations,
            "memory_statistics": self.memory_tools.get_memory_statistics()
        }
    
    def get_core_memory(self) -> str:
        """获取核心记忆内容"""
        return self.memory_tools.core_memory.get()
    
    def get_memory_statistics(self) -> Dict[str, Any]:
        """获取记忆统计信息"""
        return self.memory_tools.get_memory_statistics()


_memgpt_agent: Optional[MemGPTAgent] = None


def get_memgpt_agent(user_id: str = "anonymous") -> MemGPTAgent:
    global _memgpt_agent
    if _memgpt_agent is None or _memgpt_agent.user_id != user_id:
        _memgpt_agent = MemGPTAgent(user_id=user_id)
    return _memgpt_agent
