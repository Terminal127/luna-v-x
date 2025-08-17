from fastapi import FastAPI
from pydantic import BaseModel
from typing import Dict, Any
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Tool Config API")

# ✅ Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # allow all origins (for dev, use ["http://localhost:3000"] for Next.js)
    allow_credentials=True,
    allow_methods=["*"],  # allow all HTTP methods
    allow_headers=["*"],  # allow all headers
)

# Default config
config = {
    "tool_name": "default_tool",
    "tool_args": {},
    "authorization": None
}

# Request model
class ConfigUpdate(BaseModel):
    tool_name: str | None = None
    tool_args: Dict[str, Any] | None = None
    authorization: str | None = None

@app.get("/")
def get_config():
    """Get current config"""
    return config

@app.post("/")
def update_config(update: ConfigUpdate):
    """Update tool_name and/or tool_args"""
    if update.tool_name is not None:
        config["tool_name"] = update.tool_name
    if update.tool_args is not None:
        config["tool_args"] = update.tool_args
    if update.authorization is not None:
        config["authorization"] = update.authorization
    return {"message": "Config updated successfully", "config": config}
