"""
FastAPI server exposing the Luna Version X agent (LangGraph + Gemini) over HTTP.

Features:
- POST /api/chat           : Single chat turn (creates session if absent)
- POST /api/session        : Create a new session for a user
- GET  /api/session/{id}   : Retrieve session message history (sanitized)
- GET  /api/user/{email}/sessions : Get all sessions for a user
- GET  /health             : Basic liveness / readiness info

Includes:
- User email-based session management via MongoDB
- Tool invocation capture via streaming events
- Structured JSON responses with latency, session management
- Graceful startup/shutdown (persists chat history using existing test.py mechanisms)
- CORS enabled (allow all by default; tighten for production)
- Optional environment loading via python-dotenv

Assumptions:
- test.py resides in the same directory and contains the LangGraph implementation
- GOOGLE_API_KEY is set in environment (.env loaded automatically if present)

To run:
    uvicorn api_server:app --host 0.0.0.0 --port 8000 --reload
"""

from __future__ import annotations

import os
import json
import time
import threading
import uuid
from typing import Any, Dict, List, Optional
from datetime import datetime
from urllib.parse import unquote
from fastapi import Response

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
    email: str = Field(..., description="User email for session management")
    session_id: Optional[str] = Field(None, description="Existing session ID or omit to use latest/create new")
    message: str = Field(..., min_length=1, max_length=8000, description="User input text")


class ChatResponse(BaseModel):
    session_id: str
    email: str
    message: str
    response: str
    latency_ms: float
    tool_events: List[Dict[str, Any]] = []
    error: Optional[str] = None


class SessionCreateRequest(BaseModel):
    email: str = Field(..., description="User email for the new session")


class SessionCreateResponse(BaseModel):
    session_id: str
    email: str


class HistoryMessage(BaseModel):
    role: str
    content: str
    timestamp: Optional[str] = None


class SessionHistoryResponse(BaseModel):
    session_id: str
    email: str
    messages: List[HistoryMessage]
    count: int


class UserSessionInfo(BaseModel):
    session_id: str
    last_updated: str
    message_count: int


class UserSessionsResponse(BaseModel):
    email: str
    sessions: List[UserSessionInfo]
    count: int


# -----------------------------------------------------------------------------
# FastAPI App
# -----------------------------------------------------------------------------
app = FastAPI(
    title=f"{APP_NAME} API",
    version="1.0.0",
    description="HTTP interface for the Luna Version X Agent with MongoDB session management",
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
        # Initialize MongoDB connection
        if not backend.setup_mongodb_client():
            raise RuntimeError("Failed to connect to MongoDB")
        _app_graph = backend.create_agent_graph()
        if not _app_graph:
            raise RuntimeError("Failed to initialize LangGraph agent")


def setup_user_session(email: str, session_id: Optional[str] = None) -> str:
    """Setup user session similar to test.py's load_chat_history logic"""
    original_email = backend.user_email
    original_session = backend.session_id

    # Temporarily set the user email to load their history
    backend.user_email = email.strip().lower()

    if session_id:
        # Use the provided session_id
        backend.session_id = session_id
        # Ensure this session exists in chatmap
        if session_id not in backend.chatmap:
            backend.chatmap[session_id] = backend.InMemoryChatMessageHistory()
    else:
        # Load the user's latest session or create new one
        backend.load_chat_history()

    return backend.session_id


# -----------------------------------------------------------------------------
# Core Chat Logic (adapted for LangGraph)
# -----------------------------------------------------------------------------
def invoke_agent(email: str, session_id: str, user_input: str) -> (str, List[Dict[str, Any]]):
    """Invoke the LangGraph agent with tool capture and user session management."""
    ensure_agent_initialized()

    tool_events = []

    # Setup the user session
    actual_session_id = setup_user_session(email, session_id)
    backend.current_api_session_id = actual_session_id
    config = {"configurable": {"thread_id": actual_session_id}}

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

        # Update the chatmap with the conversation
        if actual_session_id not in backend.chatmap:
            backend.chatmap[actual_session_id] = backend.InMemoryChatMessageHistory()

        backend.chatmap[actual_session_id].add_message(backend.HumanMessage(content=user_input))
        backend.chatmap[actual_session_id].add_message(backend.AIMessage(content=response_text))

        # Finalize any remaining tool events
        for tool_event in tool_events:
            if tool_event.end is None:
                tool_event.finalize("Completed")

        tool_events_dict = [evt.to_dict() for evt in tool_events]
        return actual_session_id, response_text, tool_events_dict

    except Exception as e:
        # Finalize any tool events with error
        for tool_event in tool_events:
            if tool_event.end is None:
                tool_event.fail(e)

        tool_events_dict = [evt.to_dict() for evt in tool_events]
        return actual_session_id, f"Error: {e}", tool_events_dict


# -----------------------------------------------------------------------------
# Routes
# -----------------------------------------------------------------------------
@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    start = time.time()
    ensure_agent_initialized()

    try:
        session_id, output, tool_events = invoke_agent(req.email, req.session_id, req.message)
        backend.save_chat_history()
        latency = (time.time() - start) * 1000
        return ChatResponse(
            session_id=session_id,
            email=req.email,
            message=req.message,
            response=output,
            latency_ms=round(latency, 2),
            tool_events=tool_events,
        )
    except Exception as e:
        latency = (time.time() - start) * 1000
        return ChatResponse(
            session_id=req.session_id or "unknown",
            email=req.email,
            message=req.message,
            response="",
            latency_ms=round(latency, 2),
            tool_events=[],
            error=str(e),
        )


@router.post("/session", response_model=SessionCreateResponse)
def create_session(req: SessionCreateRequest):
    ensure_agent_initialized()

    # Create new session ID
    new_sid = str(uuid.uuid4())

    # Set up the user context
    backend.user_email = req.email.strip().lower()
    backend.session_id = new_sid

    # Create empty history for new session
    backend.chatmap[new_sid] = backend.InMemoryChatMessageHistory()

    return SessionCreateResponse(session_id=new_sid, email=req.email)


@router.get("/session/{session_id}/history", response_model=SessionHistoryResponse)
def get_history(session_id: str, email: str, limit: int = 100):
    ensure_agent_initialized()

    # Set up user context to ensure proper access
    backend.user_email = email.strip().lower()

    # Try to load the specific session if not already in memory
    if session_id not in backend.chatmap:
        # Try to load from MongoDB
        if backend.db_client:
            db2 = backend.db_client[backend.CHATS_DB_NAME]
            chats_collection = db2[backend.CHATS_COLLECTION_NAME]
            session_data = chats_collection.find_one({"_id": session_id})

            if session_data and session_data.get("user_email") == email and "messages" in session_data:
                history = backend.InMemoryChatMessageHistory()
                for msg in session_data["messages"]:
                    if msg['type'] == 'human':
                        history.add_message(backend.HumanMessage(content=msg['content']))
                    else:
                        history.add_message(backend.AIMessage(content=msg['content']))
                backend.chatmap[session_id] = history
            else:
                raise HTTPException(status_code=404, detail="Session not found or access denied")
        else:
            raise HTTPException(status_code=404, detail="Session not found")

    history = backend.chatmap.get(session_id)
    if not history:
        raise HTTPException(status_code=404, detail="Session not found")

    msgs = history.messages[-limit:]
    out: List[HistoryMessage] = []
    for m in msgs:
        role = "user" if m.type == "human" else "assistant"
        out.append(HistoryMessage(role=role, content=m.content, timestamp=None))

    return SessionHistoryResponse(
        session_id=session_id,
        email=email,
        messages=out,
        count=len(out)
    )


@router.get("/user/{email:path}/sessions", response_model=UserSessionsResponse)
def get_user_sessions(email: str):
    """Get all sessions for a specific user"""
    ensure_agent_initialized()

    if not backend.db_client:
        raise HTTPException(status_code=500, detail="Database not connected")

    # --- Start of New Debug Code ---
    print("\n" + "="*50)
    print("--- DEBUGGING /user/{email}/sessions ---")
    print(f"1. Raw 'email' parameter received from URL: '{email}'")

    # URL decode and normalize email
    decoded_email = unquote(email).strip().lower()
    print(f"2. Decoded, stripped, and lowercased email: '{decoded_email}'")

    db1 = backend.db_client[backend.METADATA_DB_NAME]
    metadata_collection = db1[backend.METADATA_COLLECTION_NAME]
    print(f"3. Accessing Collection: '{backend.METADATA_DB_NAME}.{backend.METADATA_COLLECTION_NAME}'")

    query = {"_id": decoded_email}
    print(f"4. Executing MongoDB query: {query}")

    user_metadata = metadata_collection.find_one(query)
    print(f"5. MongoDB query result: {user_metadata}")
    # --- End of New Debug Code ---

    if not user_metadata:
        # This part is the source of the 404 error if the query result is None
        print("6. User not found in database. Raising 404 HTTPException.")
        print("="*50 + "\n")
        all_users = list(metadata_collection.find({}, {"_id": 1}).limit(10))
        raise HTTPException(
            status_code=404,
            detail=f"User not found for query: {query}. Is the _id in the database exactly '{decoded_email}'? "
                   f"Sample of _ids found: {[u['_id'] for u in all_users]}"
        )

    print("6. User FOUND in database. Proceeding...")

    if not user_metadata.get("sessions"):
        print("7. User found, but has no 'sessions' array. Returning empty list.")
        print("="*50 + "\n")
        return UserSessionsResponse(email=decoded_email, sessions=[], count=0)

    print(f"7. User has {len(user_metadata.get('sessions', []))} session(s). Fetching details...")

    # Get message counts for each session from db2
    db2 = backend.db_client[backend.CHATS_DB_NAME]
    chats_collection = db2[backend.CHATS_COLLECTION_NAME]

    session_infos = []
    for session_info in user_metadata["sessions"]:
        session_id = session_info["session_id"]
        last_updated = session_info.get("last_updated", "Unknown")

        # Get message count from the actual session data
        session_data = chats_collection.find_one({"_id": session_id})
        message_count = len(session_data.get("messages", [])) if session_data else 0

        # Handle different datetime formats
        if hasattr(last_updated, 'isoformat'):
            last_updated_str = last_updated.isoformat()
        elif isinstance(last_updated, str):
            last_updated_str = last_updated
        else:
            last_updated_str = str(last_updated)

        session_infos.append(UserSessionInfo(
            session_id=session_id,
            last_updated=last_updated_str,
            message_count=message_count
        ))

    print("8. Successfully processed all sessions.")
    print("="*50 + "\n")

    return UserSessionsResponse(
        email=decoded_email,
        sessions=session_infos,
        count=len(session_infos)
    )


@router.delete("/session/{session_id}", status_code=204)
def delete_session(session_id: str, email: str):
    """Deletes a specific chat session for a user."""
    ensure_agent_initialized()
    if not backend.db_client:
        raise HTTPException(status_code=500, detail="Database not connected")

    decoded_email = unquote(email).strip().lower()

    # 1. Delete the main chat data from the chats database
    db2 = backend.db_client[backend.CHATS_DB_NAME]
    chats_collection = db2[backend.CHATS_COLLECTION_NAME]
    delete_result = chats_collection.delete_one({"_id": session_id, "user_email": decoded_email})

    if delete_result.deleted_count == 0:
        # This prevents users from deleting sessions that aren't theirs
        # Or if the session_id is wrong
        raise HTTPException(status_code=404, detail="Session not found or access denied")

    # 2. Remove the session metadata from the user's session list
    db1 = backend.db_client[backend.METADATA_DB_NAME]
    metadata_collection = db1[backend.METADATA_COLLECTION_NAME]
    metadata_collection.update_one(
        {"_id": decoded_email},
        {"$pull": {"sessions": {"session_id": session_id}}}
    )

    # 3. Clean up in-memory cache if it exists
    if session_id in backend.chatmap:
        del backend.chatmap[session_id]

    print(f"🗑️ Deleted session {session_id} for user {decoded_email}")
    return Response(status_code=204)

@app.get("/health")
def health():
    uptime = time.time() - START_TIME
    return {
        "status": "ok",
        "app": APP_NAME,
        "uptime_seconds": round(uptime, 2),
        "model_initialized": _app_graph is not None,
        "active_sessions": len(backend.chatmap) if hasattr(backend, 'chatmap') else 0,
        "mongodb_connected": backend.db_client is not None,
        "current_user": getattr(backend, 'user_email', None),
        "current_session": getattr(backend, 'session_id', None),
    }


# -----------------------------------------------------------------------------
# Lifespan Events
# -----------------------------------------------------------------------------
@app.on_event("startup")
def on_startup():
    try:
        ensure_agent_initialized()
        print("✅ API Server initialized successfully")
    except Exception as e:
        # Log error (print fallback)
        print(f"❌ [startup] Initialization failed: {e}")


@app.on_event("shutdown")
def on_shutdown():
    try:
        backend.save_chat_history()
        print("✅ Chat history saved on shutdown")
    except Exception as e:
        print(f"⚠️ [shutdown] Failed to persist history: {e}")


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
