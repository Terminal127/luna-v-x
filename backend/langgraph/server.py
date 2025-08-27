# server.py (Upgraded with WebSockets)

import os
import json
import asyncio
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import redis

# --- Initialization ---
load_dotenv()
app = FastAPI(title="Tool Authorization API (WebSocket-Powered)")

# Enable CORS for HTTP endpoints
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Redis Connection ---
try:
    r = redis.Redis(
        host=os.getenv("REDIS_HOST"),
        port=int(os.getenv("REDIS_PORT")),
        username=os.getenv("REDIS_USERNAME"),
        password=os.getenv("REDIS_PASSWORD"),
        decode_responses=True,
    )
    r.ping()
    print("✅ Successfully connected to Redis.")
except Exception as e:
    print(f"❌ Could not connect to Redis: {e}")
    r = None

KEY_PREFIX = "auth:"
KEY_EXPIRY_SECONDS = 600

# --- Pydantic Models (Unchanged) ---
class AuthRequest(BaseModel):
    session_id: str
    tool_name: str
    tool_args: Dict[str, Any]

class AuthResponse(BaseModel):
    session_id: str
    authorization: str
    tool_args: Optional[Dict[str, Any]] = None

# --- WebSocket Connection Manager ---
# This class handles the "phone lines" for each user.
class ConnectionManager:
    def __init__(self):
        # A dictionary to store the active connection for each session_id
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, session_id: str):
        """Accept a new WebSocket connection and store it."""
        await websocket.accept()
        self.active_connections[session_id] = websocket
        print(f"📞 WebSocket connected for session: {session_id}")

    def disconnect(self, session_id: str):
        """Remove a disconnected WebSocket."""
        if session_id in self.active_connections:
            del self.active_connections[session_id]
            print(f"🔌 WebSocket disconnected for session: {session_id}")

    async def send_notification(self, message: dict, session_id: str):
        """Send a JSON message (notification) to a specific user's session."""
        if session_id in self.active_connections:
            websocket = self.active_connections[session_id]
            try:
                await websocket.send_json(message)
                print(f"📨 Sent notification to session: {session_id}")
            except Exception as e:
                print(f"Error sending notification to {session_id}: {e}")
                self.disconnect(session_id)

manager = ConnectionManager()

# --- WebSocket Endpoint ---
@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """
    This is the main WebSocket endpoint that frontends connect to.
    It establishes a persistent "phone line" for a given session.
    """
    await manager.connect(websocket, session_id)
    try:
        # Loop indefinitely to keep the connection open.
        # The frontend doesn't need to send messages, just listen.
        while True:
            # We wait here. If the client disconnects, a WebSocketDisconnect
            # exception will be raised, and we can clean up.
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(session_id)

# --- API Endpoints (HTTP) ---

@app.get("/auth/{session_id}")
def get_auth_request(session_id: str):
    """
    Allows the frontend to get the current request details if it missed
    the WebSocket notification (e.g., due to a page refresh).
    """
    if not r: raise HTTPException(status_code=503, detail="Redis not connected")
    key = f"{KEY_PREFIX}{session_id}"
    auth_request_json = r.get(key)
    if not auth_request_json:
        return {"session_id": session_id, "tool_name": None, "tool_args": {}}
    return json.loads(auth_request_json)

@app.post("/auth/request")
async def request_authorization(req: AuthRequest): # Note: This is now an async function
    """
    The backend agent calls this endpoint. It saves the request to Redis
    and then pushes an instant notification to the connected frontend via WebSocket.
    """
    if not r: raise HTTPException(status_code=503, detail="Redis not connected")
    key = f"{KEY_PREFIX}{req.session_id}"
    payload = {
        "session_id": req.session_id,
        "tool_name": req.tool_name,
        "tool_args": req.tool_args,
        "authorization": None
    }
    r.set(key, json.dumps(payload), ex=KEY_EXPIRY_SECONDS)

    # ⭐ The key change: Send a notification over the WebSocket "phone line"
    await manager.send_notification(payload, req.session_id)

    return {"message": f"Authorization requested and notification sent for session {req.session_id}"}

@app.post("/auth/respond")
def respond_to_authorization(res: AuthResponse):
    """
    The frontend calls this HTTP endpoint when the user makes a decision
    (Approve, Deny, Modify). This logic is unchanged.
    """
    if not r: raise HTTPException(status_code=503, detail="Redis not connected")
    key = f"{KEY_PREFIX}{res.session_id}"
    auth_request_json = r.get(key)
    if not auth_request_json:
        raise HTTPException(status_code=404, detail="No active authorization request for this session.")

    auth_data = json.loads(auth_request_json)
    auth_data["authorization"] = res.authorization

    if res.authorization == "A" and res.tool_args:
        auth_data["tool_args"] = res.tool_args

    ttl = r.ttl(key)
    r.set(key, json.dumps(auth_data), ex=ttl if ttl > 0 else KEY_EXPIRY_SECONDS)
    return {"message": "Response recorded."}

@app.get("/auth/status/{session_id}")
def get_auth_status(session_id: str):
    """
    The backend agent still polls this endpoint to get the final decision.
    This logic is also unchanged.
    """
    if not r: raise HTTPException(status_code=503, detail="Redis not connected")
    key = f"{KEY_PREFIX}{session_id}"
    auth_request_json = r.get(key)
    if not auth_request_json:
        return {"authorization": None}

    auth_data = json.loads(auth_request_json)
    decision = auth_data.get("authorization")

    if decision is not None:
        r.delete(key)
        return auth_data

    return {"authorization": None}
