import re
from typing import Dict, Any, List, Optional
from .long_term_memory import LongTermMemory, get_long_term_memory


class MemoryContextManager:
    MEMORY_KEYWORDS = [
        "昨天", "上次", "之前", "刚才", "刚刚",
        "记得", "记住", "历史", "以前的",
        "那些论文", "那个任务", "上次的结果",
        "之前找的", "之前搜索", "之前的"
    ]
    
    def __init__(self, memory: LongTermMemory = None):
        self.memory = memory or get_long_term_memory()
    
    def should_use_memory(self, current_task: str) -> bool:
        return any(kw in current_task for kw in self.MEMORY_KEYWORDS)
    
    def extract_memory_query(self, current_task: str) -> str:
        patterns = [
            r"昨天[搜索找]?(.+?)(?:的|相关)?论文",
            r"上次[搜索找]?(.+?)(?:的|相关)?论文",
            r"之前[搜索找]?(.+?)(?:的|相关)?论文",
            r"(.+?)相关的论文",
            r"那些(.+?)论文",
            r"之前找的(.+?)",
            r"之前搜索的(.+?)",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, current_task)
            if match:
                return match.group(1).strip()
        
        return current_task
    
    def build_context_for_task(
        self, 
        user_id: str,
        current_task: str
    ) -> str:
        if not self.memory.is_available():
            return ""
        
        context_parts = []
        
        similar_tasks = self.memory.recall_similar_tasks(
            task=current_task,
            user_id=user_id,
            n_results=3
        )
        if similar_tasks:
            context_parts.append("【历史相似任务】")
            for i, t in enumerate(similar_tasks):
                task_desc = t['metadata'].get('task', '')[:100]
                task_type = t['metadata'].get('task_type', '')
                score = t['metadata'].get('evaluation_score', 0)
                
                context_parts.append(f"{i+1}. [{task_type}] {task_desc}")
                if score and float(score) >= 0.7:
                    context_parts.append(f"   → 高质量结果(评分:{score})，可参考")
        
        recent_tasks = self.memory.get_user_recent_tasks(user_id, limit=5)
        if recent_tasks:
            context_parts.append("\n【最近任务】")
            for t in recent_tasks[:3]:
                task_type = t['metadata'].get('task_type', '')
                task_desc = t['metadata'].get('task', '')[:50]
                context_parts.append(f"- [{task_type}] {task_desc}")
        
        relevant_knowledge = self.memory.search_knowledge(
            query=current_task,
            user_id=user_id,
            n_results=5
        )
        if relevant_knowledge:
            context_parts.append("\n【相关知识】")
            for k in relevant_knowledge[:3]:
                title = k['metadata'].get('title', '')[:80]
                source = k['metadata'].get('source', '')
                context_parts.append(f"- [{source}] {title}")
        
        return "\n".join(context_parts) if context_parts else ""
    
    def get_memory_for_query(
        self,
        query: str,
        user_id: str = None
    ) -> Dict[str, Any]:
        if not self.memory.is_available():
            return {"available": False}
        
        memory_query = self.extract_memory_query(query)
        
        similar_tasks = self.memory.recall_similar_tasks(
            task=memory_query,
            user_id=user_id,
            n_results=3
        )
        
        relevant_papers = self.memory.search_knowledge(
            query=memory_query,
            user_id=user_id,
            n_results=10
        )
        
        conversations = self.memory.recall_conversations(
            query=memory_query,
            user_id=user_id,
            n_results=3
        )
        
        return {
            "available": True,
            "query": memory_query,
            "similar_tasks": similar_tasks,
            "relevant_papers": relevant_papers,
            "conversations": conversations,
            "has_relevant_memory": bool(similar_tasks or relevant_papers or conversations)
        }
    
    def format_memory_for_prompt(self, memory_data: Dict[str, Any]) -> str:
        if not memory_data.get("has_relevant_memory"):
            return ""
        
        parts = ["以下是相关的历史记忆，请参考："]
        
        if memory_data.get("similar_tasks"):
            parts.append("\n【相似任务】")
            for t in memory_data["similar_tasks"][:2]:
                parts.append(f"- {t['metadata'].get('task', '')[:100]}")
        
        if memory_data.get("relevant_papers"):
            parts.append("\n【相关论文】")
            for p in memory_data["relevant_papers"][:5]:
                parts.append(f"- {p['metadata'].get('title', '')[:80]}")
        
        return "\n".join(parts)
    
    def get_task_suggestions(
        self,
        user_id: str,
        current_task: str
    ) -> List[str]:
        suggestions = []
        
        if not self.memory.is_available():
            return suggestions
        
        similar_tasks = self.memory.recall_similar_tasks(
            task=current_task,
            user_id=user_id,
            n_results=3
        )
        
        for t in similar_tasks:
            score = t['metadata'].get('evaluation_score', 0)
            if score and float(score) >= 0.7:
                task_type = t['metadata'].get('task_type', '')
                if task_type == 'literature_research':
                    suggestions.append("之前做过类似的文献调研，结果质量很高")
                elif task_type == 'question_answering':
                    suggestions.append("之前回答过类似问题，可以参考")
        
        return suggestions[:3]


_memory_context_manager: Optional[MemoryContextManager] = None


def get_memory_context_manager() -> MemoryContextManager:
    global _memory_context_manager
    if _memory_context_manager is None:
        _memory_context_manager = MemoryContextManager()
    return _memory_context_manager
