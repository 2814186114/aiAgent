from typing import Dict, Any, Optional, Callable, List
from datetime import datetime
import asyncio

from .evaluator import ResultEvaluator, EvaluationResult
from .analyzer import ReflectionAnalyzer, ReflectionResult
from .adjuster import PlanAdjuster


class ReflectionAgent:
    MAX_ITERATIONS = 2
    REFLECTION_ENABLED = True
    
    def __init__(self, base_agent, client=None, model: str = "deepseek-chat"):
        self.base_agent = base_agent
        self.evaluator = ResultEvaluator(client, model)
        self.analyzer = ReflectionAnalyzer(client, model)
        self.adjuster = PlanAdjuster(client, model)
        self.client = client
        self.model = model
    
    async def execute_task(self, task: str, callback: Optional[Callable] = None,
                          context: Dict[str, Any] = None) -> Dict[str, Any]:
        if not self.REFLECTION_ENABLED:
            return await self.base_agent.execute_task(task, callback, context)
        
        if context is None:
            context = {}
        
        iteration = 0
        current_task = task
        current_context = context.copy()
        best_result = None
        best_score = 0.0
        
        reflection_history = []
        
        while iteration <= self.MAX_ITERATIONS:
            if iteration > 0:
                await self._send_reflection_message(callback, {
                    "type": "reflection",
                    "iteration": iteration,
                    "max_iterations": self.MAX_ITERATIONS,
                    "adjusted_task": current_task,
                    "timestamp": datetime.now().isoformat()
                })
            
            result = await self.base_agent.execute_task(
                current_task, callback, current_context
            )
            
            task_type = result.get("task_type", "general")
            
            evaluation = await self.evaluator.evaluate(current_task, result, task_type)
            
            await self._send_evaluation_message(callback, {
                "type": "evaluation",
                "iteration": iteration,
                "scores": evaluation.to_dict(),
                "passed": evaluation.passed,
                "timestamp": datetime.now().isoformat()
            })
            
            if evaluation.overall_score > best_score:
                best_score = evaluation.overall_score
                best_result = result
            
            if evaluation.passed:
                result["reflection"] = {
                    "enabled": True,
                    "iterations": iteration,
                    "final_score": evaluation.overall_score,
                    "passed": True,
                    "history": reflection_history
                }
                return result
            
            if iteration >= self.MAX_ITERATIONS:
                break
            
            reflection = await self.analyzer.analyze(
                current_task, result, evaluation, task_type
            )
            
            reflection_history.append({
                "iteration": iteration,
                "evaluation": evaluation.to_dict(),
                "reflection": reflection.to_dict()
            })
            
            await self._send_reflection_message(callback, {
                "type": "reflection_analysis",
                "iteration": iteration,
                "failure_reason": reflection.failure_reason,
                "suggestions": reflection.improvement_suggestions,
                "will_retry": reflection.should_retry,
                "timestamp": datetime.now().isoformat()
            })
            
            if reflection.should_replan or reflection.should_retry:
                current_task = self.adjuster.adjust_task(
                    current_task, result, reflection, task_type
                )
                
                if reflection.adjusted_params:
                    current_context.update(reflection.adjusted_params)
            
            iteration += 1
        
        if best_result:
            best_result["reflection"] = {
                "enabled": True,
                "iterations": iteration,
                "final_score": best_score,
                "passed": False,
                "history": reflection_history,
                "message": "达到最大反思次数，返回最佳结果"
            }
            return best_result
        
        result["reflection"] = {
            "enabled": True,
            "iterations": iteration,
            "final_score": evaluation.overall_score if 'evaluation' in dir() else 0,
            "passed": False,
            "history": reflection_history,
            "message": "反思未能改善结果"
        }
        return result
    
    async def _send_reflection_message(self, callback: Optional[Callable], 
                                       message: Dict[str, Any]):
        if callback:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(message)
                else:
                    callback(message)
            except Exception as e:
                print(f"[ReflectionAgent] Failed to send message: {e}")
    
    async def _send_evaluation_message(self, callback: Optional[Callable],
                                       message: Dict[str, Any]):
        if callback:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(message)
                else:
                    callback(message)
            except Exception as e:
                print(f"[ReflectionAgent] Failed to send evaluation: {e}")
    
    def enable_reflection(self, enabled: bool = True):
        self.REFLECTION_ENABLED = enabled
    
    def set_max_iterations(self, max_iterations: int):
        self.MAX_ITERATIONS = max(0, min(5, max_iterations))
