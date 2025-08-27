# server.py (with modifications)

import os
import json
import redis
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Tool Authorization API (Redis-Powered)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Redis Connection (No changes) ---
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

# --- Pydantic Models (AuthResponse is updated) ---
class AuthRequest(BaseModel):
    session_id: str
    tool_name: str
    tool_args: Dict[str, Any]

class AuthResponse(BaseModel):
    session_id: str
    authorization: str  # "A" for approve, "D" for deny
    # ⭐ NEW: Add an optional field for the user's modified arguments
    tool_args: Optional[Dict[str, Any]] = None

# --- API Endpoints (/auth/respond is updated) ---

@app.get("/auth/{session_id}")
def get_auth_request(session_id: str):
    # No changes to this endpoint
    if not r: raise HTTPException(status_code=503, detail="Redis not connected")
    key = f"{KEY_PREFIX}{session_id}"
    auth_request_json = r.get(key)
    if not auth_request_json:
        return {"session_id": session_id, "tool_name": None, "tool_args": {}}
    return json.loads(auth_request_json)

@app.post("/auth/request")
def request_authorization(req: AuthRequest):
    # No changes to this endpoint
    if not r: raise HTTPException(status_code=503, detail="Redis not connected")
    key = f"{KEY_PREFIX}{req.session_id}"
    payload = {
        "session_id": req.session_id,
        "tool_name": req.tool_name,
        "tool_args": req.tool_args,
        "authorization": None
    }
    r.set(key, json.dumps(payload), ex=KEY_EXPIRY_SECONDS)
    return {"message": f"Authorization requested for session {req.session_id}"}

@app.post("/auth/respond")
def respond_to_authorization(res: AuthResponse):
    """⭐ UPDATED to handle modified tool arguments."""
    if not r: raise HTTPException(status_code=503, detail="Redis not connected")

    key = f"{KEY_PREFIX}{res.session_id}"
    auth_request_json = r.get(key)
    if not auth_request_json:
        raise HTTPException(status_code=404, detail="No active authorization request for this session.")

    auth_data = json.loads(auth_request_json)

    # Update the authorization status
    auth_data["authorization"] = res.authorization

    # If the user approved WITH modifications, update the tool_args
    if res.authorization == "A" and res.tool_args:
        print(f"User approved with modifications for session {res.session_id}: {res.tool_args}")
        auth_data["tool_args"] = res.tool_args

    ttl = r.ttl(key)
    r.set(key, json.dumps(auth_data), ex=ttl if ttl > 0 else KEY_EXPIRY_SECONDS)

    return {"message": "Response recorded."}

@app.get("/auth/status/{session_id}")
def get_auth_status(session_id: str):
    # ⭐ UPDATED to return the whole payload on decision
    if not r: raise HTTPException(status_code=503, detail="Redis not connected")

    key = f"{KEY_PREFIX}{session_id}"
    auth_request_json = r.get(key)

    if not auth_request_json:
        return {"authorization": None}

    auth_data = json.loads(auth_request_json)
    decision = auth_data.get("authorization")

    if decision is not None:
        r.delete(key)
        # Return the entire object so the agent can check for modified args
        return auth_data

    return {"authorization": None}
