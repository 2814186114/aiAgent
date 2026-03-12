"""
MemGPT 风格的记忆系统调用接口
让 LLM 自主决定何时读写记忆

核心思想：
- LLM 通过 tool_calls 主动调用记忆操作
- 类似操作系统的系统调用 (syscall)
- LLM 自己决定何时存储、检索、更新记忆
"""

import json
import uuid
import math
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field


@dataclass
class MemoryItem:
    content: str
    timestamp: datetime
    importance: float = 5.0
    access_count: int = 0
    memory_type: str = "observation"
    metadata: Dict[str, Any] = field(default_factory=dict)


class CoreMemory:
    """
    核心记忆 - 类似 MemGPT 的 Core Memory
    存储 Agent 的自我认知和用户信息
    容量有限，但始终在上下文中
    """
    
    def __init__(self, max_length: int = 2000):
        self.max_length = max_length
        self.sections = {
            "persona": "我是一个学术研究助手，擅长文献调研、论文分析和研究规划。",
            "human": ""
        }
    
    def append(self, section: str, content: str) -> Dict[str, Any]:
        if section not in self.sections:
            return {"success": False, "error": f"Unknown section: {section}"}
        
        current = self.sections[section]
        new_content = f"{current}\n{content}" if current else content
        
        if len(new_content) > self.max_length:
            new_content = new_content[-self.max_length:]
        
        self.sections[section] = new_content
        return {"success": True, "section": section, "length": len(new_content)}
    
    def replace(self, section: str, old_content: str, new_content: str) -> Dict[str, Any]:
        if section not in self.sections:
            return {"success": False, "error": f"Unknown section: {section}"}
        
        current = self.sections[section]
        if old_content not in current:
            return {"success": False, "error": "Content to replace not found"}
        
        self.sections[section] = current.replace(old_content, new_content, 1)
        return {"success": True, "section": section}
    
    def get(self, section: str = None) -> str:
        if section:
            return self.sections.get(section, "")
        return f"[关于我]\n{self.sections['persona']}\n\n[关于用户]\n{self.sections['human']}"
    
    def to_prompt(self) -> str:
        return f"""<core_memory>
{self.get()}
</core_memory>"""


class WorkingMemory:
    """
    工作记忆 - 当前任务相关的临时信息
    容量小，速度快，类似 CPU 缓存
    """
    
    def __init__(self, max_items: int = 10):
        self.max_items = max_items
        self.items: Dict[str, MemoryItem] = {}
    
    def add(self, key: str, content: str, importance: float = 5.0) -> Dict[str, Any]:
        if len(self.items) >= self.max_items:
            self._evict_lowest_importance()
        
        self.items[key] = MemoryItem(
            content=content,
            timestamp=datetime.now(),
            importance=importance,
            memory_type="working"
        )
        return {"success": True, "key": key, "total_items": len(self.items)}
    
    def get(self, key: str) -> Optional[str]:
        if key in self.items:
            self.items[key].access_count += 1
            return self.items[key].content
        return None
    
    def get_all(self) -> List[MemoryItem]:
        return sorted(self.items.values(), key=lambda x: x.importance, reverse=True)
    
    def clear(self) -> Dict[str, Any]:
        count = len(self.items)
        self.items.clear()
        return {"success": True, "cleared_items": count}
    
    def _evict_lowest_importance(self):
        if not self.items:
            return
        lowest_key = min(self.items.keys(), key=lambda k: self.items[k].importance)
        del self.items[lowest_key]
    
    def to_prompt(self) -> str:
        if not self.items:
            return ""
        
        lines = ["<working_memory>", "当前任务相关信息："]
        for item in self.get_all()[:5]:
            lines.append(f"- {item.content[:200]}")
        lines.append("</working_memory>")
        return "\n".join(lines)


class RecallMemory:
    """
    回忆记忆 - 对话历史和近期交互
    类似 MemGPT 的 Recall Storage
    """
    
    def __init__(self, long_term_memory=None):
        self.long_term_memory = long_term_memory
        self.recent_messages: List[Dict[str, Any]] = []
        self.max_recent = 20
    
    def add_message(self, role: str, content: str, metadata: Dict = None):
        self.recent_messages.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        })
        
        if len(self.recent_messages) > self.max_recent:
            self.recent_messages = self.recent_messages[-self.max_recent:]
    
    def search(self, query: str, user_id: str = None, n_results: int = 5) -> Dict[str, Any]:
        results = []
        
        for msg in reversed(self.recent_messages):
            if query.lower() in msg["content"].lower():
                results.append({
                    "content": msg["content"][:500],
                    "role": msg["role"],
                    "timestamp": msg["timestamp"]
                })
                if len(results) >= n_results:
                    break
        
        if self.long_term_memory and self.long_term_memory.is_available():
            db_results = self.long_term_memory.recall_conversations(
                query=query,
                user_id=user_id,
                n_results=n_results
            )
            for r in db_results:
                results.append({
                    "content": r.get("document", "")[:500],
                    "metadata": r.get("metadata", {})
                })
        
        return {
            "success": True,
            "query": query,
            "results": results[:n_results],
            "total_found": len(results)
        }
    
    def to_prompt(self, last_n: int = 5) -> str:
        if not self.recent_messages:
            return ""
        
        lines = ["<recall_memory>", "最近对话："]
        for msg in self.recent_messages[-last_n:]:
            role = "用户" if msg["role"] == "user" else "助手"
            lines.append(f"{role}: {msg['content'][:200]}")
        lines.append("</recall_memory>")
        return "\n".join(lines)


class ArchivalMemory:
    """
    档案记忆 - 长期持久化存储
    类似 MemGPT 的 Archival Storage
    """
    
    def __init__(self, long_term_memory=None):
        self.long_term_memory = long_term_memory
    
    def insert(self, content: str, user_id: str = None, metadata: Dict = None) -> Dict[str, Any]:
        if not self.long_term_memory or not self.long_term_memory.is_available():
            return {"success": False, "error": "Long-term memory not available"}
        
        doc_id = f"archive_{uuid.uuid4().hex[:8]}"
        
        result = self.long_term_memory.save_task(
            user_id=user_id or "anonymous",
            task_id=doc_id,
            task=content[:500],
            result={"archived": True, "content": content},
            task_type="archival",
            evaluation_score=None
        )
        
        if result.get("success"):
            return {"success": True, "doc_id": doc_id, "message": "Content archived successfully"}
        return result
    
    def search(self, query: str, user_id: str = None, n_results: int = 5) -> Dict[str, Any]:
        if not self.long_term_memory or not self.long_term_memory.is_available():
            return {"success": False, "error": "Long-term memory not available", "results": []}
        
        task_results = self.long_term_memory.recall_similar_tasks(
            task=query,
            user_id=user_id,
            n_results=n_results
        )
        
        knowledge_results = self.long_term_memory.search_knowledge(
            query=query,
            user_id=user_id,
            n_results=n_results
        )
        
        results = []
        for r in task_results:
            results.append({
                "content": r.get("document", "")[:500],
                "source": "tasks",
                "metadata": r.get("metadata", {})
            })
        
        for r in knowledge_results:
            results.append({
                "content": r.get("document", "")[:500],
                "source": "knowledge",
                "metadata": r.get("metadata", {})
            })
        
        return {
            "success": True,
            "query": query,
            "results": results[:n_results],
            "total_found": len(results)
        }


class MemoryTools:
    """
    记忆系统调用工具集
    这些工具会被注册到 LLM 的 tools 中，让 LLM 自主调用
    """
    
    def __init__(self, long_term_memory=None, user_id: str = "anonymous"):
        self.user_id = user_id
        self.core_memory = CoreMemory()
        self.working_memory = WorkingMemory()
        self.recall_memory = RecallMemory(long_term_memory)
        self.archival_memory = ArchivalMemory(long_term_memory)
        self._long_term_memory = long_term_memory
    
    @staticmethod
    def get_tool_definitions() -> List[Dict[str, Any]]:
        """
        返回工具定义，用于注册到 LLM
        这是 LLM 可以调用的"系统调用"列表
        """
        return [
            {
                "type": "function",
                "function": {
                    "name": "core_memory_append",
                    "description": "向核心记忆追加内容。核心记忆始终在上下文中，用于存储关于自己或用户的重要信息。当用户告诉你关于他们的重要信息时，应该调用此函数。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "section": {
                                "type": "string",
                                "enum": ["persona", "human"],
                                "description": "要追加到的部分：persona(关于AI自己) 或 human(关于用户)"
                            },
                            "content": {
                                "type": "string",
                                "description": "要追加的内容"
                            }
                        },
                        "required": ["section", "content"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "core_memory_replace",
                    "description": "替换核心记忆中的内容。当需要更新或修正已有信息时使用。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "section": {
                                "type": "string",
                                "enum": ["persona", "human"],
                                "description": "要修改的部分"
                            },
                            "old_content": {
                                "type": "string",
                                "description": "要被替换的旧内容"
                            },
                            "new_content": {
                                "type": "string",
                                "description": "替换后的新内容"
                            }
                        },
                        "required": ["section", "old_content", "new_content"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "recall_memory_search",
                    "description": "搜索对话历史和近期交互。当你需要回忆之前的对话内容时调用此函数。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "搜索查询，描述你想回忆的内容"
                            },
                            "n_results": {
                                "type": "integer",
                                "description": "返回结果数量，默认5",
                                "default": 5
                            }
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "archival_memory_insert",
                    "description": "向档案存储写入内容。用于持久化重要信息，如用户偏好、重要事实、学到的知识等。这些信息会被长期保存。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "content": {
                                "type": "string",
                                "description": "要存档的内容"
                            }
                        },
                        "required": ["content"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "archival_memory_search",
                    "description": "搜索档案存储。当你需要检索长期记忆或之前存档的信息时调用此函数。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "搜索查询"
                            },
                            "n_results": {
                                "type": "integer",
                                "description": "返回结果数量，默认5",
                                "default": 5
                            }
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "working_memory_add",
                    "description": "向工作记忆添加信息。工作记忆用于存储当前任务相关的临时信息，容量有限但访问快速。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "key": {
                                "type": "string",
                                "description": "信息的键名"
                            },
                            "content": {
                                "type": "string",
                                "description": "信息内容"
                            },
                            "importance": {
                                "type": "number",
                                "description": "重要性评分(1-10)，默认5",
                                "default": 5.0
                            }
                        },
                        "required": ["key", "content"]
                    }
                }
            }
        ]
    
    def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行工具调用 - 这是"系统调用"的入口点
        """
        tool_map = {
            "core_memory_append": self._core_memory_append,
            "core_memory_replace": self._core_memory_replace,
            "recall_memory_search": self._recall_memory_search,
            "archival_memory_insert": self._archival_memory_insert,
            "archival_memory_search": self._archival_memory_search,
            "working_memory_add": self._working_memory_add,
        }
        
        if tool_name not in tool_map:
            return {"success": False, "error": f"Unknown tool: {tool_name}"}
        
        try:
            return tool_map[tool_name](**arguments)
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _core_memory_append(self, section: str, content: str) -> Dict[str, Any]:
        result = self.core_memory.append(section, content)
        if result["success"]:
            result["message"] = f"已将信息添加到{section}记忆"
        return result
    
    def _core_memory_replace(self, section: str, old_content: str, new_content: str) -> Dict[str, Any]:
        result = self.core_memory.replace(section, old_content, new_content)
        if result["success"]:
            result["message"] = "核心记忆已更新"
        return result
    
    def _recall_memory_search(self, query: str, n_results: int = 5) -> Dict[str, Any]:
        return self.recall_memory.search(query, self.user_id, n_results)
    
    def _archival_memory_insert(self, content: str) -> Dict[str, Any]:
        return self.archival_memory.insert(content, self.user_id)
    
    def _archival_memory_search(self, query: str, n_results: int = 5) -> Dict[str, Any]:
        return self.archival_memory.search(query, self.user_id, n_results)
    
    def _working_memory_add(self, key: str, content: str, importance: float = 5.0) -> Dict[str, Any]:
        return self.working_memory.add(key, content, importance)
    
    def add_message(self, role: str, content: str):
        self.recall_memory.add_message(role, content)
    
    def build_context_prompt(self) -> str:
        parts = []
        
        core = self.core_memory.to_prompt()
        if core:
            parts.append(core)
        
        working = self.working_memory.to_prompt()
        if working:
            parts.append(working)
        
        recall = self.recall_memory.to_prompt(last_n=3)
        if recall:
            parts.append(recall)
        
        return "\n\n".join(parts)
    
    def get_memory_statistics(self) -> Dict[str, Any]:
        return {
            "core_memory_sections": list(self.core_memory.sections.keys()),
            "working_memory_items": len(self.working_memory.items),
            "recent_messages": len(self.recall_memory.recent_messages),
            "user_id": self.user_id
        }
