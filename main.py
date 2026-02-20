import os
import sys

_lib_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "python_libs")
if os.path.exists(_lib_path):
    sys.path.insert(0, _lib_path)

try:
    from dotenv import load_dotenv
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    load_dotenv(env_path)
except ImportError:
    pass

import asyncio
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from agent import ReActAgent
from agent.planning_agent import PlanningAgent
from agent.unified_agent import UnifiedAgent
from agent.reflection import ReflectionAgent
from agent.ppt_generator import generate_ppt
from agent.memory import get_memory_manager
from agent.tasks import save_task, get_task, list_tasks, delete_task
from agent.experiments import add_experiment, query_experiments, get_experiment, update_experiment, delete_experiment, list_all_experiments
from agent.literature import (
    add_paper, remove_paper, is_paper_saved, list_saved_papers,
    add_tag, remove_tag, list_tags, add_tag_to_paper, remove_tag_from_paper,
    add_note, update_note, delete_note,
    add_folder, delete_folder, list_folders, add_paper_to_folder, remove_paper_from_folder,
    mark_paper_read
)
from agent.auth import (
    create_user, authenticate_user, get_user,
    create_conversation, save_message, get_conversation, 
    list_conversations, delete_conversation, search_conversations
)

app = FastAPI(title="Academic Assistant Agent - Python Service")

ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:3000,http://localhost:3001")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

agent = ReActAgent()
planning_agent = PlanningAgent()
unified_agent = UnifiedAgent()
reflection_agent = ReflectionAgent(unified_agent)

REFLECTION_ENABLED = True

active_websockets: List[WebSocket] = []

class MessageRequest(BaseModel):
    message: str
    sessionId: Optional[str] = None
    timestamp: Optional[str] = None

class PPTRequest(BaseModel):
    user_request: str

class RecallRequest(BaseModel):
    query: str
    top_k: int = 3

class PreferenceUpdateRequest(BaseModel):
    key: str
    value: str

class PreferenceGetRequest(BaseModel):
    key: str
    default: Optional[str] = None

class SaveTaskRequest(BaseModel):
    task_id: str
    task: str
    answer: Optional[str] = None
    steps: List[Dict[str, Any]] = []
    task_type: Optional[str] = None
    plan: Optional[List[Dict[str, Any]]] = None

class StepResponse(BaseModel):
    type: str
    content: Optional[str] = None
    tool: Optional[str] = None
    arguments: Optional[Dict[str, Any]] = None
    iteration: int

class AddExperimentRequest(BaseModel):
    note: str

class QueryExperimentsRequest(BaseModel):
    query: Optional[str] = ""
    limit: Optional[int] = 10

class UpdateExperimentRequest(BaseModel):
    model: Optional[str] = None
    dataset: Optional[str] = None
    metric: Optional[str] = None
    value: Optional[float] = None
    notes: Optional[str] = None

class AddPaperRequest(BaseModel):
    paper_id: str
    title: str
    authors: Optional[List[str]] = None
    year: Optional[int] = None
    abstract: Optional[str] = None
    url: Optional[str] = None
    pdf_url: Optional[str] = None

class TagRequest(BaseModel):
    name: str

class PaperTagRequest(BaseModel):
    paper_id: str
    tag_name: str

class NoteRequest(BaseModel):
    paper_id: str
    content: str

class UpdateNoteRequest(BaseModel):
    content: str

class FolderRequest(BaseModel):
    name: str
    description: Optional[str] = None

class FolderPaperRequest(BaseModel):
    paper_id: str
    folder_id: int

class RegisterRequest(BaseModel):
    username: str
    password: str
    email: Optional[str] = None

class LoginRequest(BaseModel):
    username: str
    password: str

class SaveMessageRequest(BaseModel):
    conversation_id: str
    role: str
    content: str
    metadata: Optional[Dict[str, Any]] = None

class CreateConversationRequest(BaseModel):
    title: Optional[str] = None
    user_id: Optional[int] = None

class SearchConversationsRequest(BaseModel):
    query: str
    user_id: Optional[int] = None
    limit: Optional[int] = 20

@app.get("/ping")
async def ping():
    return {"message": "pong"}

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "python-fastapi",
        "timestamp": datetime.now().isoformat(),
        "llm_configured": agent.client is not None
    }

@app.post("/auth/register")
async def register(request: RegisterRequest):
    result = create_user(request.username, request.password, request.email)
    if result.get("success"):
        return JSONResponse(content={
            "success": True,
            "user": result
        })
    else:
        return JSONResponse(content={
            "success": False,
            "error": result.get("error")
        }, status_code=400)

@app.post("/auth/login")
async def login(request: LoginRequest):
    result = authenticate_user(request.username, request.password)
    if result.get("success"):
        return JSONResponse(content={
            "success": True,
            "user": result["user"]
        })
    else:
        return JSONResponse(content={
            "success": False,
            "error": result.get("error")
        }, status_code=401)

@app.get("/auth/user/{user_id}")
async def get_user_info(user_id: int):
    user = get_user(user_id)
    if user:
        return JSONResponse(content={
            "success": True,
            "user": user
        })
    else:
        return JSONResponse(content={
            "success": False,
            "error": "User not found"
        }, status_code=404)

@app.post("/conversations")
async def create_new_conversation(request: CreateConversationRequest):
    result = create_conversation(request.user_id, request.title)
    if result.get("success"):
        return JSONResponse(content={
            "success": True,
            "conversation": result["conversation"]
        })
    else:
        return JSONResponse(content={
            "success": False,
            "error": result.get("error")
        }, status_code=400)

@app.get("/conversations")
async def get_conversations(user_id: Optional[int] = None, limit: int = 50):
    conversations = list_conversations(user_id, limit)
    return JSONResponse(content={
        "success": True,
        "conversations": conversations
    })

@app.get("/conversations/{conversation_id}")
async def get_conversation_detail(conversation_id: str):
    conversation = get_conversation(conversation_id)
    if conversation:
        return JSONResponse(content={
            "success": True,
            "conversation": conversation
        })
    else:
        return JSONResponse(content={
            "success": False,
            "error": "Conversation not found"
        }, status_code=404)

@app.post("/messages")
async def save_message_to_conversation(request: SaveMessageRequest):
    result = save_message(request.conversation_id, request.role, request.content, request.metadata)
    if result.get("success"):
        return JSONResponse(content={
            "success": True,
            "message": result["message"]
        })
    else:
        return JSONResponse(content={
            "success": False,
            "error": result.get("error")
        }, status_code=400)

@app.delete("/conversations/{conversation_id}")
async def delete_conversation_by_id(conversation_id: str):
    result = delete_conversation(conversation_id)
    if result.get("success"):
        return JSONResponse(content={
            "success": True
        })
    else:
        return JSONResponse(content={
            "success": False,
            "error": result.get("error")
        }, status_code=400)

@app.post("/conversations/search")
async def search_conversations_endpoint(request: SearchConversationsRequest):
    conversations = search_conversations(request.query, request.user_id, request.limit)
    return JSONResponse(content={
        "success": True,
        "conversations": conversations
    })

@app.post("/process")
async def process_message(request: MessageRequest):
    steps_collector = []
    
    async def collect_step(step: Dict[str, Any]):
        steps_collector.append(step)
    
    result = await agent.run(request.message, callback=collect_step)
    
    return {
        "task": result["task"],
        "steps": result["steps"],
        "answer": result["answer"],
        "iterations": result["iterations"],
        "session_id": request.sessionId
    }

@app.post("/process-plan")
async def process_plan_message(request: MessageRequest):
    steps_collector = []
    
    async def collect_step(step: Dict[str, Any]):
        steps_collector.append(step)
    
    result = await planning_agent.execute_task(request.message, callback=collect_step)
    
    return {
        "task": result["task"],
        "steps": steps_collector,
        "answer": result.get("final_answer", "完成"),
        "plan": result.get("plan", []),
        "iterations": len(result.get("plan", [])),
        "session_id": request.sessionId
    }

@app.post("/generate-ppt")
async def generate_ppt_endpoint(request: PPTRequest):
    result = await generate_ppt(request.user_request)
    if result.get("success"):
        return JSONResponse(content={
            "success": True,
            "outline": result["outline"]
        })
    else:
        return JSONResponse(content={
            "success": False,
            "error": result.get("error")
        }, status_code=400)

@app.post("/recall")
async def recall_endpoint(request: RecallRequest):
    memory_manager = get_memory_manager()
    result = memory_manager.recall_task_history(request.query, top_k=request.top_k)
    if result.get("success"):
        return JSONResponse(content={
            "success": True,
            "results": result.get("results", [])
        })
    else:
        return JSONResponse(content={
            "success": False,
            "error": result.get("error"),
            "results": []
        }, status_code=400 if result.get("error") else 200)

@app.get("/preferences")
async def list_preferences_endpoint():
    memory_manager = get_memory_manager()
    result = memory_manager.list_all_preferences()
    if result.get("success"):
        return JSONResponse(content={
            "success": True,
            "preferences": result.get("preferences", {})
        })
    else:
        return JSONResponse(content={
            "success": False,
            "error": result.get("error"),
            "preferences": {}
        }, status_code=400 if result.get("error") else 200)

@app.post("/preferences")
async def update_preference_endpoint(request: PreferenceUpdateRequest):
    memory_manager = get_memory_manager()
    result = memory_manager.update_preference(request.key, request.value)
    if result.get("success"):
        return JSONResponse(content={
            "success": True,
            "key": result.get("key"),
            "value": result.get("value")
        })
    else:
        return JSONResponse(content={
            "success": False,
            "error": result.get("error")
        }, status_code=400)

@app.get("/preferences/{key}")
async def get_preference_endpoint(key: str, default: Optional[str] = None):
    memory_manager = get_memory_manager()
    result = memory_manager.get_preference(key, default)
    if result.get("success"):
        return JSONResponse(content={
            "success": True,
            "key": result.get("key"),
            "value": result.get("value")
        })
    else:
        return JSONResponse(content={
            "success": False,
            "error": result.get("error"),
            "value": default
        }, status_code=400 if result.get("error") else 200)

@app.get("/tasks")
async def list_tasks_endpoint(limit: int = 50):
    tasks = list_tasks(limit)
    return JSONResponse(content={
        "success": True,
        "tasks": tasks
    })

@app.get("/tasks/{task_id}")
async def get_task_endpoint(task_id: str):
    task = get_task(task_id)
    if task:
        return JSONResponse(content={
            "success": True,
            "task": task
        })
    else:
        return JSONResponse(content={
            "success": False,
            "error": "Task not found"
        }, status_code=404)

@app.post("/tasks")
async def save_task_endpoint(request: SaveTaskRequest):
    print(f"[save_task_endpoint] Received request: {request}")
    result = save_task(
        request.task_id, 
        request.task, 
        request.answer, 
        request.steps,
        request.task_type,
        request.plan
    )
    print(f"[save_task_endpoint] Result: {result}")
    if result.get("success"):
        return JSONResponse(content={
            "success": True,
            "task_id": result.get("task_id")
        })
    else:
        return JSONResponse(content={
            "success": False,
            "error": result.get("error")
        }, status_code=400)

@app.delete("/tasks/{task_id}")
async def delete_task_endpoint(task_id: str):
    result = delete_task(task_id)
    if result.get("success"):
        return JSONResponse(content={
            "success": True
        })
    else:
        return JSONResponse(content={
            "success": False,
            "error": result.get("error")
        }, status_code=400)

@app.post("/experiments")
async def add_experiment_endpoint(request: AddExperimentRequest):
    result = await add_experiment(request.note)
    if result.get("success"):
        return JSONResponse(content=result)
    else:
        return JSONResponse(content=result, status_code=400)

@app.get("/experiments")
async def list_experiments_endpoint(
    model: Optional[str] = None,
    dataset: Optional[str] = None,
    metric: Optional[str] = None,
    limit: int = 100
):
    result = await list_all_experiments(model, dataset, metric, limit)
    return JSONResponse(content=result)

@app.post("/experiments/query")
async def query_experiments_endpoint(request: QueryExperimentsRequest):
    result = await query_experiments(request.query, request.limit)
    return JSONResponse(content=result)

@app.get("/experiments/{exp_id}")
async def get_experiment_endpoint(exp_id: int):
    result = await get_experiment(exp_id)
    if result.get("success"):
        return JSONResponse(content=result)
    else:
        return JSONResponse(content=result, status_code=404)

@app.put("/experiments/{exp_id}")
async def update_experiment_endpoint(exp_id: int, request: UpdateExperimentRequest):
    result = await update_experiment(
        exp_id,
        request.model,
        request.dataset,
        request.metric,
        request.value,
        request.notes
    )
    if result.get("success"):
        return JSONResponse(content=result)
    else:
        return JSONResponse(content=result, status_code=400)

@app.delete("/experiments/{exp_id}")
async def delete_experiment_endpoint(exp_id: int):
    result = await delete_experiment(exp_id)
    if result.get("success"):
        return JSONResponse(content=result)
    else:
        return JSONResponse(content=result, status_code=400)

@app.post("/literature/papers")
async def add_paper_endpoint(request: AddPaperRequest):
    result = add_paper(
        request.paper_id,
        request.title,
        request.authors,
        request.year,
        request.abstract,
        request.url,
        request.pdf_url
    )
    if result.get("success"):
        return JSONResponse(content=result)
    else:
        return JSONResponse(content=result, status_code=400)

@app.delete("/literature/papers/{paper_id}")
async def remove_paper_endpoint(paper_id: str):
    result = remove_paper(paper_id)
    if result.get("success"):
        return JSONResponse(content=result)
    else:
        return JSONResponse(content=result, status_code=400)

@app.get("/literature/papers/{paper_id}/saved")
async def is_paper_saved_endpoint(paper_id: str):
    result = is_paper_saved(paper_id)
    return JSONResponse(content=result)

@app.get("/literature/papers")
async def list_saved_papers_endpoint(
    tag: Optional[str] = None,
    folder: Optional[int] = None,
    limit: int = 100
):
    result = list_saved_papers(tag, folder, limit)
    return JSONResponse(content=result)

@app.post("/literature/papers/{paper_id}/read")
async def mark_paper_read_endpoint(paper_id: str):
    result = mark_paper_read(paper_id)
    if result.get("success"):
        return JSONResponse(content=result)
    else:
        return JSONResponse(content=result, status_code=400)

@app.post("/literature/tags")
async def add_tag_endpoint(request: TagRequest):
    result = add_tag(request.name)
    if result.get("success"):
        return JSONResponse(content=result)
    else:
        return JSONResponse(content=result, status_code=400)

@app.delete("/literature/tags/{name}")
async def remove_tag_endpoint(name: str):
    result = remove_tag(name)
    if result.get("success"):
        return JSONResponse(content=result)
    else:
        return JSONResponse(content=result, status_code=400)

@app.get("/literature/tags")
async def list_tags_endpoint():
    result = list_tags()
    return JSONResponse(content=result)

@app.post("/literature/papers/tags")
async def add_tag_to_paper_endpoint(request: PaperTagRequest):
    result = add_tag_to_paper(request.paper_id, request.tag_name)
    if result.get("success"):
        return JSONResponse(content=result)
    else:
        return JSONResponse(content=result, status_code=400)

@app.delete("/literature/papers/{paper_id}/tags/{tag_name}")
async def remove_tag_from_paper_endpoint(paper_id: str, tag_name: str):
    result = remove_tag_from_paper(paper_id, tag_name)
    if result.get("success"):
        return JSONResponse(content=result)
    else:
        return JSONResponse(content=result, status_code=400)

@app.post("/literature/notes")
async def add_note_endpoint(request: NoteRequest):
    result = add_note(request.paper_id, request.content)
    if result.get("success"):
        return JSONResponse(content=result)
    else:
        return JSONResponse(content=result, status_code=400)

@app.put("/literature/notes/{note_id}")
async def update_note_endpoint(note_id: int, request: UpdateNoteRequest):
    result = update_note(note_id, request.content)
    if result.get("success"):
        return JSONResponse(content=result)
    else:
        return JSONResponse(content=result, status_code=400)

@app.delete("/literature/notes/{note_id}")
async def delete_note_endpoint(note_id: int):
    result = delete_note(note_id)
    if result.get("success"):
        return JSONResponse(content=result)
    else:
        return JSONResponse(content=result, status_code=400)

@app.post("/literature/folders")
async def add_folder_endpoint(request: FolderRequest):
    result = add_folder(request.name, request.description)
    if result.get("success"):
        return JSONResponse(content=result)
    else:
        return JSONResponse(content=result, status_code=400)

@app.delete("/literature/folders/{folder_id}")
async def delete_folder_endpoint(folder_id: int):
    result = delete_folder(folder_id)
    if result.get("success"):
        return JSONResponse(content=result)
    else:
        return JSONResponse(content=result, status_code=400)

@app.get("/literature/folders")
async def list_folders_endpoint():
    result = list_folders()
    return JSONResponse(content=result)

@app.post("/literature/folders/papers")
async def add_paper_to_folder_endpoint(request: FolderPaperRequest):
    result = add_paper_to_folder(request.paper_id, request.folder_id)
    if result.get("success"):
        return JSONResponse(content=result)
    else:
        return JSONResponse(content=result, status_code=400)

@app.delete("/literature/folders/{folder_id}/papers/{paper_id}")
async def remove_paper_from_folder_endpoint(folder_id: int, paper_id: str):
    result = remove_paper_from_folder(paper_id, folder_id)
    if result.get("success"):
        return JSONResponse(content=result)
    else:
        return JSONResponse(content=result, status_code=400)

class LiteratureReviewRequest(BaseModel):
    query: str
    paper_limit: Optional[int] = 15

class ResearchTrendsRequest(BaseModel):
    query: str
    years: Optional[int] = 5

class ResearchGapsRequest(BaseModel):
    query: str

try:
    from agent.literature_review import (
        generate_literature_review,
        analyze_research_trends,
        find_research_gaps
    )
    
    @app.post("/literature/review")
    async def literature_review_endpoint(request: LiteratureReviewRequest):
        result = await generate_literature_review(request.query, request.paper_limit or 15)
        return JSONResponse(content=result)
    
    @app.post("/literature/trends")
    async def research_trends_endpoint(request: ResearchTrendsRequest):
        result = await analyze_research_trends(request.query, request.years or 5)
        return JSONResponse(content=result)
    
    @app.post("/literature/gaps")
    async def research_gaps_endpoint(request: ResearchGapsRequest):
        result = await find_research_gaps(request.query)
        return JSONResponse(content=result)
except ImportError:
    pass

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_websockets.append(websocket)
    
    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            if message_data.get("type") == "task":
                task = message_data.get("message", "")
                
                async def send_step(step: Dict[str, Any]):
                    await websocket.send_json({
                        "type": "step",
                        "data": step
                    })
                
                result = await agent.run(task, callback=send_step)
                
                await websocket.send_json({
                    "type": "complete",
                    "data": {
                        "answer": result["answer"],
                        "total_steps": len(result["steps"]),
                        "iterations": result["iterations"]
                    }
                })
            
    except WebSocketDisconnect:
        if websocket in active_websockets:
            active_websockets.remove(websocket)

try:
    from agent.research_agent import ResearchAgent
    
    research_agents: Dict[str, ResearchAgent] = {}
    
    @app.websocket("/ws/research")
    async def research_websocket(websocket: WebSocket):
        await websocket.accept()
        is_active = True
        
        try:
            while True:
                data = await websocket.receive_json()
                
                if data.get("type") == "start_research":
                    topic = data.get("topic", "")
                    years = data.get("years", 2)
                    max_papers = data.get("max_papers", 30)
                    
                    agent = ResearchAgent()
                    
                    async def progress_callback(progress_data):
                        nonlocal is_active
                        if is_active:
                            try:
                                await websocket.send_json(progress_data)
                            except:
                                is_active = False
                    
                    result = await agent.conduct_research(
                        topic=topic,
                        years=years,
                        max_papers=max_papers,
                        callback=progress_callback
                    )
                    
                    if is_active:
                        try:
                            await websocket.send_json({
                                "type": "complete",
                                "result": result
                            })
                        except:
                            pass
                    
        except WebSocketDisconnect:
            is_active = False
            pass
        except Exception as e:
            is_active = False
            try:
                await websocket.send_json({
                    "type": "error",
                    "error": str(e)
                })
            except:
                pass
        
    @app.websocket("/ws/planning")
    async def planning_websocket(websocket: WebSocket):
        await websocket.accept()
        is_active = True
        print(f"[WS] Connection accepted from client")
        
        async def safe_send(step_data: Dict[str, Any]):
            nonlocal is_active
            if not is_active:
                return False
            try:
                await websocket.send_json(step_data)
                print(f"[WS] Sent message type: {step_data.get('type', 'unknown')}")
                return True
            except Exception as e:
                print(f"[WS] Failed to send message: {e}")
                is_active = False
                return False
        
        try:
            while True:
                try:
                    raw_data = await websocket.receive_text()
                    print(f"[WS] Raw data received: {raw_data[:200]}...")
                    data = json.loads(raw_data)
                except json.JSONDecodeError as e:
                    print(f"[WS] JSON decode error: {e}")
                    await safe_send({
                        "type": "error",
                        "error": f"无效的消息格式: {str(e)}"
                    })
                    continue
                
                print(f"[WS] Parsed message type: {data.get('type', 'unknown')}")
                
                if data.get("type") == "start_planning":
                    task = data.get("task", "")
                    context = data.get("context", {})
                    
                    print(f"[WS] Task: {task[:100] if task else 'EMPTY'}...")
                    print(f"[WS] Context keys: {list(context.keys()) if context else 'None'}")
                    
                    if not task:
                        await safe_send({
                            "type": "error",
                            "error": "任务内容不能为空"
                        })
                        continue
                    
                    async def callback(step_data: Dict[str, Any]):
                        success = await safe_send(step_data)
                        if not success:
                            print("[WS] Callback failed, stopping further messages")
                    
                    try:
                        print(f"[WS] Starting task execution...")
                        if REFLECTION_ENABLED:
                            result = await reflection_agent.execute_task(task, callback=callback, context=context)
                        else:
                            result = await unified_agent.execute_task(task, callback=callback, context_input=context)
                        
                        if is_active:
                            print("[WS] Task completed, sending final result")
                            await safe_send({
                                "type": "complete",
                                "result": result
                            })
                            
                    except Exception as e:
                        import traceback
                        print(f"[WS] Task execution error: {e}")
                        traceback.print_exc()
                        await safe_send({
                            "type": "error",
                            "error": str(e)
                        })
                    
        except WebSocketDisconnect as e:
            is_active = False
            print(f"[WS] Client disconnected: code={e.code}, reason={e.reason}")
        except Exception as e:
            import traceback
            print(f"[WS] Unexpected error: {e}")
            traceback.print_exc()
            is_active = False
            try:
                await websocket.send_json({
                    "type": "error",
                    "error": f"服务器错误: {str(e)}"
                })
            except:
                pass
    
except ImportError as e:
    print(f"Research agent not available: {e}")

@app.on_event("startup")
async def startup_event():
    print(f"Agent initialized. LLM configured: {agent.client is not None}")
    if agent.client is None:
        print("Warning: No API key configured. Running in simulation mode.")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
