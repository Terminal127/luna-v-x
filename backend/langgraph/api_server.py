"""
FastAPI server exposing the Luna Version X agent (LangGraph + Gemini) over HTTP.

Features:
- POST /api/chat           : Single chat turn (creates session if absent)
- POST /api/session        : Create a new session
- GET  /api/session/{id}   : Retrieve session message history (sanitized)
- GET  /health             : Basic liveness / readiness info

Includes:
- Tool invocation capture via streaming events
- Structured JSON responses with latency, session management
- Graceful startup/shutdown (persists chat history using existing test.py mechanisms)
- CORS enabled (allow all by default; tighten for production)
- Optional environment loading via python-dotenv

Assumptions:
- test.py resides in the same directory and contains the LangGraph implementation
- GOOGLE_API_KEY is set in environment (.env loaded automatically if present)

To run:
    uvicorn api_server:app --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import os
import json
import time
import threading
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi import APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # optional
    load_dotenv = lambda *_, **__: None  # type: ignore

# Import existing LangGraph agent logic
import test as backend  # relative import (test.py contains the LangGraph implementation)

# -----------------------------------------------------------------------------
# Environment & Initialization
# -----------------------------------------------------------------------------
load_dotenv(override=False)

APP_NAME = os.getenv("APP_NAME", "Luna Version X")

# Thread-safety guard for lazy initialization
_init_lock = threading.Lock()
_app_graph = None

START_TIME = time.time()


# -----------------------------------------------------------------------------
# Tool Event Capture (adapted for LangGraph)
# -----------------------------------------------------------------------------
class ToolEvent:
    def __init__(self, name: str, args: Dict[str, Any]):
        self.name = name
        self.args = args
        self.start = time.time()
        self.end: Optional[float] = None
        self.error: Optional[str] = None
        self.output_excerpt: Optional[str] = None

    def finalize(self, output: Any):
        self.end = time.time()
        text = str(output)
        self.output_excerpt = text[:200] + ("..." if len(text) > 200 else "")

    def fail(self, err: Exception):
        self.end = time.time()
        self.error = f"{type(err).__name__}: {err}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tool": self.name,
            "args": self.args,
            "duration_ms": round(((self.end or time.time()) - self.start) * 1000, 2),
            "success": self.error is None,
            "error": self.error,
            "output_excerpt": self.output_excerpt,
        }


# -----------------------------------------------------------------------------
# Pydantic Schemas
# -----------------------------------------------------------------------------
class ChatRequest(BaseModel):
    session_id: Optional[str] = Field(None, description="Existing session ID or omit for implicit continuity")
    message: str = Field(..., min_length=1, max_length=8000, description="User input text")


class ChatResponse(BaseModel):
    session_id: str
    message: str
    response: str
    latency_ms: float
    tool_events: List[Dict[str, Any]] = []
    error: Optional[str] = None


class SessionCreateResponse(BaseModel):
    session_id: str


class HistoryMessage(BaseModel):
    role: str
    content: str
    timestamp: Optional[str] = None


class SessionHistoryResponse(BaseModel):
    session_id: str
    messages: List[HistoryMessage]
    count: int


# -----------------------------------------------------------------------------
# FastAPI App
# -----------------------------------------------------------------------------
app = FastAPI(
    title=f"{APP_NAME} API",
    version="1.0.0",
    description="HTTP interface for the Luna Version X Agent (LangGraph implementation)",
)

# Allow all origins (tighten in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

router = APIRouter(prefix="/api", tags=["chat"])

# ---------------------------------------------------------------------------
# Static Frontend Mount
# ---------------------------------------------------------------------------
# Serve the lightweight frontend (if the directory exists) at the root path.
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend-static"
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")


# -----------------------------------------------------------------------------
# Initialization Helpers
# -----------------------------------------------------------------------------
def ensure_agent_initialized():
    global _app_graph
    if _app_graph is not None:
        return
    with _init_lock:
        if _app_graph is not None:
            return
        backend.load_chat_history()  # reconstruct existing session
        _app_graph = backend.create_agent_graph()
        if not _app_graph:
            raise RuntimeError("Failed to initialize LangGraph agent")


# -----------------------------------------------------------------------------
# Core Chat Logic (adapted for LangGraph)
# -----------------------------------------------------------------------------
def invoke_agent(session_id: str, user_input: str) -> (str, List[Dict[str, Any]]):
    """Invoke the LangGraph agent with tool capture."""
    ensure_agent_initialized()

    tool_events = []
    config = {"configurable": {"thread_id": session_id}}

    try:
        # Get initial message count to know what's new
        initial_state = None
        try:
            # Try to get current state to know existing message count
            initial_state = _app_graph.get_state(config)
            initial_message_count = len(initial_state.values.get("messages", [])) if initial_state.values else 0
        except:
            initial_message_count = 0

        current_tools = {}
        final_state = None

        # Stream through the graph execution
        for event in _app_graph.stream(
            {"messages": [backend.HumanMessage(content=user_input)]},
            config,
            stream_mode="values"
        ):
            final_state = event

            # Only process messages that are NEW (added during this request)
            if "messages" in event:
                all_messages = event["messages"]

                # Only examine messages after the initial count
                new_messages = all_messages[initial_message_count:]

                for message in new_messages:
                    # Skip the user input message we just added
                    if hasattr(message, 'type') and message.type == "human":
                        continue

                    # Check if this is an AI message with tool calls
                    if hasattr(message, 'tool_calls') and message.tool_calls:
                        for tool_call in message.tool_calls:
                            tool_id = tool_call.get("id", "unknown")
                            if tool_id not in current_tools:
                                # New tool call detected
                                tool_event = ToolEvent(
                                    name=tool_call.get("name", "unknown"),
                                    args=tool_call.get("args", {})
                                )
                                current_tools[tool_id] = tool_event
                                tool_events.append(tool_event)

                    # Check if this is a tool message (response from tool)
                    elif hasattr(message, 'tool_call_id') and message.tool_call_id:
                        tool_id = message.tool_call_id
                        if tool_id in current_tools:
                            # Tool execution completed
                            if hasattr(message, 'content'):
                                if "Error" in str(message.content):
                                    current_tools[tool_id].fail(Exception(message.content))
                                else:
                                    current_tools[tool_id].finalize(message.content)

        # Extract the final response
        response_text = "No response generated"
        if final_state and final_state.get("messages"):
            last_message = final_state["messages"][-1]
            if hasattr(last_message, 'content') and last_message.content:
                response_text = last_message.content
            elif hasattr(last_message, 'tool_calls'):
                response_text = "Tool calls executed successfully"

        # Finalize any remaining tool events
        for tool_event in tool_events:
            if tool_event.end is None:
                tool_event.finalize("Completed")

        tool_events_dict = [evt.to_dict() for evt in tool_events]
        return response_text, tool_events_dict

    except Exception as e:
        # Finalize any tool events with error
        for tool_event in tool_events:
            if tool_event.end is None:
                tool_event.fail(e)

        tool_events_dict = [evt.to_dict() for evt in tool_events]
        return f"Error: {e}", tool_events_dict


# -----------------------------------------------------------------------------
# Session Utilities
# -----------------------------------------------------------------------------
def new_session_id() -> str:
    import uuid
    return str(uuid.uuid4())


# -----------------------------------------------------------------------------
# Routes
# -----------------------------------------------------------------------------
@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    start = time.time()
    ensure_agent_initialized()

    # If no explicit session provided, rely on backend global session
    session_id = req.session_id or backend.session_id
    if not session_id:
        session_id = new_session_id()
        backend.session_id = session_id

    try:
        output, tool_events = invoke_agent(session_id, req.message)
        backend.save_chat_history()
        latency = (time.time() - start) * 1000
        return ChatResponse(
            session_id=session_id,
            message=req.message,
            response=output,
            latency_ms=round(latency, 2),
            tool_events=tool_events,
        )
    except Exception as e:
        latency = (time.time() - start) * 1000
        return ChatResponse(
            session_id=session_id,
            message=req.message,
            response="",
            latency_ms=round(latency, 2),
            tool_events=[],
            error=str(e),
        )


@router.post("/session", response_model=SessionCreateResponse)
def create_session():
    ensure_agent_initialized()
    sid = new_session_id()
    # Create empty history for new session
    backend.chatmap[sid] = backend.InMemoryChatMessageHistory()
    return SessionCreateResponse(session_id=sid)


@router.get("/session/{session_id}/history", response_model=SessionHistoryResponse)
def get_history(session_id: str, limit: int = 100):
    ensure_agent_initialized()
    history = backend.chatmap.get(session_id)
    if not history:
        raise HTTPException(status_code=404, detail="Session not found")

    msgs = history.messages[-limit:]
    out: List[HistoryMessage] = []
    for m in msgs:
        role = "user" if m.type == "human" else "assistant"
        out.append(HistoryMessage(role=role, content=m.content, timestamp=None))
    return SessionHistoryResponse(session_id=session_id, messages=out, count=len(out))


@app.get("/health")
def health():
    uptime = time.time() - START_TIME
    return {
        "status": "ok",
        "app": APP_NAME,
        "uptime_seconds": round(uptime, 2),
        "model_initialized": _app_graph is not None,
        "active_sessions": len(backend.chatmap) if hasattr(backend, 'chatmap') else 0,
    }


# -----------------------------------------------------------------------------
# Lifespan Events
# -----------------------------------------------------------------------------
@app.on_event("startup")
def on_startup():
    try:
        ensure_agent_initialized()
    except Exception as e:
        # Log error (print fallback)
        print(f"[startup] Initialization failed: {e}")


@app.on_event("shutdown")
def on_shutdown():
    try:
        backend.save_chat_history()
    except Exception as e:
        print(f"[shutdown] Failed to persist history: {e}")


# Register router last
app.include_router(router)


# -----------------------------------------------------------------------------
# CLI Entrypoint
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api_server:app",
        host=os.getenv("HOST", "127.0.0.1"),  # Changed default to localhost
        port=int(os.getenv("PORT", "8000")),
        reload=bool(os.getenv("UVICORN_RELOAD", "false").lower() == "true"),
    )
