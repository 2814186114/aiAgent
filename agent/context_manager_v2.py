"""
上下文管理改进模块

改进点：
1. 分层记忆架构（工作记忆、短期记忆、长期记忆）
2. Token 预算管理
3. 遗忘机制（重要性衰减）
4. 对话状态管理（指代消解）
5. 记忆压缩（摘要生成）
"""

import os
import sys
import json
import math
import time
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import deque
import re

_lib_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "python_libs")
if os.path.exists(_lib_path):
    sys.path.insert(0, _lib_path)

try:
    import chromadb
    from chromadb.utils import embedding_functions
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False


# ============================================================================
# 数据结构定义
# ============================================================================

class MemoryPriority(Enum):
    CRITICAL = 1.0
    HIGH = 0.8
    MEDIUM = 0.5
    LOW = 0.3
    BACKGROUND = 0.1


@dataclass
class MemoryItem:
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    importance: float = 0.5
    access_count: int = 0
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    token_count: int = 0
    
    def touch(self):
        self.access_count += 1
        self.last_accessed = time.time()
    
    def calculate_current_importance(self) -> float:
        days_since_access = (time.time() - self.last_accessed) / (24 * 60 * 60)
        time_decay = math.exp(-days_since_access / 30)
        access_boost = math.log(1 + self.access_count) / 10
        return self.importance * time_decay * (1 + access_boost)


@dataclass
class ConversationState:
    current_intent: Optional[str] = None
    filled_slots: Dict[str, Any] = field(default_factory=dict)
    last_topic: Optional[str] = None
    last_task: Optional[str] = None
    last_result: Optional[Dict[str, Any]] = None
    pending_questions: List[str] = field(default_factory=list)
    conversation_history: List[Dict[str, str]] = field(default_factory=list)
    
    def add_message(self, role: str, content: str):
        self.conversation_history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        if len(self.conversation_history) > 50:
            self.conversation_history = self.conversation_history[-50:]


# ============================================================================
# 1. 分层记忆架构
# ============================================================================

class WorkingMemory:
    """
    工作记忆：存储当前任务相关的临时信息
    - 容量小，速度快
    - 任务完成后清空或转移到短期记忆
    """
    
    def __init__(self, max_items: int = 10):
        self.max_items = max_items
        self.items: Dict[str, MemoryItem] = {}
    
    def add(self, key: str, content: str, metadata: Dict = None, importance: float = 0.8):
        if len(self.items) >= self.max_items:
            self._evict_lowest_importance()
        
        self.items[key] = MemoryItem(
            content=content,
            metadata=metadata or {},
            importance=importance
        )
    
    def get(self, key: str) -> Optional[MemoryItem]:
        if key in self.items:
            self.items[key].touch()
            return self.items[key]
        return None
    
    def get_all(self) -> List[MemoryItem]:
        return list(self.items.values())
    
    def clear(self):
        self.items.clear()
    
    def _evict_lowest_importance(self):
        if not self.items:
            return
        lowest_key = min(self.items.keys(), key=lambda k: self.items[k].calculate_current_importance())
        del self.items[lowest_key]


class ShortTermMemory:
    """
    短期记忆：存储最近几轮对话
    - 使用滑动窗口，保留最近 N 条
    - 自动过期（默认 1 小时）
    """
    
    def __init__(self, max_items: int = 20, ttl_seconds: int = 3600):
        self.max_items = max_items
        self.ttl_seconds = ttl_seconds
        self.items: deque = deque(maxlen=max_items)
    
    def add(self, content: str, metadata: Dict = None, importance: float = 0.5):
        self.items.append(MemoryItem(
            content=content,
            metadata=metadata or {},
            importance=importance
        ))
    
    def get_recent(self, n: int = 5) -> List[MemoryItem]:
        self._cleanup_expired()
        return list(self.items)[-n:]
    
    def search(self, query: str, top_k: int = 3) -> List[MemoryItem]:
        self._cleanup_expired()
        results = []
        query_lower = query.lower()
        for item in self.items:
            if query_lower in item.content.lower():
                results.append(item)
            if len(results) >= top_k:
                break
        return results
    
    def _cleanup_expired(self):
        current_time = time.time()
        while self.items and (current_time - self.items[0].created_at) > self.ttl_seconds:
            self.items.popleft()


class LongTermMemoryV2:
    """
    长期记忆：持久化存储，使用 ChromaDB
    - 支持向量检索
    - 支持遗忘机制
    """
    
    def __init__(self):
        self.client = None
        self.collections: Dict[str, Any] = {}
        self.embedding_function = None
        
        if CHROMA_AVAILABLE:
            self._init_chroma()
    
    def _init_chroma(self):
        try:
            chroma_path = self._get_chroma_path()
            self.client = chromadb.PersistentClient(path=chroma_path)
            
            try:
                self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
                    model_name="BAAI/bge-small-zh-v1.5"
                )
            except:
                self.embedding_function = None
            
            for name in ["conversations", "tasks", "knowledge"]:
                self.collections[name] = self.client.get_or_create_collection(
                    name=name,
                    embedding_function=self.embedding_function
                )
        except Exception as e:
            print(f"[LongTermMemoryV2] Init error: {e}")
    
    def _get_chroma_path(self) -> str:
        if sys.platform == "win32":
            base = os.environ.get("APPDATA", os.path.join(os.path.expanduser("~"), "AppData", "Roaming"))
            path = os.path.join(base, "AcademicAssistant", "chroma_v2")
        else:
            path = os.path.join(os.path.expanduser("~"), ".academicassistant", "chroma_v2")
        os.makedirs(path, exist_ok=True)
        return path
    
    def is_available(self) -> bool:
        return self.client is not None
    
    def save(self, collection_name: str, doc_id: str, content: str, metadata: Dict):
        if not self.is_available():
            return False
        
        collection = self.collections.get(collection_name)
        if not collection:
            return False
        
        metadata["created_at"] = time.time()
        metadata["access_count"] = 0
        metadata["importance"] = metadata.get("importance", 0.5)
        
        collection.upsert(
            documents=[content],
            metadatas=[metadata],
            ids=[doc_id]
        )
        return True
    
    def search(self, collection_name: str, query: str, n_results: int = 5, where: Dict = None) -> List[Dict]:
        if not self.is_available():
            return []
        
        collection = self.collections.get(collection_name)
        if not collection:
            return []
        
        results = collection.query(
            query_texts=[query],
            n_results=n_results,
            where=where
        )
        
        return self._format_results(results)
    
    def _format_results(self, results: Dict) -> List[Dict]:
        formatted = []
        if not results or not results.get('documents'):
            return formatted
        
        for i, doc in enumerate(results['documents'][0]):
            formatted.append({
                "content": doc,
                "metadata": results['metadatas'][0][i] if results.get('metadatas') else {},
                "distance": results['distances'][0][i] if results.get('distances') else None
            })
        return formatted


# ============================================================================
# 2. Token 预算管理
# ============================================================================

class TokenBudgetManager:
    """
    Token 预算管理器
    - 分配 Token 预算给不同类型的记忆
    - 按优先级压缩/截断
    """
    
    def __init__(self, max_tokens: int = 4000):
        self.max_tokens = max_tokens
        self.budget_allocation = {
            "system_prompt": 0.15,      # 15% 给系统提示
            "working_memory": 0.20,     # 20% 给工作记忆
            "short_term_memory": 0.25,  # 25% 给短期记忆
            "long_term_memory": 0.30,   # 30% 给长期记忆
            "user_input": 0.10          # 10% 给用户输入
        }
    
    def estimate_tokens(self, text: str) -> int:
        return len(text) // 4 + 1
    
    def build_context(
        self,
        system_prompt: str,
        working_items: List[MemoryItem],
        short_term_items: List[MemoryItem],
        long_term_items: List[Dict],
        user_input: str
    ) -> str:
        budget = self.max_tokens
        context_parts = []
        
        system_budget = int(budget * self.budget_allocation["system_prompt"])
        system_text = self._truncate(system_prompt, system_budget)
        context_parts.append(f"[系统]\n{system_text}")
        budget -= self.estimate_tokens(system_text)
        
        working_budget = int(budget * self.budget_allocation["working_memory"] / sum(self.budget_allocation.values()))
        working_text = self._compress_items(working_items, working_budget)
        if working_text:
            context_parts.append(f"\n[当前任务上下文]\n{working_text}")
        
        short_budget = int(budget * self.budget_allocation["short_term_memory"] / sum(self.budget_allocation.values()))
        short_text = self._compress_items(short_term_items, short_budget)
        if short_text:
            context_parts.append(f"\n[最近对话]\n{short_text}")
        
        long_budget = int(budget * self.budget_allocation["long_term_memory"] / sum(self.budget_allocation.values()))
        long_text = self._compress_long_term(long_term_items, long_budget)
        if long_text:
            context_parts.append(f"\n[相关历史]\n{long_text}")
        
        context_parts.append(f"\n[用户输入]\n{user_input}")
        
        return "\n".join(context_parts)
    
    def _truncate(self, text: str, max_tokens: int) -> str:
        estimated = self.estimate_tokens(text)
        if estimated <= max_tokens:
            return text
        
        ratio = max_tokens / estimated
        target_length = int(len(text) * ratio * 0.9)
        return text[:target_length] + "..."
    
    def _compress_items(self, items: List[MemoryItem], budget: int) -> str:
        if not items:
            return ""
        
        sorted_items = sorted(items, key=lambda x: x.calculate_current_importance(), reverse=True)
        
        parts = []
        current_tokens = 0
        
        for item in sorted_items:
            item_tokens = self.estimate_tokens(item.content)
            if current_tokens + item_tokens > budget:
                remaining = budget - current_tokens
                if remaining > 50:
                    compressed = self._truncate(item.content, remaining)
                    parts.append(compressed)
                break
            
            parts.append(item.content)
            current_tokens += item_tokens
        
        return "\n".join(parts)
    
    def _compress_long_term(self, items: List[Dict], budget: int) -> str:
        if not items:
            return ""
        
        parts = []
        current_tokens = 0
        
        for item in items:
            content = item.get("content", "")
            item_tokens = self.estimate_tokens(content)
            
            if current_tokens + item_tokens > budget:
                remaining = budget - current_tokens
                if remaining > 50:
                    compressed = self._truncate(content, remaining)
                    parts.append(compressed)
                break
            
            parts.append(content)
            current_tokens += item_tokens
        
        return "\n".join(parts)


# ============================================================================
# 3. 遗忘机制
# ============================================================================

class MemoryForgettingManager:
    """
    记忆遗忘管理器
    - 基于时间衰减和访问频率
    - 定期清理低重要性记忆
    """
    
    def __init__(
        self,
        decay_rate: float = 0.03,
        min_importance: float = 0.1,
        cleanup_interval: int = 86400
    ):
        self.decay_rate = decay_rate
        self.min_importance = min_importance
        self.cleanup_interval = cleanup_interval
        self.last_cleanup = time.time()
    
    def update_importance(self, item: MemoryItem) -> float:
        days_since_access = (time.time() - item.last_accessed) / (24 * 60 * 60)
        time_decay = math.exp(-self.decay_rate * days_since_access)
        access_boost = math.log(1 + item.access_count) / 10
        current_importance = item.importance * time_decay * (1 + access_boost)
        return current_importance
    
    def should_forget(self, item: MemoryItem) -> bool:
        return self.update_importance(item) < self.min_importance
    
    def cleanup_memory(self, items: Dict[str, MemoryItem]) -> List[str]:
        forgotten_keys = []
        
        for key, item in list(items.items()):
            if self.should_forget(item):
                forgotten_keys.append(key)
                del items[key]
        
        self.last_cleanup = time.time()
        return forgotten_keys
    
    def consolidate_memory(
        self,
        short_term: ShortTermMemory,
        long_term: LongTermMemoryV2,
        importance_threshold: float = 0.6
    ):
        """将重要的短期记忆转移到长期记忆"""
        for item in short_term.items:
            if item.calculate_current_importance() >= importance_threshold:
                long_term.save(
                    collection_name="conversations",
                    doc_id=f"consolidated_{int(time.time() * 1000)}",
                    content=item.content,
                    metadata=item.metadata
                )


# ============================================================================
# 4. 对话状态管理
# ============================================================================

class ConversationStateManager:
    """
    对话状态管理器
    - 意图跟踪
    - 槽位填充
    - 指代消解
    """
    
    CONTINUATION_KEYWORDS = ["继续", "接着", "然后", "还有", "另外"]
    REFERENCE_KEYWORDS = ["那个", "这个", "刚才", "之前", "上面"]
    
    def __init__(self):
        self.states: Dict[str, ConversationState] = {}
    
    def get_state(self, conversation_id: str) -> ConversationState:
        if conversation_id not in self.states:
            self.states[conversation_id] = ConversationState()
        return self.states[conversation_id]
    
    def process_message(
        self,
        conversation_id: str,
        user_message: str,
        assistant_response: str = None
    ) -> Dict[str, Any]:
        state = self.get_state(conversation_id)
        
        result = {
            "is_continuation": False,
            "is_reference": False,
            "resolved_content": user_message,
            "intent": None,
            "slots": {}
        }
        
        if self._is_continuation(user_message):
            result["is_continuation"] = True
            result["resolved_content"] = self._resolve_continuation(state, user_message)
        
        if self._has_reference(user_message):
            result["is_reference"] = True
            result["resolved_content"] = self._resolve_reference(state, user_message)
        
        intent = self._extract_intent(user_message)
        if intent:
            result["intent"] = intent
            state.current_intent = intent
        
        slots = self._extract_slots(user_message)
        if slots:
            result["slots"] = slots
            state.filled_slots.update(slots)
        
        state.add_message("user", user_message)
        if assistant_response:
            state.add_message("assistant", assistant_response)
        
        return result
    
    def _is_continuation(self, message: str) -> bool:
        return any(kw in message for kw in self.CONTINUATION_KEYWORDS)
    
    def _has_reference(self, message: str) -> bool:
        return any(kw in message for kw in self.REFERENCE_KEYWORDS)
    
    def _resolve_continuation(self, state: ConversationState, message: str) -> str:
        if state.last_task:
            return f"[继续之前的任务] {state.last_task}\n用户补充: {message}"
        return message
    
    def _resolve_reference(self, state: ConversationState, message: str) -> str:
        resolved = message
        
        if state.last_topic:
            resolved = resolved.replace("那个", f"[{state.last_topic}]")
            resolved = resolved.replace("这个", f"[{state.last_topic}]")
        
        if state.last_result:
            if "结果" in message or "答案" in message:
                resolved += f"\n[引用上次结果: {state.last_result.get('summary', '无')}]"
        
        return resolved
    
    def _extract_intent(self, message: str) -> Optional[str]:
        intent_patterns = {
            "search": ["搜索", "查找", "找", "检索"],
            "analyze": ["分析", "研究", "调研"],
            "summarize": ["总结", "摘要", "概括"],
            "schedule": ["安排", "计划", "日程", "提醒"],
            "question": ["什么是", "为什么", "如何", "怎么"]
        }
        
        message_lower = message.lower()
        for intent, keywords in intent_patterns.items():
            if any(kw in message_lower for kw in keywords):
                return intent
        
        return None
    
    def _extract_slots(self, message: str) -> Dict[str, Any]:
        slots = {}
        
        year_pattern = r'(\d{4})年?'
        years = re.findall(year_pattern, message)
        if years:
            slots["years"] = [int(y) for y in years]
        
        number_pattern = r'(\d+)\s*(篇|个|条)'
        numbers = re.findall(number_pattern, message)
        if numbers:
            slots["count"] = int(numbers[0][0])
        
        return slots
    
    def update_task_context(
        self,
        conversation_id: str,
        task: str,
        result: Dict[str, Any]
    ):
        state = self.get_state(conversation_id)
        state.last_task = task
        state.last_result = result
        state.last_topic = self._extract_topic(task)
    
    def _extract_topic(self, text: str) -> Optional[str]:
        keywords = re.findall(r'[\u4e00-\u9fa5]{2,}', text)
        if keywords:
            return max(keywords, key=len)
        return None


# ============================================================================
# 5. 记忆压缩
# ============================================================================

class MemoryCompressor:
    """
    记忆压缩器
    - 将多轮对话压缩为摘要
    - 分层压缩（细节 → 关键点 → 摘要）
    """
    
    def __init__(self, llm_client=None, model: str = "deepseek-chat"):
        self.llm_client = llm_client
        self.model = model
    
    def compress_conversation(
        self,
        messages: List[Dict[str, str]],
        max_length: int = 500
    ) -> str:
        if not messages:
            return ""
        
        if len(messages) <= 3:
            return self._format_messages(messages)
        
        key_points = self._extract_key_points(messages)
        
        if self.llm_client:
            summary = self._llm_summarize(key_points, max_length)
            if summary:
                return summary
        
        return self._rule_based_compress(messages, max_length)
    
    def _extract_key_points(self, messages: List[Dict]) -> List[str]:
        key_points = []
        
        for msg in messages:
            content = msg.get("content", "")
            role = msg.get("role", "")
            
            if role == "user":
                questions = re.findall(r'[^。？!！]+[？?]', content)
                key_points.extend(questions)
            
            if role == "assistant":
                sentences = re.split(r'[。！？\n]', content)
                important = [s for s in sentences if len(s) > 20 and any(
                    kw in s for kw in ["结论", "结果", "发现", "建议", "总结"]
                )]
                key_points.extend(important[:2])
        
        return key_points[:10]
    
    def _llm_summarize(self, key_points: List[str], max_length: int) -> Optional[str]:
        if not self.llm_client or not key_points:
            return None
        
        prompt = f"""请将以下对话要点压缩为简洁的摘要（不超过{max_length}字）：

要点：
{chr(10).join(f'- {p}' for p in key_points)}

摘要："""
        
        try:
            response = self.llm_client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_length,
                temperature=0.3
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"[MemoryCompressor] LLM summarize error: {e}")
            return None
    
    def _rule_based_compress(self, messages: List[Dict], max_length: int) -> str:
        total_len = sum(len(m.get("content", "")) for m in messages)
        
        if total_len <= max_length:
            return self._format_messages(messages)
        
        ratio = max_length / total_len
        compressed_parts = []
        
        for msg in messages:
            content = msg.get("content", "")
            target_len = int(len(content) * ratio)
            if target_len < len(content):
                compressed_parts.append(f"{msg['role']}: {content[:target_len]}...")
            else:
                compressed_parts.append(f"{msg['role']}: {content}")
        
        return "\n".join(compressed_parts)
    
    def _format_messages(self, messages: List[Dict]) -> str:
        return "\n".join(
            f"{m.get('role', 'unknown')}: {m.get('content', '')}"
            for m in messages
        )
    
    def hierarchical_compress(
        self,
        memories: List[MemoryItem],
        levels: int = 3
    ) -> Dict[str, Any]:
        if not memories:
            return {"summary": "", "levels": []}
        
        sorted_memories = sorted(memories, key=lambda x: x.created_at)
        
        chunk_size = max(1, len(sorted_memories) // levels)
        chunks = [
            sorted_memories[i:i + chunk_size]
            for i in range(0, len(sorted_memories), chunk_size)
        ]
        
        level_summaries = []
        for chunk in chunks:
            chunk_content = "\n".join(m.content for m in chunk)
            summary = self.compress_conversation(
                [{"role": "memory", "content": chunk_content}],
                max_length=200
            )
            level_summaries.append(summary)
        
        final_summary = self.compress_conversation(
            [{"role": "summary", "content": s} for s in level_summaries],
            max_length=300
        )
        
        return {
            "summary": final_summary,
            "levels": level_summaries,
            "original_count": len(memories)
        }


# ============================================================================
# 统一上下文管理器
# ============================================================================

class ContextManagerV2:
    """
    改进版上下文管理器
    整合所有改进点
    """
    
    def __init__(
        self,
        max_tokens: int = 4000,
        llm_client=None,
        model: str = "deepseek-chat"
    ):
        self.working_memory = WorkingMemory()
        self.short_term_memory = ShortTermMemory()
        self.long_term_memory = LongTermMemoryV2()
        
        self.token_manager = TokenBudgetManager(max_tokens)
        self.forgetting_manager = MemoryForgettingManager()
        self.conversation_manager = ConversationStateManager()
        self.compressor = MemoryCompressor(llm_client, model)
        
        self.llm_client = llm_client
        self.model = model
    
    async def build_context(
        self,
        conversation_id: str,
        user_message: str,
        system_prompt: str = ""
    ) -> Tuple[str, Dict[str, Any]]:
        state_result = self.conversation_manager.process_message(
            conversation_id, user_message
        )
        
        resolved_message = state_result["resolved_content"]
        
        working_items = self.working_memory.get_all()
        
        short_term_items = self.short_term_memory.get_recent(5)
        
        long_term_items = []
        if self.long_term_memory.is_available():
            long_term_items = self.long_term_memory.search(
                "conversations",
                resolved_message,
                n_results=3
            )
        
        context = self.token_manager.build_context(
            system_prompt=system_prompt,
            working_items=working_items,
            short_term_items=short_term_items,
            long_term_items=long_term_items,
            user_input=resolved_message
        )
        
        return context, state_result
    
    def update_after_response(
        self,
        conversation_id: str,
        user_message: str,
        assistant_response: str,
        task: str = None,
        result: Dict = None
    ):
        state = self.conversation_manager.get_state(conversation_id)
        state.add_message("user", user_message)
        state.add_message("assistant", assistant_response)
        
        self.short_term_memory.add(
            content=f"用户: {user_message}\n助手: {assistant_response}",
            metadata={"conversation_id": conversation_id}
        )
        
        if task and result:
            self.conversation_manager.update_task_context(
                conversation_id, task, result
            )
            
            self.working_memory.add(
                key=f"task_{int(time.time())}",
                content=f"任务: {task}\n结果摘要: {str(result)[:500]}",
                metadata={"conversation_id": conversation_id},
                importance=0.7
            )
    
    def run_maintenance(self):
        self.forgetting_manager.cleanup_memory(self.working_memory.items)
        
        self.forgetting_manager.consolidate_memory(
            self.short_term_memory,
            self.long_term_memory
        )
    
    def clear_working_memory(self):
        self.working_memory.clear()


# ============================================================================
# 单例获取函数
# ============================================================================

_context_manager: Optional[ContextManagerV2] = None


def get_context_manager(
    max_tokens: int = 4000,
    llm_client=None,
    model: str = "deepseek-chat"
) -> ContextManagerV2:
    global _context_manager
    if _context_manager is None:
        _context_manager = ContextManagerV2(max_tokens, llm_client, model)
    return _context_manager
