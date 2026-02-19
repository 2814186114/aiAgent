from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from datetime import datetime
import json
import re


@dataclass
class EvaluationResult:
    completeness: float = 0.0
    accuracy: float = 0.0
    usefulness: float = 0.0
    clarity: float = 0.0
    passed: bool = False
    feedback: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def overall_score(self) -> float:
        return (self.completeness * 0.3 + 
                self.accuracy * 0.3 + 
                self.usefulness * 0.25 + 
                self.clarity * 0.15)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "completeness": self.completeness,
            "accuracy": self.accuracy,
            "usefulness": self.usefulness,
            "clarity": self.clarity,
            "overall_score": self.overall_score,
            "passed": self.passed,
            "feedback": self.feedback,
            "details": self.details
        }


class ResultEvaluator:
    PASS_THRESHOLD = 0.6
    TASK_TYPE_CRITERIA = {
        "literature_research": {
            "min_papers_ratio": 0.8,
            "required_fields": ["papers"],
            "quality_checks": ["has_abstracts", "has_titles", "relevant_topic"]
        },
        "schedule_planning": {
            "required_fields": ["schedule", "reminder"],
            "quality_checks": ["has_time", "has_content", "no_conflict"]
        },
        "experiment_management": {
            "required_fields": ["experiments"],
            "quality_checks": ["has_data", "has_metrics"]
        },
        "question_answering": {
            "min_answer_length": 50,
            "quality_checks": ["answered_question", "has_explanation"]
        },
        "general": {
            "min_result_length": 20,
            "quality_checks": ["has_content"]
        }
    }
    
    def __init__(self, client=None, model: str = "deepseek-chat"):
        self.client = client
        self.model = model
    
    async def evaluate(self, task: str, result: Dict[str, Any], 
                      task_type: str = "general") -> EvaluationResult:
        evaluation = EvaluationResult()
        
        evaluation.completeness = self._evaluate_completeness(task, result, task_type)
        evaluation.accuracy = self._evaluate_accuracy(task, result, task_type)
        evaluation.usefulness = self._evaluate_usefulness(task, result, task_type)
        evaluation.clarity = self._evaluate_clarity(task, result)
        
        if self.client:
            llm_evaluation = await self._llm_evaluate(task, result, task_type)
            evaluation.completeness = (evaluation.completeness + llm_evaluation.completeness) / 2
            evaluation.accuracy = (evaluation.accuracy + llm_evaluation.accuracy) / 2
            evaluation.usefulness = (evaluation.usefulness + llm_evaluation.usefulness) / 2
            evaluation.clarity = (evaluation.clarity + llm_evaluation.clarity) / 2
            if llm_evaluation.feedback:
                evaluation.feedback = llm_evaluation.feedback
        
        evaluation.passed = evaluation.overall_score >= self.PASS_THRESHOLD
        
        if not evaluation.feedback:
            evaluation.feedback = self._generate_feedback(evaluation, task_type)
        
        evaluation.details = {
            "task_type": task_type,
            "evaluated_at": datetime.now().isoformat(),
            "result_keys": list(result.keys()) if isinstance(result, dict) else []
        }
        
        return evaluation
    
    def _evaluate_completeness(self, task: str, result: Dict[str, Any], 
                               task_type: str) -> float:
        if not result:
            return 0.0
        
        criteria = self.TASK_TYPE_CRITERIA.get(task_type, self.TASK_TYPE_CRITERIA["general"])
        score = 0.0
        
        if task_type == "literature_research":
            papers = result.get("research_result", {}).get("papers", [])
            if not papers:
                papers = result.get("papers", [])
            
            if papers:
                score += 0.4
                if len(papers) >= 5:
                    score += 0.3
                if all(p.get("title") for p in papers):
                    score += 0.2
                if all(p.get("abstract") for p in papers):
                    score += 0.1
            else:
                final_answer = result.get("final_answer", "")
                if final_answer and len(final_answer) > 100:
                    score += 0.5
        
        elif task_type == "question_answering":
            answer = result.get("final_answer", "")
            if answer:
                score += 0.3
                if len(answer) >= 50:
                    score += 0.4
                if len(answer) >= 200:
                    score += 0.3
        
        elif task_type == "schedule_planning":
            if result.get("schedule_info") or result.get("reminder"):
                score += 0.5
            if result.get("final_answer"):
                score += 0.3
            if "成功" in result.get("final_answer", ""):
                score += 0.2
        
        elif task_type == "experiment_management":
            if result.get("experiments") or result.get("experiment_result"):
                score += 0.5
            if result.get("final_answer"):
                score += 0.3
            if result.get("statistics"):
                score += 0.2
        
        else:
            if result.get("final_answer"):
                score += 0.5
                if len(result.get("final_answer", "")) > 50:
                    score += 0.3
            if result.get("plan") and len(result.get("plan", [])) > 0:
                score += 0.2
        
        return min(1.0, score)
    
    def _evaluate_accuracy(self, task: str, result: Dict[str, Any], 
                          task_type: str) -> float:
        if not result:
            return 0.0
        
        score = 0.7
        
        if task_type == "literature_research":
            papers = result.get("research_result", {}).get("papers", [])
            if not papers:
                papers = result.get("papers", [])
            
            if papers:
                task_lower = task.lower()
                keywords = re.findall(r'[\u4e00-\u9fa5]+|[a-zA-Z]{2,}', task)
                
                relevant_count = 0
                for paper in papers[:10]:
                    title = paper.get("title", "").lower()
                    abstract = paper.get("abstract", "").lower()
                    
                    for kw in keywords:
                        if kw.lower() in title or kw.lower() in abstract:
                            relevant_count += 1
                            break
                
                if papers:
                    relevance_ratio = relevant_count / min(len(papers), 10)
                    score = 0.5 + relevance_ratio * 0.5
        
        elif task_type == "question_answering":
            answer = result.get("final_answer", "")
            if answer:
                if "抱歉" in answer or "无法" in answer or "错误" in answer:
                    score = 0.3
                elif len(answer) > 100:
                    score = 0.8
                else:
                    score = 0.6
        
        return min(1.0, score)
    
    def _evaluate_usefulness(self, task: str, result: Dict[str, Any], 
                            task_type: str) -> float:
        if not result:
            return 0.0
        
        score = 0.5
        
        if task_type == "literature_research":
            papers = result.get("research_result", {}).get("papers", [])
            if not papers:
                papers = result.get("papers", [])
            
            if papers:
                if any(p.get("url") for p in papers):
                    score += 0.2
                if any(p.get("pdf_url") for p in papers):
                    score += 0.1
                if any(p.get("citation_count", 0) > 0 for p in papers):
                    score += 0.1
                if any(p.get("abstract") for p in papers):
                    score += 0.1
        
        elif task_type == "question_answering":
            answer = result.get("final_answer", "")
            if "```" in answer:
                score += 0.2
            if answer.count("\n") > 3:
                score += 0.1
            if any(marker in answer for marker in ["1.", "2.", "•", "-", "第一"]):
                score += 0.1
            if "例如" in answer or "比如" in answer or "example" in answer.lower():
                score += 0.1
        
        return min(1.0, score)
    
    def _evaluate_clarity(self, task: str, result: Dict[str, Any]) -> float:
        if not result:
            return 0.0
        
        answer = result.get("final_answer", "")
        if not answer:
            return 0.5
        
        score = 0.5
        
        if len(answer) > 50:
            score += 0.1
        if len(answer) > 200:
            score += 0.1
        
        paragraphs = answer.split("\n\n")
        if len(paragraphs) > 1:
            score += 0.1
        
        if "```" in answer:
            score += 0.1
        
        if answer.count("##") > 0:
            score += 0.1
        
        return min(1.0, score)
    
    async def _llm_evaluate(self, task: str, result: Dict[str, Any], 
                           task_type: str) -> EvaluationResult:
        if not self.client:
            return EvaluationResult()
        
        result_summary = str(result)[:2000]
        
        prompt = f"""请评估以下任务执行结果的质量。

用户任务: {task}
任务类型: {task_type}
执行结果摘要: {result_summary}

请从以下维度评分(0.0-1.0):
1. 完整性: 结果是否完整回答了用户的问题或完成了用户的请求
2. 准确性: 结果内容是否准确、相关
3. 有用性: 结果对用户是否有实际帮助价值
4. 清晰度: 结果表达是否清晰易懂

请以JSON格式返回:
{{
    "completeness": 0.0-1.0,
    "accuracy": 0.0-1.0,
    "usefulness": 0.0-1.0,
    "clarity": 0.0-1.0,
    "feedback": "简短的评估反馈"
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
                return EvaluationResult(
                    completeness=float(data.get("completeness", 0.5)),
                    accuracy=float(data.get("accuracy", 0.5)),
                    usefulness=float(data.get("usefulness", 0.5)),
                    clarity=float(data.get("clarity", 0.5)),
                    feedback=data.get("feedback", "")
                )
        except Exception as e:
            print(f"[Evaluator] LLM evaluation failed: {e}")
        
        return EvaluationResult()
    
    def _generate_feedback(self, evaluation: EvaluationResult, task_type: str) -> str:
        feedback_parts = []
        
        if evaluation.completeness < 0.5:
            feedback_parts.append("结果不够完整")
        elif evaluation.completeness < 0.7:
            feedback_parts.append("结果基本完整但可以更详细")
        
        if evaluation.accuracy < 0.5:
            feedback_parts.append("结果准确性需要提高")
        
        if evaluation.usefulness < 0.5:
            feedback_parts.append("结果的实用性有待加强")
        
        if evaluation.clarity < 0.5:
            feedback_parts.append("结果表达可以更清晰")
        
        if not feedback_parts:
            return "结果质量良好"
        
        return "；".join(feedback_parts)
