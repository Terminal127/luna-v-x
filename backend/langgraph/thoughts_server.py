import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

# --- Initialization ---
app = FastAPI(title="Luna Agent Thoughts Streamer")

# Allow Cross-Origin Resource Sharing (CORS) so your frontend can connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],     # Allows all methods (GET, POST, etc.)
    allow_headers=["*"],     # Allows all headers
)

# --- WebSocket Connection Manager ---
class ConnectionManager:
    def __init__(self):
        self.active_connection: Optional[WebSocket] = None

    async def connect(self, websocket: WebSocket):
        """Accept and store the one active WebSocket connection."""
        await websocket.accept()
        self.active_connection = websocket
        print("✅ Frontend connected to thoughts stream.")

    def disconnect(self):
        """Clear the active connection."""
        self.active_connection = None
        print("🔌 Frontend disconnected from thoughts stream.")

    async def broadcast(self, message: str):
        """Send a message to the active frontend connection if it exists."""
        if self.active_connection:
            try:
                await self.active_connection.send_text(message)
            except Exception as e:
                # This might happen if the frontend closes the tab abruptly
                print(f"Error sending thought, connection might be closed: {e}")
                self.disconnect()

manager = ConnectionManager()

# Pydantic model for the incoming thought from the agent
class Thought(BaseModel):
    step: str

@app.websocket("/ws/thoughts")
async def websocket_endpoint(websocket: WebSocket):
    """
    This is the endpoint your frontend will connect to.
    It establishes the persistent "phone line" for receiving thoughts.
    """
    await manager.connect(websocket)
    try:
        # Loop indefinitely to keep the connection open.
        # We don't expect the frontend to send any messages, just listen.
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect()

@app.post("/thought")
async def post_thought(thought: Thought):
    """
    This is the endpoint your Agent (`test.py`) will call.
    It receives a thought and broadcasts it to the connected frontend.
    """

    print(f"🧠 Received thought: '{thought.step}'")
    # Broadcast the thought to the frontend via the WebSocket manager
    await manager.broadcast(thought.step)
    return {"status": "ok", "thought_sent": thought.step}

# A simple health check endpoint
@app.get("/health")
def health_check():
    return {"status": "ok", "message": "Thoughts server is running."}
