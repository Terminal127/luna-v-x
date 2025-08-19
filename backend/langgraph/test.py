import os
import sys
import uuid
import json
import requests
import subprocess

import time
from urllib.parse import quote, unquote
import readline
from datetime import datetime
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.chat_history import InMemoryChatMessageHistory

from langchain_core.runnables.history import RunnableWithMessageHistory

from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END, START
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict
from dotenv import load_dotenv
import warnings
import base64
from email.mime.text import MIMEText

from typing import Dict, Any, Optional, List, Annotated

from pathlib import Path
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

warnings.filterwarnings("ignore", message="Convert_system_message_to_human will be deprecated!")

load_dotenv()

db_client = None

MONGO_USERNAME = os.getenv("MONGO_USERNAME")
DB_PASSWORD = os.getenv("DB_PASSWORD")
MONGO_CLUSTER = os.getenv("MONGO_CLUSTER")
MONGO_URI = os.getenv("MONGO_URI", f"mongodb+srv://{MONGO_USERNAME}:{DB_PASSWORD}@{MONGO_CLUSTER}/?retryWrites=true&w=majority&appName=Cluster0")
METADATA_DB_NAME = os.getenv("METADATA_DB_NAME")
CHATS_DB_NAME = os.getenv("CHATS_DB_NAME")
METADATA_COLLECTION_NAME = os.getenv("METADATA_COLLECTION_NAME")
CHATS_COLLECTION_NAME = os.getenv("CHATS_COLLECTION_NAME")
SECRETS_COLLECTION_NAME = os.getenv("SECRETS_COLLECTION_NAME")

# Global variables
chatmap = {}
session_id = os.getenv("DEFAULT_SESSION_ID")
user_email = os.getenv("DEFAULT_USER_EMAIL")

# --- ENHANCED PERSISTENCE PATHS (Legacy, for command history only) ---
PROJECT_ROOT = Path("/home/anubhav/courses/luna-version-x/backend/langgraph")
COMMAND_HISTORY_FILE = PROJECT_ROOT / "langchain_chat_history.json"

# Ensure directories exist for command history
PROJECT_ROOT.mkdir(exist_ok=True)


# Authorization settings - tools that require user permission
REQUIRES_AUTHORIZATION = {
    "read_gmail_messages": "This will read your Gmail messages. Do you want to proceed?",
    "send_gmail_message": "This will send a gmail to the appopriate authority, Fo you want to proceed"
}


# State for LangGraph
class AgentState(TypedDict):
    messages: Annotated[List[HumanMessage | AIMessage | ToolMessage], add_messages]

def get_user_access_token(user_email):
    """Get user's access token from MongoDB secrets collection"""
    try:
        # Use the same MongoDB connection as your main app
        mongo_uri = os.getenv("MONGO_URI")
        client = MongoClient(mongo_uri)
        db = client[METADATA_DB_NAME]

        collection = db[SECRETS_COLLECTION_NAME]

        # Find the user's token document
        token_doc = collection.find_one({"email": user_email})

        if token_doc and "accessToken" in token_doc:
            print(f"Found access token for {user_email}")
            return token_doc["accessToken"]
        else:
            print(f"No access token found for {user_email}")
            return None

    except Exception as e:
        print(f"Error getting access token from MongoDB: {e}")
        return None

def setup_readline():
    """Setup readline for command history and arrow key support"""
    try:
        readline.parse_and_bind("tab: complete")
        if COMMAND_HISTORY_FILE.exists():
            readline.read_history_file(str(COMMAND_HISTORY_FILE))
        readline.set_history_length(1000)
    except Exception as e:
        print(f"Warning: Could not setup readline: {e}")

def save_readline_history():
    """Save command history to file"""
    try:
        readline.write_history_file(str(COMMAND_HISTORY_FILE))
    except Exception as e:
        print(f"Warning: Could not save command history: {e}")

# ==============================================================================
#  TOOLS DEFINITION (No changes needed in the tools themselves)
# ==============================================================================
@tool
def get_current_time() -> str:
    """Get the current date and time."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

@tool
def calculate(expression: str) -> str:
    """Safely evaluate a mathematical expression."""
    import ast, operator as op
    try:
        operators = {
            ast.Add: op.add, ast.Sub: op.sub, ast.Mult: op.mul,
            ast.Div: op.truediv, ast.Mod: op.mod, ast.Pow: op.pow,
            ast.USub: op.neg, ast.UAdd: op.pos,
        }
        def _eval(node):
            if isinstance(node, ast.Num):
                return node.n
            if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
                return node.value
            if isinstance(node, ast.BinOp) and type(node.op) in operators:
                return operators[type(node.op)](_eval(node.left), _eval(node.right))
            if isinstance(node, ast.UnaryOp) and type(node.op) in operators:
                return operators[type(node.op)](_eval(node.operand))
            raise ValueError("Unsupported expression component")
        tree = ast.parse(expression, mode='eval')
        result = _eval(tree.body)
        return str(result)
    except ZeroDivisionError:
        return "Error: Division by zero"
    except Exception as e:
        return f"Error calculating: {e}"

@tool
def get_weather(city: str) -> str:
    """Get current weather information for a city."""
    try:
        return f"Mock weather data for {city}: Sunny, 22°C, Light breeze"
    except Exception as e:
        return f"Error getting weather: {str(e)}"

@tool
def file_operations(operation: str, filename: str, content: str = "") -> str:
    """Perform controlled file system interactions in the CURRENT working directory only."""
    # This tool's implementation remains unchanged
    try:
        operation = operation.lower().strip()
        allowed_ops = {"read", "write", "list"}
        if operation not in allowed_ops:
            return "Error: Invalid operation. Use one of: read, write, list"

        base_dir = os.getcwd()
        target = filename.strip()
        if target == "" and operation == "list":
            target_path = base_dir
        elif target == "":
            return "Error: filename required for this operation"
        else:
            if os.path.isabs(target):
                return "Error: Absolute paths are not allowed"
            if ".." in target.split(os.sep):
                return "Error: Parent directory traversal is not allowed"
            target_path = os.path.realpath(os.path.join(base_dir, target))
            if os.path.commonpath([base_dir, target_path]) != base_dir:
                return "Error: Path escapes the working directory"

        if operation == "list":
            if not os.path.isdir(target_path):
                return f"Error: Directory not found: {filename or '.'}"
            entries = sorted(os.listdir(target_path))
            if not entries:
                return "(empty directory)"
            return "\n".join(entries)

        if operation == "read":
            if not os.path.exists(target_path):
                return f"Error: File not found: {filename}"
            if os.path.isdir(target_path):
                return "Error: Path refers to a directory, not a file"
            if os.path.getsize(target_path) > 2 * 1024 * 1024:
                return "Error: File too large to read (>2MB)"
            with open(target_path, "r", encoding="utf-8", errors="replace") as f:
                return f.read()

        if operation == "write":
            if len(content) > 100_000:
                return "Error: Content exceeds 100KB write limit"
            parent = os.path.dirname(target_path)
            if parent and not os.path.exists(parent):
                return f"Error: Parent directory does not exist: {parent}"
            with open(target_path, "w", encoding="utf-8") as f:
                f.write(content)
            return f"Success: Wrote {len(content)} bytes to {filename}"

        return "Error: Unhandled operation"
    except Exception as e:
        return f"Error: {e}"

@tool
def run_command(command: str) -> str:
    """Execute a safe shell command and return its output."""
    # This tool's implementation remains unchanged
    try:
        safe_commands = ['ls', 'pwd', 'date', 'whoami', 'echo', 'cat', 'head', 'tail']
        cmd_parts = command.split()
        if not cmd_parts or cmd_parts[0] not in safe_commands:
            return "Error: Command not allowed for security reasons"
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=10)
        return result.stdout if result.returncode == 0 else f"Error: {result.stderr}"
    except subprocess.TimeoutExpired:
        return "Error: Command timed out"
    except Exception as e:
        return f"Error: {str(e)}"

@tool
def get_chat_history_summary() -> str:
    """Get a summary of the current chat session history."""
    global chatmap, session_id
    if session_id not in chatmap or not chatmap[session_id].messages:
        return "No chat history found in current session."
    history = chatmap[session_id].messages
    recent_messages = history[-20:] if len(history) > 20 else history
    summary = "Recent chat history:\n"
    for i, msg in enumerate(recent_messages):
        role = "User" if msg.type == "human" else "Assistant"
        content = msg.content[:100] + "..." if len(msg.content) > 100 else msg.content
        summary += f"{i+1}. {role}: {content}\n"
    return summary

@tool
def task_planner(user_request: str) -> str:
    """Plan out the steps needed to complete a complex user request."""
    return (f"Planning steps for: {user_request}\n"
           f"1. Identify all requested actions\n"
           f"2. Determine which tools are needed\n"
           f"3. Execute tools in proper sequence\n"
           f"4. Verify all tasks are completed\n"
           f"Remember: Actually use the tools, don't just describe what you would do!")

@tool
def youtube_search(
    query: str,
    max_results: int = 5,
    video_type: str = "video",
    output_format: str = "text"
) -> str:
    """
    Search YouTube for videos, playlists, or channels via the YouTube Data API v3
    with optional structured JSON output.
    """
    # This tool's implementation remains unchanged
    try:
        api_key = os.getenv('YOUTUBE_API_KEY')
        output_format = (output_format or "text").lower()
        if output_format not in {"text", "json"}:
            output_format = "text"

        max_results = max(1, min(int(max_results), 50))
        valid_types = {"video", "playlist", "channel"}
        if video_type not in valid_types:
            video_type = "video"

        if not api_key:
            # Mock data generation remains the same
            mock_items = [
                {"index": 1, "title": "Sample Valorant Montage - Epic Plays", "channel": "ProGamer123", "published": "Unknown", "url": "https://youtube.com/watch?v=sample123", "description": "Amazing valorant highlights and clutch moments...", "kind": "video"},
                {"index": 2, "title": "Best Valorant Montage 2024", "channel": "EsportsHighlights", "published": "Unknown", "url": "https://youtube.com/watch?v=sample456", "description": "Top valorant plays compilation from professional matches...", "kind": "video"}
            ]
            if output_format == "json":
                return json.dumps({"query": query, "type": video_type, "count": len(mock_items), "results": mock_items, "mock": True, "note": "Set YOUTUBE_API_KEY for live results"}, indent=2)
            lines = [f"YouTube Search Results for '{query}' (MOCK DATA - set YOUTUBE_API_KEY for live results):", ""]
            for item in mock_items:
                lines.append(f"{item['index']}. {item['title']}\n   Channel: {item['channel']}\n   Published: {item['published']}\n   URL: {item['url']}\n   Description: {item['description']}")
            return "\n".join(lines)

        # Live API call logic remains the same
        base_url = "https://www.googleapis.com/youtube/v3/search"
        params = {"part": "snippet", "q": query, "type": video_type, "maxResults": max_results, "key": api_key, "order": "relevance"}
        response = requests.get(base_url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        items = data.get("items", [])
        if not items:
            if output_format == "json":
                return json.dumps({"query": query, "type": video_type, "count": 0, "results": []}, indent=2)
            return f"No YouTube results found for query: '{query}'"

        structured_results = []
        text_blocks = [f"YouTube Search Results for '{query}':", ""]
        for idx, item in enumerate(items, 1):
            snippet, id_part = item.get("snippet", {}), item.get("id", {})
            video_id, playlist_id, channel_id = id_part.get("videoId", ""), id_part.get("playlistId", ""), id_part.get("channelId", "")
            if video_id: url, kind = f"https://youtube.com/watch?v={video_id}", "video"
            elif playlist_id: url, kind = f"https://youtube.com/playlist?list={playlist_id}", "playlist"
            elif channel_id: url, kind = f"https://youtube.com/channel/{channel_id}", "channel"
            else: url, kind = "URL not available", "unknown"
            title = snippet.get("title", "No title")
            channel = snippet.get("channelTitle", "Unknown channel")
            description = (snippet.get("description", "No description") or "No description")[:100] + "..."
            published = snippet.get("publishTime", snippet.get("publishedAt", "Unknown date"))
            structured_results.append({"index": idx, "title": title, "channel": channel, "published": published, "url": url, "description": description, "kind": kind})
            if output_format == "text":
                text_blocks.append(f"{idx}. {title}\n   Channel: {channel}\n   Published: {published}\n   URL: {url}\n   Description: {description}")

        if output_format == "json":
            return json.dumps({"query": query, "type": video_type, "count": len(structured_results), "results": structured_results}, indent=2)
        return "\n".join(text_blocks)

    except requests.exceptions.RequestException as e:
        return f"Error making YouTube API request: {e}"
    except Exception as e:
        return f"Error searching YouTube: {e}"


@tool
def chrome_tab_controller(command: str, url: Optional[str] = None, tab_id: Optional[int] = None) -> str:
    """Control Google Chrome tabs by connecting to a WebSocket server."""
    return f"Chrome tab controller executed: {command} (requires WebSocket server)"

@tool
def read_gmail_messages(top=5):
    """Main function to read Gmail messages with all helper functions defined inside"""
    # This tool's implementation remains unchanged
    top = int(top)
    result_string = ""

    def decode_base64_url(data):
        missing_padding = len(data) % 4
        if missing_padding: data += '=' * (4 - missing_padding)
        data = data.replace('-', '+').replace('_', '/')
        try: return base64.b64decode(data).decode('utf-8')
        except: return "[Unable to decode content]"

    def extract_message_body(payload):
        body = ""
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain' and 'data' in part['body']: body += decode_base64_url(part['body']['data'])
                elif 'parts' in part: body += extract_message_body(part)
        elif 'data' in payload.get('body', {}):
            body = decode_base64_url(payload['body']['data'])
        return body

    access_token = get_user_access_token(user_email)
    if not access_token:
        return f"❌ No access token found for {user_email}. Please login first."

    list_url, params = "https://gmail.googleapis.com/gmail/v1/users/me/messages", {"maxResults": top, "labelIds": "INBOX"}
    headers = {"Authorization": f"Bearer {access_token}"}
    list_response = requests.get(list_url, headers=headers, params=params)

    if list_response.status_code != 200:
        return f"Error fetching messages: {list_response.status_code} {list_response.text}"

    messages = list_response.json().get("messages", [])
    result_string += f"Found {len(messages)} messages\n\n"

    for i, msg in enumerate(messages, 1):
        msg_id = msg["id"]
        detail_url = f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{msg_id}"
        detail_response = requests.get(detail_url, headers=headers, params={"format": "full"})
        if detail_response.status_code != 200: continue

        msg_data = detail_response.json()
        headers_list = msg_data.get("payload", {}).get("headers", [])
        email_headers = {h["name"]: h["value"] for h in headers_list}
        subject, sender = email_headers.get("Subject", "(No Subject)"), email_headers.get("From", "(No Sender)")
        body = extract_message_body(msg_data.get("payload", {}))
        snippet = msg_data.get("snippet", "").strip()

        result_string += f"{'='*80}\nMESSAGE {i} - ID: {msg_id}\n{'='*80}\n"
        result_string += f"📧 Subject: {subject}\n👤 From: {sender}\n\n📄 SNIPPET:\n{snippet}\n"
        if body.strip():
            result_string += f"\n📃 FULL BODY:\n{'-'*40}\n" + (body[:1000] + "..." if len(body) > 1000 else body) + "\n"
        result_string += "\n" + "="*80 + "\n\n"

    return result_string

@tool
def send_gmail_message(to: str, title: str, body: str):
    """
    Send an email using Gmail API with a saved OAuth token.
    """
    try:
        access_token = get_user_access_token(user_email)
        if not access_token:
            return f"❌ No access token found for {user_email}. Please login first."

        message = MIMEText(body)
        message["to"], message["subject"] = to, title
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")

        url, headers = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send", {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
        payload = {"raw": raw_message}
        response = requests.post(url, headers=headers, json=payload)

        if response.status_code == 200: return f"✅ Message successfully sent to {to}"
        else: return f"❌ Failed to send message: {response.status_code} {response.text}"
    except Exception as e:
        return f"⚠️ Error sending message: {str(e)}"

# ==============================================================================
#  AGENT AND GRAPH SETUP (No changes needed here)
# ==============================================================================
# Separate tools into safe and sensitive categories
safe_tools = [get_current_time, calculate, get_weather, get_chat_history_summary, task_planner, youtube_search]
sensitive_tools = [read_gmail_messages, send_gmail_message]
sensitive_tool_names = {t.name for t in sensitive_tools}
all_tools = safe_tools + sensitive_tools

def handle_tool_error(state) -> dict:
    error, tool_calls = state.get("error"), state["messages"][-1].tool_calls
    return {"messages": [ToolMessage(content=f"Error: {repr(error)}\nPlease fix your mistakes.", tool_call_id=tc["id"]) for tc in tool_calls]}

def create_tool_node_with_fallback(tools: list):
    from langchain_core.runnables import RunnableLambda
    return ToolNode(tools).with_fallbacks([RunnableLambda(handle_tool_error)], exception_key="error")

def get_user_authorization(tool_calls):
    """Get user authorization for sensitive tool calls"""
    authorized_calls = []
    for tool_call in tool_calls:
        tool_name = tool_call["name"]
        if tool_name in REQUIRES_AUTHORIZATION:
            print(f"\n🔐 AUTHORIZATION REQUIRED for {tool_name}")
            print(f"📋 {REQUIRES_AUTHORIZATION[tool_name]}")
            print(f"🔧 Parameters: {json.dumps(tool_call['args'], indent=2)}")
            AUTH_URL = "http://localhost:9000/"
            data, basic_data = {"tool_name": tool_name, "tool_args": tool_call['args'], "authorization": "null"}, {"tool_name": "default_tool", "tool_args": {}, "authorization": "null"}
            requests.post(AUTH_URL, json=data)
            while True:
                resp = requests.get(AUTH_URL)
                config_data = resp.json()
                if config_data.get("authorization") is not None:
                    auth = config_data["authorization"].upper()
                    if auth == "A":
                        authorized_calls.append(tool_call)
                        requests.post(AUTH_URL, json=basic_data)
                        break
                    elif auth == "D":
                        denied_call = tool_call.copy()
                        denied_call["denied"] = True
                        authorized_calls.append(denied_call)
                        requests.post(AUTH_URL, json=basic_data)
                        break
        else:
            authorized_calls.append(tool_call)
    return authorized_calls

class MixedToolNode:
    """Tool node that handles both safe and sensitive tools in one call"""
    def __init__(self, safe_tools, sensitive_tools):
        self.safe_tools, self.sensitive_tools = {tool.name: tool for tool in safe_tools}, {tool.name: tool for tool in sensitive_tools}
    def __call__(self, state: AgentState):
        last_message = state["messages"][-1]
        if not hasattr(last_message, 'tool_calls') or not last_message.tool_calls:
            return {"messages": state["messages"]}
        safe_calls = [tc for tc in last_message.tool_calls if tc["name"] not in sensitive_tool_names]
        sensitive_calls = [tc for tc in last_message.tool_calls if tc["name"] in sensitive_tool_names]
        results = []
        for tool_call in safe_calls:
            try:
                result_content = self.safe_tools[tool_call["name"]].invoke(tool_call["args"])
                results.append(ToolMessage(content=str(result_content), tool_call_id=tool_call["id"]))
            except Exception as e:
                results.append(ToolMessage(content=f"Error executing {tool_call['name']}: {str(e)}", tool_call_id=tool_call["id"]))
        if sensitive_calls:
            try:
                authorized_calls = get_user_authorization(sensitive_calls)
                for tool_call in authorized_calls:
                    if tool_call.get("denied", False):
                        results.append(ToolMessage(content="Authorization denied by user.", tool_call_id=tool_call["id"]))
                        continue
                    try:
                        result_content = self.sensitive_tools[tool_call["name"]].invoke(tool_call["args"])
                        results.append(ToolMessage(content=str(result_content), tool_call_id=tool_call["id"]))
                    except Exception as e:
                        results.append(ToolMessage(content=f"Error executing {tool_call['name']}: {str(e)}", tool_call_id=tool_call["id"]))
            except Exception as e:
                for tool_call in sensitive_calls:
                    results.append(ToolMessage(content=f"Authorization error: {str(e)}", tool_call_id=tool_call["id"]))
        return {"messages": state["messages"] + results}


def create_agent_graph():
    """Create the LangGraph workflow with authorization"""
    model = setup_model()
    if not model: return None
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are Luna, an intelligent AI assistant powered by Google Gemini. Your role is to be helpful, concise, and use tools only when there is explicit user intent.

        **Tool Usage Policy:**
        1.  **Default to Knowledge:** Answer from your internal knowledge first for general questions.
        2.  **Explicit Intent Required:** Only use a tool if the user's request explicitly asks for an action that requires it (e.g., "what is the time now?", "read my latest email", "search YouTube for...").
        3.  **No Speculation:** Do not run tools based on assumptions. If a request is ambiguous, ask for clarification.
        4.  **Sequential Narration for Multi-Tool Tasks:** For requests requiring multiple tools, narrate the results step-by-step. Example: "The current time is [result 1]. Now, checking your emails. You have a new email about [result 2]."
        5.  **Transparency:** If a tool fails or you don't use one, state it clearly. Never claim to have performed an action you didn't.

        Current time: {time}"""),
        MessagesPlaceholder(variable_name="messages"),
    ]).partial(time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    agent_runnable = prompt | model.bind_tools(all_tools)
    class Assistant:
        def __init__(self, runnable): self.runnable = runnable
        def __call__(self, state: AgentState):
            result = self.runnable.invoke(state)
            return {"messages": [result]}

    workflow = StateGraph(AgentState)
    workflow.add_node("assistant", Assistant(agent_runnable))
    workflow.add_node("tools", MixedToolNode(safe_tools, sensitive_tools))
    workflow.add_edge(START, "assistant")
    workflow.add_conditional_edges("assistant", tools_condition, ["tools", END])
    workflow.add_edge("tools", "assistant")
    return workflow.compile(checkpointer=MemorySaver())

# ==============================================================================
#  MONGODB PERSISTENCE LOGIC (NEW)
# ==============================================================================
def setup_mongodb_client():
    """Initializes and returns the MongoDB client, testing the connection."""
    global db_client
    try:
        client = MongoClient(MONGO_URI, server_api=ServerApi('1'))
        client.admin.command('ping')
        print("✅ Pinged your deployment. You successfully connected to MongoDB!")
        db_client = client
        return client
    except Exception as e:
        print(f"❌ Could not connect to MongoDB: {e}")
        return None

def load_chat_history():
    """Loads the most recent chat session for the current user from MongoDB."""
    global chatmap, session_id, user_email, db_client
    if not user_email or not db_client:
        print("⚠️ Cannot load history, user email or DB client not set.")
        session_id = str(uuid.uuid4()) # Start a new session if we can't load
        return

    print(f"🔄 Loading chat history for {user_email} from MongoDB...")

    # Connect to the two separate databases
    db1 = db_client[METADATA_DB_NAME]
    db2 = db_client[CHATS_DB_NAME]

    metadata_collection = db1[METADATA_COLLECTION_NAME]
    chats_collection = db2[CHATS_COLLECTION_NAME]

    # Find the latest session_id for the user from db1
    user_metadata = metadata_collection.find_one({"_id": user_email})

    latest_session_id = None
    if user_metadata and user_metadata.get("sessions"):
        # Find the session with the latest 'last_updated' timestamp
        latest_session_info = max(user_metadata["sessions"], key=lambda s: s["last_updated"])
        latest_session_id = latest_session_info["session_id"]
        print(f"✅ Found latest session metadata in '{METADATA_DB_NAME}': {latest_session_id[:8]}...")

    if latest_session_id:
        # Now, get the actual chat data from db2
        session_data = chats_collection.find_one({"_id": latest_session_id})
        if session_data and "messages" in session_data:
            history = InMemoryChatMessageHistory()
            for msg in session_data["messages"]:
                if msg['type'] == 'human':
                    history.add_message(HumanMessage(content=msg['content']))
                else:
                    history.add_message(AIMessage(content=msg['content']))
            chatmap[latest_session_id] = history
            session_id = latest_session_id
            print(f"✅ Loaded {len(session_data['messages'])} messages from '{CHATS_DB_NAME}' for session {session_id[:8]}...")
            return

    # If no session was found or loaded, start a new one
    print("📝 No previous sessions found for this user. Starting a new one.")
    session_id = str(uuid.uuid4())
    chatmap[session_id] = InMemoryChatMessageHistory()

def save_chat_history():
    """Saves the current chat session to the correct MongoDB databases."""
    global chatmap, session_id, user_email, db_client
    if not all([session_id, user_email, db_client, session_id in chatmap]):
        return

    # Connect to the two separate databases
    db1 = db_client[METADATA_DB_NAME]
    db2 = db_client[CHATS_DB_NAME]

    metadata_collection = db1[METADATA_COLLECTION_NAME]
    chats_collection = db2[CHATS_COLLECTION_NAME]

    # 1. Save the chat messages to db2.sessionid_chats
    current_messages = []
    for msg in chatmap[session_id].messages:
        current_messages.append({
            'type': msg.type,
            'content': msg.content,
            'timestamp': datetime.now().isoformat()
        })

    if not current_messages: # Don't save empty chat sessions
        return

    chats_collection.update_one(
        {"_id": session_id},
        {"$set": {
            "messages": current_messages,
            "user_email": user_email,
            "last_updated": datetime.now()
        },
         "$setOnInsert": {"created_at": datetime.now()}
        },
        upsert=True
    )

    # 2. Update the user's session metadata in db1.user_sessionid
    # First, pull the existing session info to avoid duplicates
    metadata_collection.update_one(
        {"_id": user_email},
        {"$pull": {"sessions": {"session_id": session_id}}}
    )
    # Then, add the updated session info to the top of the list
    metadata_collection.update_one(
        {"_id": user_email},
        {
            "$push": {
                "sessions": {
                    "$each": [{"session_id": session_id, "last_updated": datetime.now()}],
                    "$sort": {"last_updated": -1} # Sort to keep the most recent at the top
                }
            },
            "$setOnInsert": {"email": user_email}
        },
        upsert=True
    )
    print(f"💾 Saved session {session_id[:8]} to MongoDB ({METADATA_DB_NAME} & {CHATS_DB_NAME}).")


# ==============================================================================
#  APPLICATION LOGIC
# ==============================================================================
def setup_model():
    """Initialize the Gemini model"""
    api_key = os.getenv("MODEL_API_KEY")
    if not api_key:
        print("❌ MODEL_API_KEY not found in environment")
        return None
    try:
        model = ChatGoogleGenerativeAI(
            model=os.getenv("MODEL_NAME", "gemini-1.5-flash"),
            temperature=float(os.getenv("TEMPERATURE", "0.3")),
            google_api_key=api_key,
            convert_system_message_to_human=True
        )
        print(f"✅ Model initialized: {os.getenv('MODEL_NAME', 'gemini-1.5-flash')}")
        return model
    except Exception as e:
        print(f"❌ Error initializing model: {e}")
        return None

def print_welcome():
    """Print welcome message"""
    global session_id, user_email
    sid_display = (session_id[:8] + "...") if session_id and len(session_id) >= 8 else "N/A"
    print("\n" + "="*60)
    print("🤖 LUNA AGENT WITH MONGODB PERSISTENCE")
    print("="*60)
    print(f"👤 User: {user_email}")
    print(f"📱 Session ID: {sid_display}")
    print("💡 Commands: /help, /history, /clear, /quit, /new")
    print("="*60 + "\n")

def print_help():
    """Print help message"""
    print("\n📚 AVAILABLE COMMANDS:")
    print("  /help     - Show this help message")
    print("  /new      - Start a new chat session")
    print("  /clear    - Clear current session's chat history")
    print("  /quit     - Exit the application")
    print()

def run_chat_loop(app):
    """Interactive chat loop with MongoDB auto-save"""
    global session_id, chatmap
    config = {"configurable": {"thread_id": session_id}}

    try:
        while True:
            try:
                user_input = input("🧑 You: ").strip()
            except EOFError:
                print("\n👋 Goodbye!")
                break

            if not user_input: continue

            if user_input.startswith('/'):
                command = user_input.lower()
                if command in ('/quit', '/exit'): break
                elif command == '/help': print_help()
                elif command == '/clear':
                    if session_id in chatmap: chatmap[session_id].clear()
                    print("🗑️ Current session history cleared!")
                    save_chat_history()
                elif command == '/new':
                    save_chat_history() # Save current session first
                    session_id = str(uuid.uuid4())
                    chatmap[session_id] = InMemoryChatMessageHistory()
                    config = {"configurable": {"thread_id": session_id}}
                    print(f"🆕 Started new session: {session_id[:8]}...")
                else:
                    print("❌ Unknown command. Type /help for options.")
                continue

            print("🤖 AI: ", end="", flush=True)

            try:
                final_state = None
                for event in app.stream({"messages": [HumanMessage(content=user_input)]}, config, stream_mode="values"):
                    final_state = event

                if final_state and final_state.get("messages"):
                    last_message = final_state["messages"][-1]
                    if hasattr(last_message, 'content') and last_message.content:
                        print(last_message.content)
                        if session_id not in chatmap: chatmap[session_id] = InMemoryChatMessageHistory()
                        chatmap[session_id].add_message(HumanMessage(content=user_input))
                        chatmap[session_id].add_message(AIMessage(content=last_message.content))
            except Exception as e:
                print(f"\nAn error occurred during agent execution: {e}")

            print()
            save_chat_history() # AUTO-SAVE after every interaction

    except KeyboardInterrupt:
        print("\n\n👋 Chat interrupted.")
    finally:
        save_chat_history()
        save_readline_history()
        print("👋 Goodbye! Your session has been saved.")

def main():
    """Entry point with MongoDB integration"""
    global user_email
    load_dotenv(override=False)

    if not os.getenv("MODEL_API_KEY"):
        print("⚠️ MODEL_API_KEY not found. Please set it in your .env file.")
        sys.exit(1)

    # 1. Connect to MongoDB
    if not setup_mongodb_client():
        sys.exit(1)

    # 2. Get user email
    while not user_email:
        user_email = input("📧 Please enter your email to load/save chat history: ").strip().lower()
        if not user_email: print("Email cannot be empty.")

    setup_readline()

    # 3. Load history from MongoDB
    load_chat_history()

    # 4. Create the agent graph
    app = create_agent_graph()
    if not app:
        print("❌ Failed to initialize the agent. Check your API key.")
        sys.exit(1)

    print_welcome()
    run_chat_loop(app)
    sys.exit(0)

if __name__ == "__main__":
    main()
