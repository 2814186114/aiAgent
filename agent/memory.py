import os
import sys
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path

_lib_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "python_libs")
if os.path.exists(_lib_path):
    sys.path.insert(0, _lib_path)

try:
    import chromadb
    from chromadb.utils import embedding_functions
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False
    print("Warning: ChromaDB not available. Memory features will be disabled.")


def get_chroma_path() -> str:
    if sys.platform == "win32":
        app_data = os.environ.get("APPDATA", "")
        if not app_data:
            app_data = os.path.join(os.path.expanduser("~"), "AppData", "Roaming")
        chroma_dir = os.path.join(app_data, "AcademicAssistant", "chroma")
    else:
        home = os.path.expanduser("~")
        chroma_dir = os.path.join(home, ".academicassistant", "chroma")
    
    os.makedirs(chroma_dir, exist_ok=True)
    return chroma_dir


class MemoryManager:
    def __init__(self):
        self.client = None
        self.task_history_collection = None
        self.user_preferences_collection = None
        self.embedding_function = None
        
        if CHROMA_AVAILABLE:
            self._init_chroma()
    
    def _init_chroma(self):
        try:
            chroma_path = get_chroma_path()
            print(f"Initializing ChromaDB at: {chroma_path}")
            
            self.client = chromadb.PersistentClient(path=chroma_path)
            
            try:
                self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
                    model_name="BAAI/bge-small-zh-v1.5"
                )
            except Exception:
                print("Warning: SentenceTransformer not available, using default embedding")
                self.embedding_function = None
            
            self.task_history_collection = self.client.get_or_create_collection(
                name="task_history",
                embedding_function=self.embedding_function,
                metadata={"description": "History of completed tasks"}
            )
            
            self.user_preferences_collection = self.client.get_or_create_collection(
                name="user_preferences",
                embedding_function=self.embedding_function,
                metadata={"description": "User preferences"}
            )
            
            print("ChromaDB initialized successfully")
        except Exception as e:
            print(f"Error initializing ChromaDB: {e}")
            self.client = None
    
    def is_available(self) -> bool:
        return self.client is not None
    
    def store_task_history(
        self,
        task_id: str,
        task_description: str,
        steps_summary: str,
        result: str,
        success: bool = True
    ) -> Dict[str, Any]:
        if not self.is_available():
            return {"success": False, "error": "ChromaDB not available"}
        
        try:
            document = f"任务: {task_description}\n\n步骤摘要:\n{steps_summary}\n\n结果:\n{result}"
            
            timestamp = datetime.now().isoformat()
            
            self.task_history_collection.add(
                documents=[document],
                metadatas=[{
                    "timestamp": timestamp,
                    "task_id": task_id,
                    "success": success,
                    "task_description": task_description
                }],
                ids=[f"task_{task_id}"]
            )
            
            return {"success": True, "task_id": task_id}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def recall_task_history(
        self,
        query: str,
        top_k: int = 3
    ) -> Dict[str, Any]:
        if not self.is_available():
            return {"success": False, "error": "ChromaDB not available", "results": []}
        
        try:
            results = self.task_history_collection.query(
                query_texts=[query],
                n_results=top_k
            )
            
            formatted_results = []
            if results and results.get("documents") and len(results["documents"]) > 0:
                for i, doc in enumerate(results["documents"][0]):
                    metadata = results["metadatas"][0][i] if results.get("metadatas") else {}
                    formatted_results.append({
                        "document": doc,
                        "metadata": metadata,
                        "distance": results["distances"][0][i] if results.get("distances") else None
                    })
            
            return {"success": True, "results": formatted_results}
        except Exception as e:
            return {"success": False, "error": str(e), "results": []}
    
    def update_preference(self, key: str, value: str) -> Dict[str, Any]:
        if not self.is_available():
            return {"success": False, "error": "ChromaDB not available"}
        
        try:
            doc_id = f"pref_{key}"
            
            self.user_preferences_collection.upsert(
                documents=[value],
                metadatas=[{
                    "key": key,
                    "timestamp": datetime.now().isoformat()
                }],
                ids=[doc_id]
            )
            
            return {"success": True, "key": key, "value": value}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_preference(self, key: str, default: Optional[str] = None) -> Dict[str, Any]:
        if not self.is_available():
            return {"success": False, "error": "ChromaDB not available", "value": default}
        
        try:
            doc_id = f"pref_{key}"
            results = self.user_preferences_collection.get(ids=[doc_id])
            
            if results and results.get("documents") and len(results["documents"]) > 0:
                return {"success": True, "key": key, "value": results["documents"][0]}
            else:
                return {"success": True, "key": key, "value": default}
        except Exception as e:
            return {"success": False, "error": str(e), "value": default}
    
    def list_all_preferences(self) -> Dict[str, Any]:
        if not self.is_available():
            return {"success": False, "error": "ChromaDB not available", "preferences": {}}
        
        try:
            results = self.user_preferences_collection.get()
            
            preferences = {}
            if results and results.get("documents") and results.get("metadatas"):
                for i, doc in enumerate(results["documents"]):
                    metadata = results["metadatas"][i]
                    key = metadata.get("key", "")
                    if key:
                        preferences[key] = doc
            
            return {"success": True, "preferences": preferences}
        except Exception as e:
            return {"success": False, "error": str(e), "preferences": {}}


_memory_manager: Optional[MemoryManager] = None


def get_memory_manager() -> MemoryManager:
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = MemoryManager()
    return _memory_manager