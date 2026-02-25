import os
import sys
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path
import json

_lib_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "python_libs")
if os.path.exists(_lib_path):
    sys.path.insert(0, _lib_path)

try:
    import chromadb
    from chromadb.utils import embedding_functions
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False
    print("Warning: ChromaDB not available. Long-term memory features will be disabled.")


def get_chroma_path() -> str:
    if sys.platform == "win32":
        app_data = os.environ.get("APPDATA", "")
        if not app_data:
            app_data = os.path.join(os.path.expanduser("~"), "AppData", "Roaming")
        chroma_dir = os.path.join(app_data, "AcademicAssistant", "chroma_longterm")
    else:
        home = os.path.expanduser("~")
        chroma_dir = os.path.join(home, ".academicassistant", "chroma_longterm")
    
    os.makedirs(chroma_dir, exist_ok=True)
    return chroma_dir


class LongTermMemory:
    def __init__(self):
        self.client = None
        self.conversation_collection = None
        self.task_collection = None
        self.knowledge_collection = None
        self.embedding_function = None
        
        if CHROMA_AVAILABLE:
            self._init_chroma()
    
    def _init_chroma(self):
        try:
            chroma_path = get_chroma_path()
            print(f"[LongTermMemory] Initializing ChromaDB at: {chroma_path}")
            
            self.client = chromadb.PersistentClient(path=chroma_path)
            
            try:
                self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
                    model_name="BAAI/bge-small-zh-v1.5"
                )
            except Exception as e:
                print(f"[LongTermMemory] SentenceTransformer not available: {e}")
                self.embedding_function = None
            
            self.conversation_collection = self.client.get_or_create_collection(
                name="conversations",
                embedding_function=self.embedding_function,
                metadata={"description": "对话历史记忆"}
            )
            
            self.task_collection = self.client.get_or_create_collection(
                name="tasks",
                embedding_function=self.embedding_function,
                metadata={"description": "任务执行记忆"}
            )
            
            self.knowledge_collection = self.client.get_or_create_collection(
                name="knowledge",
                embedding_function=self.embedding_function,
                metadata={"description": "论文知识记忆"}
            )
            
            print("[LongTermMemory] ChromaDB initialized successfully")
        except Exception as e:
            print(f"[LongTermMemory] Error initializing ChromaDB: {e}")
            self.client = None
    
    def is_available(self) -> bool:
        return self.client is not None
    
    def save_conversation(
        self, 
        user_id: str, 
        conversation_id: str,
        user_message: str, 
        assistant_message: str,
        metadata: Dict = None
    ) -> Dict[str, Any]:
        if not self.is_available():
            return {"success": False, "error": "ChromaDB not available"}
        
        try:
            doc = f"用户: {user_message}\n助手: {assistant_message}"
            
            timestamp = datetime.now().isoformat()
            doc_id = f"conv_{conversation_id}_{timestamp.replace(':', '-').replace('.', '-')}"
            
            self.conversation_collection.add(
                documents=[doc],
                metadatas=[{
                    "user_id": user_id,
                    "conversation_id": conversation_id,
                    "timestamp": timestamp,
                    "user_message": user_message[:500],
                    "assistant_message": assistant_message[:500],
                    **(metadata or {})
                }],
                ids=[doc_id]
            )
            
            return {"success": True, "doc_id": doc_id}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def save_task(
        self,
        user_id: str,
        task_id: str,
        task: str,
        result: Dict[str, Any],
        task_type: str,
        evaluation_score: float = None
    ) -> Dict[str, Any]:
        if not self.is_available():
            return {"success": False, "error": "ChromaDB not available"}
        
        try:
            result_summary = json.dumps(result, ensure_ascii=False)[:2000]
            doc = f"任务: {task}\n结果: {result_summary}"
            
            timestamp = datetime.now().isoformat()
            
            self.task_collection.upsert(
                documents=[doc],
                metadatas=[{
                    "user_id": user_id,
                    "task_id": task_id,
                    "task_type": task_type,
                    "timestamp": timestamp,
                    "evaluation_score": evaluation_score or 0.0,
                    "task": task[:500]
                }],
                ids=[f"task_{task_id}"]
            )
            
            return {"success": True, "task_id": task_id}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def save_knowledge(
        self,
        paper_id: str,
        title: str,
        abstract: str,
        authors: List[str],
        keywords: List[str],
        source: str,
        user_id: str = None
    ) -> Dict[str, Any]:
        if not self.is_available():
            return {"success": False, "error": "ChromaDB not available"}
        
        try:
            doc = f"标题: {title}\n摘要: {abstract}\n关键词: {', '.join(keywords or [])}"
            
            timestamp = datetime.now().isoformat()
            
            self.knowledge_collection.upsert(
                documents=[doc],
                metadatas=[{
                    "paper_id": paper_id,
                    "title": title[:200],
                    "authors": json.dumps(authors, ensure_ascii=False),
                    "source": source,
                    "user_id": user_id or "anonymous",
                    "timestamp": timestamp
                }],
                ids=[f"paper_{paper_id}"]
            )
            
            return {"success": True, "paper_id": paper_id}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def recall_conversations(
        self, 
        query: str, 
        user_id: str = None, 
        n_results: int = 5
    ) -> List[Dict]:
        if not self.is_available():
            return []
        
        try:
            where_filter = None
            if user_id:
                where_filter = {"user_id": user_id}
            
            results = self.conversation_collection.query(
                query_texts=[query],
                n_results=n_results,
                where=where_filter
            )
            
            return self._format_query_results(results)
        except Exception as e:
            print(f"[LongTermMemory] Error recalling conversations: {e}")
            return []
    
    def recall_similar_tasks(
        self, 
        task: str, 
        user_id: str = None,
        n_results: int = 3
    ) -> List[Dict]:
        if not self.is_available():
            return []
        
        try:
            where_filter = None
            if user_id:
                where_filter = {"user_id": user_id}
            
            results = self.task_collection.query(
                query_texts=[task],
                n_results=n_results,
                where=where_filter
            )
            
            return self._format_query_results(results)
        except Exception as e:
            print(f"[LongTermMemory] Error recalling tasks: {e}")
            return []
    
    def search_knowledge(
        self, 
        query: str, 
        source: str = None,
        user_id: str = None,
        n_results: int = 10
    ) -> List[Dict]:
        if not self.is_available():
            return []
        
        try:
            where_filter = None
            conditions = []
            if source:
                conditions.append({"source": source})
            if user_id:
                conditions.append({"user_id": user_id})
            
            if len(conditions) == 1:
                where_filter = conditions[0]
            elif len(conditions) > 1:
                where_filter = {"$and": conditions}
            
            results = self.knowledge_collection.query(
                query_texts=[query],
                n_results=n_results,
                where=where_filter
            )
            
            return self._format_query_results(results)
        except Exception as e:
            print(f"[LongTermMemory] Error searching knowledge: {e}")
            return []
    
    def get_user_recent_tasks(
        self, 
        user_id: str, 
        limit: int = 10
    ) -> List[Dict]:
        if not self.is_available():
            return []
        
        try:
            results = self.task_collection.get(
                where={"user_id": user_id},
                limit=limit
            )
            
            return self._format_get_results(results)
        except Exception as e:
            print(f"[LongTermMemory] Error getting recent tasks: {e}")
            return []
    
    def get_user_papers(
        self,
        user_id: str,
        limit: int = 50
    ) -> List[Dict]:
        if not self.is_available():
            return []
        
        try:
            results = self.knowledge_collection.get(
                where={"user_id": user_id},
                limit=limit
            )
            
            return self._format_get_results(results)
        except Exception as e:
            print(f"[LongTermMemory] Error getting user papers: {e}")
            return []
    
    def delete_old_memories(self, days: int = 30) -> Dict[str, Any]:
        if not self.is_available():
            return {"success": False, "error": "ChromaDB not available"}
        
        try:
            cutoff_date = datetime.now().timestamp() - (days * 24 * 60 * 60)
            
            deleted_count = 0
            
            return {"success": True, "deleted_count": deleted_count}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_statistics(self) -> Dict[str, Any]:
        if not self.is_available():
            return {"success": False, "error": "ChromaDB not available"}
        
        try:
            conv_count = self.conversation_collection.count()
            task_count = self.task_collection.count()
            knowledge_count = self.knowledge_collection.count()
            
            return {
                "success": True,
                "statistics": {
                    "conversations": conv_count,
                    "tasks": task_count,
                    "knowledge": knowledge_count,
                    "total": conv_count + task_count + knowledge_count
                }
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _format_query_results(self, results: Dict) -> List[Dict]:
        formatted = []
        if not results or not results.get('documents'):
            return formatted
        
        for i, doc in enumerate(results['documents'][0]):
            formatted.append({
                "document": doc,
                "metadata": results['metadatas'][0][i] if results.get('metadatas') else {},
                "distance": results['distances'][0][i] if results.get('distances') else None
            })
        return formatted
    
    def _format_get_results(self, results: Dict) -> List[Dict]:
        formatted = []
        if not results or not results.get('documents'):
            return formatted
        
        for i, doc in enumerate(results['documents']):
            formatted.append({
                "document": doc,
                "metadata": results['metadatas'][i] if results.get('metadatas') else {}
            })
        return formatted


_long_term_memory: Optional[LongTermMemory] = None


def get_long_term_memory() -> LongTermMemory:
    global _long_term_memory
    if _long_term_memory is None:
        _long_term_memory = LongTermMemory()
    return _long_term_memory
