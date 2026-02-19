import os
import sys
import json
import asyncio
import re
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

class TaskStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

class PlanStep:
    def __init__(self, step_id: str, name: str, description: str):
        self.step_id = step_id
        self.name = name
        self.description = description
        self.status = TaskStatus.PENDING
        self.steps: List[Dict] = []
        self.result: Optional[Any] = None
        self.start_time: Optional[str] = None
        self.end_time: Optional[str] = None

class PlanningAgent:
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
    
    def _simulate_plan(self, task: str) -> List[PlanStep]:
        task_lower = task.lower()
        
        if any(kw in task_lower for kw in ["搜索", "论文", "文献", "研究"]):
            return [
                PlanStep("search", "搜索相关资料", "搜索与任务相关的论文、文献和资料"),
                PlanStep("analyze", "分析资料", "分析搜索到的资料，提取关键信息"),
                PlanStep("summarize", "总结整理", "总结分析结果，形成完整答案")
            ]
        elif any(kw in task_lower for kw in ["写", "报告", "总结", "文档"]):
            return [
                PlanStep("outline", "制定大纲", "制定报告的结构和大纲"),
                PlanStep("collect", "收集内容", "收集报告所需的内容和数据"),
                PlanStep("write", "撰写报告", "按照大纲撰写完整报告")
            ]
        elif any(kw in task_lower for kw in ["实验", "测试", "验证"]):
            return [
                PlanStep("design", "设计实验", "设计实验方案和步骤"),
                PlanStep("execute", "执行实验", "按照方案执行实验"),
                PlanStep("analyze", "分析结果", "分析实验数据和结果")
            ]
        else:
            return [
                PlanStep("understand", "理解任务", "深入理解任务需求和目标"),
                PlanStep("execute", "执行任务", "按照理解执行任务"),
                PlanStep("verify", "验证结果", "验证执行结果是否满足需求")
            ]
    
    async def _llm_plan(self, task: str) -> List[PlanStep]:
        if not self.client:
            return self._simulate_plan(task)
        
        prompt = f"""请将以下任务拆解为 3-5 个清晰的步骤，以JSON格式返回：

任务：{task}

返回格式：
{{
    "steps": [
        {{
            "step_id": "唯一ID",
            "name": "步骤名称",
            "description": "步骤描述"
        }}
    ]
}}

只返回JSON，不要其他内容。"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )
            
            content = response.choices[0].message.content
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                data = json.loads(json_match.group())
                steps_data = data.get("steps", [])
                return [
                    PlanStep(s.get("step_id", f"step_{i}"), 
                             s.get("name", f"步骤{i+1}"), 
                             s.get("description", ""))
                    for i, s in enumerate(steps_data)
                ]
        except Exception as e:
            print(f"LLM planning error: {e}")
        
        return self._simulate_plan(task)
    
    def _simulate_step_execution(self, step: PlanStep, task: str) -> str:
        return f"已完成「{step.name}」：{step.description}"
    
    async def execute_task(
        self,
        task: str,
        callback: Optional[Callable[[Dict[str, Any]], None]] = None
    ) -> Dict[str, Any]:
        results = {
            "task": task,
            "started_at": datetime.now().isoformat(),
            "steps": [],
            "plan": [],
            "final_answer": ""
        }
        
        self._send_update("planning", 0, "正在规划任务...", callback)
        self._add_step('thought', f'开始处理任务：{task}，首先进行任务规划', callback)
        
        plan_steps = await self._llm_plan(task)
        
        plan_data = []
        for s in plan_steps:
            plan_data.append({
                "step_id": s.step_id,
                "name": s.name,
                "description": s.description,
                "status": s.status.value,
                "steps": []
            })
        results["plan"] = plan_data
        
        self._send_task_list(plan_steps, callback)
        self._add_step('thought', f'已规划 {len(plan_steps)} 个执行步骤，准备开始执行', callback)
        
        total_steps = len(plan_steps)
        final_answer_parts = []
        
        for i, step in enumerate(plan_steps):
            progress = int((i / total_steps) * 100)
            
            self._update_step_status(step, TaskStatus.IN_PROGRESS, callback)
            self._add_task_step(step.step_id, 'thought', f'开始执行「{step.name}」', callback)
            self._send_update("executing", progress, f"正在执行：{step.name}", callback)
            
            step_result = self._simulate_step_execution(step, task)
            final_answer_parts.append(step_result)
            
            self._add_task_step(step.step_id, 'observation', step_result, callback)
            self._update_step_status(step, TaskStatus.COMPLETED, callback)
            
            plan_data[i]["status"] = TaskStatus.COMPLETED.value
            plan_data[i]["steps"].extend([
                {"step_type": "thought", "content": f"开始执行「{step.name}」"},
                {"step_type": "observation", "content": step_result}
            ])
            
            await asyncio.sleep(0.3)
        
        self._send_update("completed", 100, "任务完成！", callback)
        self._add_step('thought', '所有步骤执行完毕！', callback)
        
        results["final_answer"] = "\n\n".join(final_answer_parts)
        results["completed_at"] = datetime.now().isoformat()
        results["plan"] = plan_data
        
        return {
            "success": True,
            **results
        }
    
    def _send_update(self, state: str, progress: int, task_desc: str, 
                     callback: Optional[Callable] = None):
        if callback:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(callback({
                    "type": "progress",
                    "state": state,
                    "progress": progress,
                    "task": task_desc,
                    "timestamp": datetime.now().isoformat()
                }))
    
    def _add_step(self, step_type: str, content: str, 
                  callback: Optional[Callable] = None):
        if callback:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(callback({
                    "type": "step",
                    "step_type": step_type,
                    "content": content,
                    "timestamp": datetime.now().isoformat()
                }))
    
    def _send_task_list(self, steps: List[PlanStep], 
                        callback: Optional[Callable] = None):
        if callback:
            task_data = [
                {
                    "task_id": s.step_id,
                    "name": s.name,
                    "description": s.description,
                    "status": s.status.value
                }
                for s in steps
            ]
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(callback({
                    "type": "task_list",
                    "tasks": task_data,
                    "timestamp": datetime.now().isoformat()
                }))
    
    def _update_step_status(self, step: PlanStep, status: TaskStatus, 
                            callback: Optional[Callable] = None):
        step.status = status
        if status == TaskStatus.IN_PROGRESS:
            step.start_time = datetime.now().isoformat()
        elif status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
            step.end_time = datetime.now().isoformat()
        
        if callback:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(callback({
                    "type": "task_update",
                    "task_id": step.step_id,
                    "status": status.value,
                    "timestamp": datetime.now().isoformat()
                }))
    
    def _add_task_step(self, task_id: str, step_type: str, content: str, 
                       callback: Optional[Callable] = None):
        if callback:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(callback({
                    "type": "task_step",
                    "task_id": task_id,
                    "step_type": step_type,
                    "content": content,
                    "timestamp": datetime.now().isoformat()
                }))
