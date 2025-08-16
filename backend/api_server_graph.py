"""
FastAPI server exposing the Luna Version X agent (LangGraph + Gemini) over HTTP & WebSocket.

Features:
- POST /api/chat           : Single chat turn with authorization handling
- POST /api/session        : Create a new session
- GET  /api/session/{id}   : Retrieve session message history (sanitized)
- POST /api/authorize      : Handle tool authorization requests
- GET  /health             : Basic liveness / readiness info
- WebSocket /ws/chat       : Interactive chat with authorization prompts

Includes:
- Tool authorization flow for sensitive tools
- Tool invocation capture via callback handler
- Structured JSON responses with latency, session management
- Authorization state management per session
- CORS enabled (allow all by default; tighten for production)

To run:
    uvicorn api_server:app --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import os
import json
import time
import uuid
import threading
import asyncio
from typing import Any, Dict, List, Optional, Union
from datetime import datetime

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi import APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = lambda *_, **__: None

# LangChain imports
try:
    from langchain_core.callbacks import BaseCallbackHandler
    from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
except ImportError:
    try:
        from langchain.callbacks.base import BaseCallbackHandler
    except ImportError:
        class BaseCallbackHandler:
            pass

# Import the corrected LangGraph agent

import test as backend

# -----------------------------------------------------------------------------
# Environment & Initialization
# -----------------------------------------------------------------------------
load_dotenv(override=False)

APP_NAME = os.getenv("APP_NAME", "Luna Version X")
START_TIME = time.time()

# Thread-safety guard
_init_lock = threading.Lock()
_agent_app = None

# Session management for authorization
authorization_sessions = {}  # session_id -> authorization_state


# -----------------------------------------------------------------------------
# Authorization State Management
# -----------------------------------------------------------------------------
class AuthorizationRequest:
    def __init__(self, session_id: str, tool_calls: List[Dict[str, Any]]):
        self.session_id = session_id
        self.tool_calls = tool_calls
        self.timestamp = datetime.now()
        self.responses = {}  # tool_call_id -> {"approved": bool, "modified_args": dict}
        self.pending = True

    def to_dict(self):
        return {
            "session_id": self.session_id,
            "tool_calls": self.tool_calls,
            "timestamp": self.timestamp.isoformat(),
            "pending": self.pending
        }


# -----------------------------------------------------------------------------
# Callback Handler for Tool Capture
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
    def __init__(self):
        self.events: List[ToolEvent] = []

    def on_tool_start(self, tool: Dict[str, Any], input_str: str, **kwargs: Any):
        name = tool.get("name") if isinstance(tool, dict) else getattr(tool, "name", "unknown_tool")
        evt = ToolEvent(name=name, args={"input": input_str})
        self.events.append(evt)

    def on_tool_end(self, output: Any, **kwargs: Any):
        if not self.events:
            return
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
# Custom Authorization Handler for API
# -----------------------------------------------------------------------------
class APIAuthorizationHandler:
    """Handles authorization for API calls by storing requests and waiting for responses"""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.pending_requests = []

    def request_authorization(self, tool_calls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Request authorization for tool calls - returns immediately for API"""
        sensitive_calls = [tc for tc in tool_calls if tc["name"] in backend.REQUIRES_AUTHORIZATION]

        if not sensitive_calls:
            return tool_calls  # No authorization needed

        # Store authorization request
        auth_request = AuthorizationRequest(self.session_id, sensitive_calls)
        authorization_sessions[self.session_id] = auth_request

        # For API, we raise a special exception to indicate authorization needed
        raise AuthorizationRequiredException(auth_request)

    def get_authorized_calls(self, tool_calls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Get authorized tool calls based on stored responses"""
        auth_state = authorization_sessions.get(self.session_id)
        if not auth_state or auth_state.pending:
            return []

        authorized_calls = []
        for tool_call in tool_calls:
            tool_id = tool_call["id"]
            if tool_id in auth_state.responses:
                response = auth_state.responses[tool_id]
                if response["approved"]:
                    # Use modified args if provided
                    modified_call = tool_call.copy()
                    if response.get("modified_args"):
                        modified_call["args"] = response["modified_args"]
                    authorized_calls.append(modified_call)
                else:
                    # Create denied response
                    denied_call = tool_call.copy()
                    denied_call["denied"] = True
                    authorized_calls.append(denied_call)
            else:
                # Safe tool - auto approve
                if tool_call["name"] not in backend.REQUIRES_AUTHORIZATION:
                    authorized_calls.append(tool_call)

        return authorized_calls


class AuthorizationRequiredException(Exception):
    """Exception raised when authorization is needed"""
    def __init__(self, auth_request: AuthorizationRequest):
        self.auth_request = auth_request
        super().__init__(f"Authorization required for session {auth_request.session_id}")


# -----------------------------------------------------------------------------
# Modified Tool Node for API
# -----------------------------------------------------------------------------
class APIMixedToolNode:
    """Modified tool node that integrates with API authorization system"""

    def __init__(self, safe_tools, sensitive_tools):
        self.safe_tools = {tool.name: tool for tool in safe_tools}
        self.sensitive_tools = {tool.name: tool for tool in sensitive_tools}
        self.all_tools = {**self.safe_tools, **self.sensitive_tools}

    def __call__(self, state: backend.AgentState):
        messages = state["messages"]
        last_message = messages[-1]

        if not hasattr(last_message, 'tool_calls') or not last_message.tool_calls:
            return {"messages": messages}

        # Get session ID from config (passed through graph execution)
        session_id = getattr(self, '_current_session_id', None)
        if not session_id:
            session_id = str(uuid.uuid4())

        # Check if we have pending authorization for this session
        auth_state = authorization_sessions.get(session_id)

        # Separate safe and sensitive tool calls
        safe_calls = [tc for tc in last_message.tool_calls if tc["name"] not in backend.sensitive_tool_names]
        sensitive_calls = [tc for tc in last_message.tool_calls if tc["name"] in backend.sensitive_tool_names]

        results = []

        # Execute safe tools immediately
        for tool_call in safe_calls:
            result = self._execute_tool_call(tool_call, is_safe=True)
            results.append(result)

        # Handle sensitive tools
        if sensitive_calls:
            if not auth_state or auth_state.pending:
                # Need authorization - raise exception to trigger authorization flow
                auth_handler = APIAuthorizationHandler(session_id)
                try:
                    auth_handler.request_authorization(sensitive_calls)
                except AuthorizationRequiredException:
                    # This will be caught by the API handler
                    raise
            else:
                # We have authorization responses - process them
                for tool_call in sensitive_calls:
                    tool_id = tool_call["id"]
                    if tool_id in auth_state.responses:
                        response = auth_state.responses[tool_id]
                        if response["approved"]:
                            # Use modified args if provided
                            if response.get("modified_args"):
                                tool_call["args"] = response["modified_args"]
                            result = self._execute_tool_call(tool_call, is_safe=False)
                            results.append(result)
                        else:
                            # Create denied response
                            result = ToolMessage(
                                content="Authorization denied by user.",
                                tool_call_id=tool_id
                            )
                            results.append(result)

        return {"messages": messages + results}

    def _execute_tool_call(self, tool_call: Dict[str, Any], is_safe: bool) -> ToolMessage:
        """Execute a single tool call"""
        tool_name = tool_call["name"]
        tool_id = tool_call["id"]

        try:
            tool_dict = self.safe_tools if is_safe else self.sensitive_tools
            if tool_name in tool_dict:
                tool_instance = tool_dict[tool_name]
                result_content = tool_instance.invoke(tool_call["args"])
                return ToolMessage(content=result_content, tool_call_id=tool_id)
            else:
                return ToolMessage(
                    content=f"Error: Tool {tool_name} not found",
                    tool_call_id=tool_id
                )
        except Exception as e:
            return ToolMessage(
                content=f"Error executing {tool_name}: {str(e)}",
                tool_call_id=tool_id
            )


# -----------------------------------------------------------------------------
# Pydantic Schemas
# -----------------------------------------------------------------------------
class ChatRequest(BaseModel):
    session_id: Optional[str] = Field(None, description="Session ID")
    message: str = Field(..., min_length=1, max_length=8000, description="User input")


class AuthorizationResponse(BaseModel):
    tool_call_id: str
    approved: bool
    modified_args: Optional[Dict[str, Any]] = None


class AuthorizeRequest(BaseModel):
    session_id: str
    responses: List[AuthorizationResponse]


class ChatResponse(BaseModel):
    session_id: str
    message: str
    response: Optional[str] = None
    latency_ms: float
    tool_events: List[Dict[str, Any]] = []
    error: Optional[str] = None
    authorization_required: Optional[Dict[str, Any]] = None


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
# WebSocket Connection Manager
# -----------------------------------------------------------------------------
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        self.active_connections[session_id] = websocket

    def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]

    async def send_personal_message(self, message: dict, session_id: str):
        websocket = self.active_connections.get(session_id)
        if websocket:
            await websocket.send_json(message)


manager = ConnectionManager()


# -----------------------------------------------------------------------------
# FastAPI App
# -----------------------------------------------------------------------------
app = FastAPI(
    title=f"{APP_NAME} API",
    version="2.0.0",
    description="HTTP interface for Luna Version X Agent with Authorization",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

router = APIRouter(prefix="/api", tags=["chat"])


# -----------------------------------------------------------------------------
# Static Frontend Mount
# -----------------------------------------------------------------------------
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend-static"
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")


# -----------------------------------------------------------------------------
# Initialization
# -----------------------------------------------------------------------------
def ensure_agent_initialized():
    global _agent_app
    if _agent_app is not None:
        return

    with _init_lock:
        if _agent_app is not None:
            return

        # Initialize the backend
        backend.load_chat_history()
        _agent_app = backend.create_agent_graph()

        # Replace the tool node with our API-compatible version
        if _agent_app:
            # Access the internal graph to replace the tool node
            # This is a bit hacky but necessary for API integration
            graph = _agent_app.graph
            api_tool_node = APIMixedToolNode(backend.safe_tools, backend.sensitive_tools)

            # Replace the tools node
            if hasattr(graph, 'nodes') and 'tools' in graph.nodes:
                graph.nodes['tools'] = api_tool_node


# -----------------------------------------------------------------------------
# Core Chat Logic
# -----------------------------------------------------------------------------
def invoke_agent(session_id: str, user_input: str) -> tuple[Optional[str], List[Dict[str, Any]], Optional[AuthorizationRequest]]:
    """Invoke the agent with authorization handling."""
    ensure_agent_initialized()

    config = {"configurable": {"thread_id": session_id}}

    # Set current session ID for tool node
    if _agent_app and hasattr(_agent_app.graph, 'nodes') and 'tools' in _agent_app.graph.nodes:
        tool_node = _agent_app.graph.nodes['tools']
        if isinstance(tool_node, APIMixedToolNode):
            tool_node._current_session_id = session_id

    handler = ToolCaptureHandler()

    try:
        final_state = None
        for event in _agent_app.stream(
            {"messages": [HumanMessage(content=user_input)]},
            config,
            stream_mode="values"
        ):
            final_state = event

        if final_state and final_state.get("messages"):
            last_message = final_state["messages"][-1]
            response_text = last_message.content if hasattr(last_message, 'content') else str(last_message)
        else:
            response_text = "No response generated"

        tool_events = [evt.to_dict() for evt in handler.events]
        return response_text, tool_events, None

    except AuthorizationRequiredException as e:
        # Authorization needed
        tool_events = [evt.to_dict() for evt in handler.events]
        return None, tool_events, e.auth_request
    except Exception as e:
        tool_events = [evt.to_dict() for evt in handler.events]
        return f"Error: {e}", tool_events, None


def new_session_id() -> str:
    return str(uuid.uuid4())


# -----------------------------------------------------------------------------
# Routes
# -----------------------------------------------------------------------------
@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    start = time.time()
    ensure_agent_initialized()

    session_id = req.session_id or new_session_id()

    try:
        output, tool_events, auth_request = invoke_agent(session_id, req.message)
        latency = (time.time() - start) * 1000

        if auth_request:
            # Authorization required
            return ChatResponse(
                session_id=session_id,
                message=req.message,
                latency_ms=round(latency, 2),
                tool_events=tool_events,
                authorization_required=auth_request.to_dict()
            )
        else:
            # Normal response
            backend.save_chat_history()
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
            latency_ms=round(latency, 2),
            tool_events=[],
            error=str(e),
        )


@router.post("/authorize")
def authorize_tools(req: AuthorizeRequest):
    """Handle tool authorization responses"""
    auth_state = authorization_sessions.get(req.session_id)
    if not auth_state:
        raise HTTPException(status_code=404, detail="No authorization request found for session")

    # Process authorization responses
    for response in req.responses:
        auth_state.responses[response.tool_call_id] = {
            "approved": response.approved,
            "modified_args": response.modified_args
        }

    # Mark as no longer pending
    auth_state.pending = False

    return {"status": "authorized", "session_id": req.session_id}


@router.post("/session", response_model=SessionCreateResponse)
def create_session():
    ensure_agent_initialized()
    session_id = new_session_id()
    backend.chatmap[session_id] = backend.InMemoryChatMessageHistory()
    return SessionCreateResponse(session_id=session_id)


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
        "model_initialized": _agent_app is not None,
        "active_sessions": len(backend.chatmap) if hasattr(backend, 'chatmap') else 0,
        "pending_authorizations": len(authorization_sessions)
    }


# -----------------------------------------------------------------------------
# WebSocket Endpoint
# -----------------------------------------------------------------------------
@app.websocket("/ws/chat/{session_id}")
async def websocket_chat(websocket: WebSocket, session_id: str):
    await manager.connect(websocket, session_id)

    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            message = data.get("message", "")

            if not message:
                continue

            start = time.time()

            try:
                output, tool_events, auth_request = invoke_agent(session_id, message)
                latency = (time.time() - start) * 1000

                if auth_request:
                    # Send authorization request
                    await manager.send_personal_message({
                        "type": "authorization_required",
                        "session_id": session_id,
                        "message": message,
                        "latency_ms": round(latency, 2),
                        "tool_events": tool_events,
                        "authorization_request": auth_request.to_dict()
                    }, session_id)

                    # Wait for authorization response
                    auth_data = await websocket.receive_json()
                    if auth_data.get("type") == "authorization_response":
                        # Process authorization
                        responses = auth_data.get("responses", [])
                        auth_state = authorization_sessions.get(session_id)
                        if auth_state:
                            for resp in responses:
                                auth_state.responses[resp["tool_call_id"]] = {
                                    "approved": resp["approved"],
                                    "modified_args": resp.get("modified_args")
                                }
                            auth_state.pending = False

                            # Continue execution
                            output, tool_events, _ = invoke_agent(session_id, message)

                            await manager.send_personal_message({
                                "type": "response",
                                "session_id": session_id,
                                "message": message,
                                "response": output,
                                "latency_ms": round(latency, 2),
                                "tool_events": tool_events
                            }, session_id)
                else:
                    # Send normal response
                    await manager.send_personal_message({
                        "type": "response",
                        "session_id": session_id,
                        "message": message,
                        "response": output,
                        "latency_ms": round(latency, 2),
                        "tool_events": tool_events
                    }, session_id)

                    backend.save_chat_history()

            except Exception as e:
                await manager.send_personal_message({
                    "type": "error",
                    "session_id": session_id,
                    "message": message,
                    "error": str(e),
                    "latency_ms": round((time.time() - start) * 1000, 2)
                }, session_id)

    except WebSocketDisconnect:
        manager.disconnect(session_id)


# -----------------------------------------------------------------------------
# Lifespan Events
# -----------------------------------------------------------------------------
@app.on_event("startup")
def on_startup():
    try:
        ensure_agent_initialized()
        print(f"🚀 {APP_NAME} API Server started successfully")
    except Exception as e:
        print(f"❌ Startup failed: {e}")


@app.on_event("shutdown")
def on_shutdown():
    try:
        backend.save_chat_history()
        print("💾 Chat history saved")
    except Exception as e:
        print(f"⚠️ Shutdown error: {e}")


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
