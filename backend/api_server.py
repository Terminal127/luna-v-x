"""
FastAPI server exposing the Luna Version X agent (LangChain + Gemini) over HTTP & WebSocket.

Features:
- POST /api/chat           : Single chat turn (creates session if absent)
- POST /api/session        : Create a new session
- GET  /api/session/{id}   : Retrieve session message history (sanitized)
- GET  /health             : Basic liveness / readiness info
- WebSocket /ws/chat       : (Basic) interactive chat channel (non-token streaming placeholder)

Includes:
- Tool invocation capture via a custom callback handler (records name, args, duration, success/error)
- Structured JSON responses with latency, session management
- Graceful startup/shutdown (persists chat history using existing new.py mechanisms)
- CORS enabled (allow all by default; tighten for production)
- Optional environment loading via python-dotenv

Assumptions:
- new.py resides in the same directory and contains:
    - setup_model()
    - setup_agent_executor(model)
    - load_chat_history()
    - save_chat_history()
    - get_chat_history(session_id)
    - global 'tools' list
- MODEL_API_KEY is set in environment (.env loaded automatically if present)

To run:
    uvicorn api_server:app --host 0.0.0.0 --port 8000

TODO (future enhancements):
    - True token streaming (Gemini streaming or chunked responses)
    - Authentication / API keys / rate limiting
    - Per-session memory summaries endpoint
    - Structured tool schemas returned to client
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
    from dotenv import load_dotenv, set_key
except ImportError:  # optional
    load_dotenv = lambda *_, **__: None  # type: ignore
    set_key = lambda *_, **__: None  # type: ignore

# LangChain callback base (attempt new import path first)
try:
    from langchain_core.callbacks import BaseCallbackHandler
except ImportError:  # fallback for older versions
    try:
        from langchain.callbacks.base import BaseCallbackHandler  # type: ignore
    except ImportError:
        # Minimal shim if callbacks not available
        class BaseCallbackHandler:  # type: ignore
            pass

# Import existing agent logic
import new as backend  # relative import (directory must be on PYTHONPATH)

# -----------------------------------------------------------------------------
# Environment & Initialization
# -----------------------------------------------------------------------------
load_dotenv(override=False)

APP_NAME = os.getenv("APP_NAME", "Luna Version X")
# WebSocket support removed; ENABLE_WEBSOCKET no longer used

# Thread-safety guard for lazy initialization
_init_lock = threading.Lock()
_model = None
_agent_with_history = None

START_TIME = time.time()


# -----------------------------------------------------------------------------
# Callback Handler to capture tool invocations
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


class ToolCaptureHandler(BaseCallbackHandler):
    """Captures tool start/end events for a single request."""

    def __init__(self):
        self.events: List[ToolEvent] = []

    # LangChain new callback signatures:
    def on_tool_start(self, tool: Dict[str, Any], input_str: str, **kwargs: Any):
        name = tool.get("name") if isinstance(tool, dict) else getattr(tool, "name", "unknown_tool")
        evt = ToolEvent(name=name, args={"input": input_str})
        self.events.append(evt)

    def on_tool_end(self, output: Any, **kwargs: Any):
        if not self.events:
            return
        # finalize last unfinished
        for evt in reversed(self.events):
            if evt.end is None:
                evt.finalize(output)
                break

    def on_tool_error(self, error: Exception, **kwargs: Any):
        if not self.events:
            return
        for evt in reversed(self.events):
            if evt.end is None:
                evt.fail(error)
                break


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


class ModelConfigRequest(BaseModel):
    api_key: Optional[str] = Field(None, description="New Google API key")
    model_name: Optional[str] = Field(None, description="Model name (e.g., gemini-1.5-flash)")
    temperature: Optional[float] = Field(None, description="Model temperature (0.0-1.0)")


class ModelConfigResponse(BaseModel):
    success: bool
    message: str
    current_config: Dict[str, Any]


# -----------------------------------------------------------------------------
# FastAPI App
# -----------------------------------------------------------------------------
app = FastAPI(
    title=f"{APP_NAME} API",
    version="1.0.0",
    description="HTTP interface for the Luna Version X Agent (WebSocket removed)",
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
# This allows direct navigation to "/" to load the chat UI.
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend-static"
if FRONTEND_DIR.exists():
    # Mount with html=True so index.html is served for "/"
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")


# -----------------------------------------------------------------------------
# Initialization Helpers
# -----------------------------------------------------------------------------
def ensure_agent_initialized():
    global _model, _agent_with_history
    if _agent_with_history is not None:
        return
    with _init_lock:
        if _agent_with_history is not None:
            return
        backend.load_chat_history()  # reconstruct existing session (backend manages session_id itself)
        _model = backend.setup_model()
        _agent_with_history = backend.setup_agent_executor(_model)


# -----------------------------------------------------------------------------
# Core Chat Logic (bypasses get_response to attach callbacks)
# -----------------------------------------------------------------------------
def invoke_agent(session_id: str, user_input: str) -> (str, List[Dict[str, Any]]):
    """Invoke the agent with tool capture."""
    ensure_agent_initialized()

    handler = ToolCaptureHandler()

    # We call the runnable directly so we can pass callbacks
    try:
        raw = _agent_with_history.invoke(
            {"input": user_input},
            config={
                "callbacks": [handler],
                "configurable": {"session_id": session_id},
            },
        )
    except Exception as e:
        return f"Error: {e}", [evt.to_dict() for evt in handler.events]

    # Normalize agent output
    response_text = None
    if isinstance(raw, dict):
        # typical AgentExecutor returns {"output": "...", ...}
        response_text = raw.get("output") or raw.get("answer") or raw.get("content") or json.dumps(raw)
    else:
        response_text = str(raw)

    tool_events = [evt.to_dict() for evt in handler.events]
    return response_text, tool_events


# -----------------------------------------------------------------------------
# Session Utilities
# -----------------------------------------------------------------------------
def new_session_id() -> str:
    import uuid
    return str(uuid.uuid4())


def update_env_file(key: str, value: str):
    """Update environment variable in .env file"""
    try:
        # Look for .env file in current directory or parent directory
        env_file = Path(".env")
        if not env_file.exists():
            env_file = Path("../.env")
        if not env_file.exists():
            env_file = Path(".env")  # Create in current directory

        set_key(str(env_file), key, value)
        print(f"✅ Updated {key} in {env_file}")
        return True
    except Exception as e:
        print(f"❌ Failed to update .env file: {e}")
        return False

def reinitialize_model():
    """Force reinitialize the model and agent with new settings"""
    global _model, _agent_with_history
    with _init_lock:
        _model = None
        _agent_with_history = None
        backend.load_chat_history()
        _model = backend.setup_model()
        if _model:
            _agent_with_history = backend.setup_agent_executor(_model)
            return True
    return False


# -----------------------------------------------------------------------------
# Routes
# -----------------------------------------------------------------------------
@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    start = time.time()
    ensure_agent_initialized()

    # If no explicit session provided, rely on backend global session (it manages continuity)
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


@router.post("/config/model", response_model=ModelConfigResponse)
def update_model_config(config: ModelConfigRequest):
    """Update API key and model configuration"""
    try:
        updated_settings = {}

        # Update environment variables in memory AND persist to .env file
        if config.api_key:
            os.environ["MODEL_API_KEY"] = config.api_key
            update_env_file("MODEL_API_KEY", config.api_key)
            updated_settings["api_key"] = "***" + config.api_key[-4:] if len(config.api_key) > 4 else "***"

        if config.model_name:
            os.environ["MODEL_NAME"] = config.model_name
            update_env_file("MODEL_NAME", config.model_name)
            updated_settings["model_name"] = config.model_name

        if config.temperature is not None:
            os.environ["TEMPERATURE"] = str(config.temperature)
            update_env_file("TEMPERATURE", str(config.temperature))
            updated_settings["temperature"] = config.temperature

        # Reinitialize the model with new settings
        if reinitialize_model():
            current_config = {
                "model_name": os.getenv("MODEL_NAME", "gemini-1.5-flash"),
                "temperature": float(os.getenv("TEMPERATURE", "0.3")),
                "api_key": "***" + os.getenv("MODEL_API_KEY", "")[-4:] if os.getenv("MODEL_API_KEY") else "Not set",
                "model_initialized": _model is not None
            }

            return ModelConfigResponse(
                success=True,
                message=f"Model configuration updated successfully: {', '.join(updated_settings.keys())}",
                current_config=current_config
            )
        else:
            return ModelConfigResponse(
                success=False,
                message="Failed to reinitialize model. Please check your API key.",
                current_config={}
            )

    except Exception as e:
        return ModelConfigResponse(
            success=False,
            message=f"Error updating configuration: {str(e)}",
            current_config={}
        )


@router.get("/config/model", response_model=ModelConfigResponse)
def get_model_config():
    """Get current model configuration"""
    try:
        current_config = {
            "model_name": os.getenv("MODEL_NAME", "gemini-1.5-flash"),
            "temperature": float(os.getenv("TEMPERATURE", "0.3")),
            "api_key": "***" + os.getenv("MODEL_API_KEY", "")[-4:] if os.getenv("MODEL_API_KEY") else "Not set",
            "model_initialized": _model is not None
        }

        return ModelConfigResponse(
            success=True,
            message="Current model configuration",
            current_config=current_config
        )
    except Exception as e:
        return ModelConfigResponse(
            success=False,
            message=f"Error getting configuration: {str(e)}",
            current_config={}
        )


@router.get("/debug/routes")
def debug_routes():
    """Debug endpoint to check if router is working"""
    return {
        "message": "Router is working!",
        "available_endpoints": [
            "/api/chat",
            "/api/session",
            "/api/config/model",
            "/api/debug/routes"
        ]
    }


@router.get("/debug/env")
def debug_env():
    """Debug endpoint to check environment variables"""
    return {
        "environment_variables": {
            "MODEL_API_KEY": "***" + os.getenv("MODEL_API_KEY", "NOT_SET")[-4:] if os.getenv("MODEL_API_KEY") else "NOT_SET",
            "MODEL_NAME": os.getenv("MODEL_NAME", "NOT_SET"),
            "TEMPERATURE": os.getenv("TEMPERATURE", "NOT_SET"),
        },
        "model_status": {
            "initialized": _model is not None,
            "agent_initialized": _agent_with_history is not None,
        },
        "process_id": os.getpid(),
        "current_working_directory": os.getcwd(),
    }


@app.get("/health")
def health():
    uptime = time.time() - START_TIME
    return {
        "status": "ok",
        "app": APP_NAME,
        "uptime_seconds": round(uptime, 2),
        "model_initialized": _agent_with_history is not None,
        "active_sessions": len(backend.chatmap),
    }


# WebSocket endpoint removed (previously /ws/chat). All interaction now via REST /api/chat.


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
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=bool(os.getenv("UVICORN_RELOAD", "false").lower() == "true"),
    )
