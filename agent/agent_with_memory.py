import os
import sys
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable

_lib_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "python_libs")
if os.path.exists(_lib_path):
    sys.path.insert(0, _lib_path)

from .unified_agent import UnifiedAgent, TaskType
from .long_term_memory import LongTermMemory, get_long_term_memory
from .memory_context import MemoryContextManager, get_memory_context_manager


class UnifiedAgentWithMemory:
    def __init__(self, base_agent: UnifiedAgent = None):
        self.base_agent = base_agent or UnifiedAgent()
        self.memory = get_long_term_memory()
        self.memory_manager = get_memory_context_manager()
    
    async def execute_task(
        self,
        task: str,
        callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        context_input: Optional[Dict[str, Any]] = None,
        user_id: str = "anonymous"
    ) -> Dict[str, Any]:
        enhanced_context = context_input or {}
        
        if self.memory.is_available():
            if self.memory_manager.should_use_memory(task):
                await self._send_memory_recall_start(callback)
                
                memory_data = self.memory_manager.get_memory_for_query(
                    query=task,
                    user_id=user_id
                )
                
                if memory_data.get("has_relevant_memory"):
                    enhanced_context["memory"] = memory_data
                    
                    memory_context = self.memory_manager.format_memory_for_prompt(memory_data)
                    if memory_context:
                        enhanced_context["memory_context"] = memory_context
                    
                    await self._send_memory_recall_result(callback, memory_data)
            else:
                memory_context = self.memory_manager.build_context_for_task(
                    user_id=user_id,
                    current_task=task
                )
                if memory_context:
                    enhanced_context["memory_context"] = memory_context
        
        result = await self.base_agent.execute_task(
            task=task,
            callback=callback,
            context_input=enhanced_context
        )
        
        if self.memory.is_available():
            await self._save_task_result(
                user_id=user_id,
                task=task,
                result=result
            )
            
            if result.get("research_result", {}).get("papers"):
                await self._save_papers(
                    user_id=user_id,
                    papers=result["research_result"]["papers"]
                )
        
        return result
    
    async def _send_memory_recall_start(self, callback: Optional[Callable] = None):
        if callback:
            try:
                await callback({
                    "type": "memory_recall_start",
                    "message": "正在检索历史记忆...",
                    "timestamp": datetime.now().isoformat()
                })
            except Exception as e:
                print(f"[MemoryAgent] Failed to send memory recall start: {e}")
    
    async def _send_memory_recall_result(
        self, 
        callback: Optional[Callable] = None,
        memory_data: Dict[str, Any] = None
    ):
        if callback:
            try:
                await callback({
                    "type": "memory_recall",
                    "similar_tasks_count": len(memory_data.get("similar_tasks", [])),
                    "papers_count": len(memory_data.get("relevant_papers", [])),
                    "conversations_count": len(memory_data.get("conversations", [])),
                    "has_relevant_memory": memory_data.get("has_relevant_memory", False),
                    "timestamp": datetime.now().isoformat()
                })
            except Exception as e:
                print(f"[MemoryAgent] Failed to send memory recall result: {e}")
    
    async def _save_task_result(
        self,
        user_id: str,
        task: str,
        result: Dict[str, Any]
    ):
        try:
            task_id = result.get("task_id") or f"task_{datetime.now().timestamp()}"
            task_type = result.get("task_type", "general")
            
            evaluation_score = None
            if result.get("evaluation"):
                evaluation_score = result["evaluation"].get("overall_score")
            
            save_result = self.memory.save_task(
                user_id=user_id,
                task_id=task_id,
                task=task,
                result=result,
                task_type=task_type,
                evaluation_score=evaluation_score
            )
            
            if save_result.get("success"):
                print(f"[MemoryAgent] Task saved to long-term memory: {task_id}")
            else:
                print(f"[MemoryAgent] Failed to save task: {save_result.get('error')}")
        except Exception as e:
            print(f"[MemoryAgent] Error saving task to memory: {e}")
    
    async def _save_papers(
        self,
        user_id: str,
        papers: List[Dict[str, Any]]
    ):
        for paper in papers[:20]:
            try:
                paper_id = paper.get("paper_id") or paper.get("id") or f"paper_{datetime.now().timestamp()}"
                
                self.memory.save_knowledge(
                    paper_id=paper_id,
                    title=paper.get("title", ""),
                    abstract=paper.get("abstract", ""),
                    authors=paper.get("authors", []),
                    keywords=paper.get("keywords", []),
                    source=paper.get("source", "unknown"),
                    user_id=user_id
                )
            except Exception as e:
                print(f"[MemoryAgent] Error saving paper to memory: {e}")
    
    def save_conversation(
        self,
        user_id: str,
        conversation_id: str,
        user_message: str,
        assistant_message: str,
        metadata: Dict = None
    ) -> Dict[str, Any]:
        if not self.memory.is_available():
            return {"success": False, "error": "Memory not available"}
        
        return self.memory.save_conversation(
            user_id=user_id,
            conversation_id=conversation_id,
            user_message=user_message,
            assistant_message=assistant_message,
            metadata=metadata
        )
    
    def recall_conversations(
        self,
        query: str,
        user_id: str = None,
        n_results: int = 5
    ) -> List[Dict]:
        return self.memory.recall_conversations(
            query=query,
            user_id=user_id,
            n_results=n_results
        )
    
    def recall_similar_tasks(
        self,
        task: str,
        user_id: str = None,
        n_results: int = 3
    ) -> List[Dict]:
        return self.memory.recall_similar_tasks(
            task=task,
            user_id=user_id,
            n_results=n_results
        )
    
    def search_knowledge(
        self,
        query: str,
        user_id: str = None,
        n_results: int = 10
    ) -> List[Dict]:
        return self.memory.search_knowledge(
            query=query,
            user_id=user_id,
            n_results=n_results
        )
    
    def get_user_recent_tasks(
        self,
        user_id: str,
        limit: int = 10
    ) -> List[Dict]:
        return self.memory.get_user_recent_tasks(
            user_id=user_id,
            limit=limit
        )
    
    def get_user_papers(
        self,
        user_id: str,
        limit: int = 50
    ) -> List[Dict]:
        return self.memory.get_user_papers(
            user_id=user_id,
            limit=limit
        )
    
    def get_memory_statistics(self) -> Dict[str, Any]:
        return self.memory.get_statistics()
    
    def is_memory_available(self) -> bool:
        return self.memory.is_available()


_agent_with_memory: Optional[UnifiedAgentWithMemory] = None


def get_agent_with_memory() -> UnifiedAgentWithMemory:
    global _agent_with_memory
    if _agent_with_memory is None:
        _agent_with_memory = UnifiedAgentWithMemory()
    return _agent_with_memory
