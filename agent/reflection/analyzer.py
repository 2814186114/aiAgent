from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from datetime import datetime
import json
import re


@dataclass
class ReflectionResult:
    failure_reason: str = ""
    failure_type: str = ""
    improvement_suggestions: List[str] = field(default_factory=list)
    should_retry: bool = False
    should_replan: bool = False
    adjusted_params: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.5
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "failure_reason": self.failure_reason,
            "failure_type": self.failure_type,
            "improvement_suggestions": self.improvement_suggestions,
            "should_retry": self.should_retry,
            "should_replan": self.should_replan,
            "adjusted_params": self.adjusted_params,
            "confidence": self.confidence
        }


class ReflectionAnalyzer:
    FAILURE_TYPES = {
        "no_results": "未获取到结果",
        "incomplete_results": "结果不完整",
        "irrelevant_results": "结果不相关",
        "api_error": "API调用错误",
        "timeout": "请求超时",
        "invalid_params": "参数错误",
        "unknown": "未知错误"
    }
    
    def __init__(self, client=None, model: str = "deepseek-chat"):
        self.client = client
        self.model = model
    
    async def analyze(self, task: str, result: Dict[str, Any], 
                     evaluation: 'EvaluationResult',
                     task_type: str = "general") -> ReflectionResult:
        reflection = ReflectionResult()
        
        if evaluation.overall_score >= 0.6:
            return reflection
        
        reflection.failure_reason = evaluation.feedback
        
        reflection.failure_type = self._classify_failure(result, evaluation, task_type)
        
        rule_based_suggestions = self._get_rule_based_suggestions(
            reflection.failure_type, task, result, task_type
        )
        
        if self.client:
            llm_reflection = await self._llm_analyze(task, result, evaluation, task_type)
            if llm_reflection.failure_reason:
                reflection.failure_reason = llm_reflection.failure_reason
            if llm_reflection.improvement_suggestions:
                reflection.improvement_suggestions = llm_reflection.improvement_suggestions
            else:
                reflection.improvement_suggestions = rule_based_suggestions
            reflection.should_retry = llm_reflection.should_retry
            reflection.should_replan = llm_reflection.should_replan
            reflection.adjusted_params = llm_reflection.adjusted_params
            reflection.confidence = llm_reflection.confidence
        else:
            reflection.improvement_suggestions = rule_based_suggestions
            reflection.should_retry = self._should_retry(reflection.failure_type)
            reflection.should_replan = self._should_replan(reflection.failure_type)
            reflection.adjusted_params = self._get_adjusted_params(task, result, task_type)
        
        return reflection
    
    def _classify_failure(self, result: Dict[str, Any], evaluation: 'EvaluationResult',
                         task_type: str) -> str:
        if not result:
            return "no_results"
        
        if evaluation.completeness < 0.4:
            return "incomplete_results"
        
        if evaluation.accuracy < 0.4:
            return "irrelevant_results"
        
        final_answer = result.get("final_answer", "")
        if any(err in final_answer for err in ["错误", "失败", "异常", "error", "failed"]):
            return "api_error"
        
        if evaluation.completeness < 0.6 or evaluation.accuracy < 0.6:
            return "incomplete_results"
        
        return "unknown"
    
    def _get_rule_based_suggestions(self, failure_type: str, task: str,
                                    result: Dict[str, Any], task_type: str) -> List[str]:
        suggestions = []
        
        if failure_type == "no_results":
            suggestions.extend([
                "尝试使用不同的搜索关键词",
                "扩大搜索范围",
                "检查是否有拼写错误"
            ])
        
        elif failure_type == "incomplete_results":
            suggestions.extend([
                "增加搜索结果数量",
                "补充更多细节信息",
                "尝试更具体的查询"
            ])
        
        elif failure_type == "irrelevant_results":
            suggestions.extend([
                "优化搜索关键词",
                "添加更多限定条件",
                "尝试使用英文关键词"
            ])
        
        elif failure_type == "api_error":
            suggestions.extend([
                "稍后重试",
                "使用备用数据源",
                "简化请求参数"
            ])
        
        else:
            suggestions.append("重新执行任务")
        
        return suggestions
    
    def _should_retry(self, failure_type: str) -> bool:
        return failure_type in ["api_error", "timeout", "no_results"]
    
    def _should_replan(self, failure_type: str) -> bool:
        return failure_type in ["irrelevant_results", "invalid_params"]
    
    def _get_adjusted_params(self, task: str, result: Dict[str, Any], 
                            task_type: str) -> Dict[str, Any]:
        params = {}
        
        if task_type == "literature_research":
            params["max_papers"] = 50
            params["years"] = 3
            
            if result.get("research_result", {}).get("papers"):
                papers = result["research_result"]["papers"]
                if len(papers) < 5:
                    params["max_papers"] = 100
        
        elif task_type == "question_answering":
            params["detail_level"] = "high"
        
        return params
    
    async def _llm_analyze(self, task: str, result: Dict[str, Any],
                          evaluation: 'EvaluationResult',
                          task_type: str) -> ReflectionResult:
        if not self.client:
            return ReflectionResult()
        
        result_summary = str(result)[:1500]
        
        prompt = f"""请分析以下任务执行失败的原因并提供改进建议。

用户任务: {task}
任务类型: {task_type}
执行结果摘要: {result_summary}
评估结果: 完整性={evaluation.completeness:.2f}, 准确性={evaluation.accuracy:.2f}, 
         有用性={evaluation.usefulness:.2f}, 清晰度={evaluation.clarity:.2f}

请分析:
1. 失败的主要原因是什么
2. 应该如何改进
3. 是否需要重试或重新规划
4. 如果重试，应该调整哪些参数

请以JSON格式返回:
{{
    "failure_reason": "失败原因描述",
    "improvement_suggestions": ["建议1", "建议2"],
    "should_retry": true/false,
    "should_replan": true/false,
    "adjusted_params": {{"参数名": "新值"}},
    "confidence": 0.0-1.0
}}"""

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
                return ReflectionResult(
                    failure_reason=data.get("failure_reason", ""),
                    improvement_suggestions=data.get("improvement_suggestions", []),
                    should_retry=data.get("should_retry", False),
                    should_replan=data.get("should_replan", False),
                    adjusted_params=data.get("adjusted_params", {}),
                    confidence=float(data.get("confidence", 0.5))
                )
        except Exception as e:
            print(f"[ReflectionAnalyzer] LLM analysis failed: {e}")
        
        return ReflectionResult()
