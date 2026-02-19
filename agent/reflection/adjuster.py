from typing import Dict, Any, List
from dataclasses import dataclass


@dataclass
class PlanAdjustment:
    action: str
    step_id: str = ""
    new_params: Dict[str, Any] = None
    new_steps: List[Dict[str, Any]] = None
    reason: str = ""
    
    def __post_init__(self):
        if self.new_params is None:
            self.new_params = {}
        if self.new_steps is None:
            self.new_steps = []


class PlanAdjuster:
    def __init__(self, client=None, model: str = "deepseek-chat"):
        self.client = client
        self.model = model
    
    def adjust_task(self, task: str, result: Dict[str, Any], 
                   reflection: 'ReflectionResult',
                   task_type: str = "general") -> str:
        if reflection.should_replan:
            return self._replan_task(task, result, reflection)
        else:
            return self._refine_task(task, result, reflection)
    
    def _refine_task(self, task: str, result: Dict[str, Any],
                    reflection: 'ReflectionResult') -> str:
        refined_task = task
        
        if reflection.adjusted_params:
            if reflection.adjusted_params.get("max_papers"):
                refined_task = f"{task}，请搜索更多结果（至少{reflection.adjusted_params['max_papers']}篇）"
            
            if reflection.adjusted_params.get("detail_level") == "high":
                refined_task = f"请详细回答：{task}"
        
        if "incomplete" in reflection.failure_type:
            refined_task = f"{task}，请提供更详细完整的回答"
        
        if "irrelevant" in reflection.failure_type:
            refined_task = f"{task}，请确保结果与问题高度相关"
        
        return refined_task
    
    def _replan_task(self, task: str, result: Dict[str, Any],
                    reflection: 'ReflectionResult') -> str:
        suggestions = reflection.improvement_suggestions
        
        if suggestions:
            hint = "，".join(suggestions[:2])
            return f"{task}（注意：{hint}）"
        
        return f"{task}，请重新规划并执行"
    
    def adjust_params(self, original_params: Dict[str, Any],
                     reflection: 'ReflectionResult') -> Dict[str, Any]:
        adjusted = original_params.copy()
        
        if reflection.adjusted_params:
            adjusted.update(reflection.adjusted_params)
        
        return adjusted
    
    def get_retry_strategy(self, failure_type: str, attempt: int) -> Dict[str, Any]:
        strategies = {
            "no_results": {
                "expand_search": True,
                "use_fallback": attempt >= 2
            },
            "incomplete_results": {
                "increase_limit": True,
                "add_detail": True
            },
            "irrelevant_results": {
                "refine_query": True,
                "use_synonyms": attempt >= 2
            },
            "api_error": {
                "use_cache": True,
                "simplify_request": attempt >= 2
            },
            "timeout": {
                "reduce_timeout": True,
                "use_smaller_batch": True
            }
        }
        
        return strategies.get(failure_type, {"retry": True})
