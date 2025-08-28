import os
import sys
import uuid
import json
import requests
import subprocess
import asyncio
import websockets
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
current_api_session_id = None


# --- ENHANCED PERSISTENCE PATHS (Legacy, for command history only) ---
PROJECT_ROOT = Path("./")
COMMAND_HISTORY_FILE = PROJECT_ROOT / "langchain_chat_history.json"

# Ensure directories exist for command history
PROJECT_ROOT.mkdir(exist_ok=True)


# Authorization settings - tools that require user permission
REQUIRES_AUTHORIZATION = {
    "read_gmail_messages": "This will read your Gmail messages. Do you want to proceed?",
    "send_gmail_message": "This will send a gmail to the appopriate authority, Fo you want to proceed",
    "create_calendar_event": "This will create a calendar event. Do you want to proceed?",
    "update_calendar_event": "This will update a calendar event. Do you want to proceed?",
    "delete_calendar_event": "This will delete a calendar event. Do you want to proceed?",
    "create_meet_space": "This will create a meet space. Do you want to proceed?",
    "end_meet_space": "This will end a meet space. Do you want to proceed?"
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
def chrome_tab_controller(
    command: str,
    url: Optional[str] = None,
    tab_id: Optional[int] = None
) -> str:
    """
    Control Google Chrome tabs by connecting to a WebSocket server.

    Args:
        command (str): The action to perform. One of:
            - 'list_tabs': List all open tabs.
            - 'open_tab': Open a new tab. Requires 'url'.
            - 'close_tab': Close a specific tab. Requires 'tab_id'.
            - 'switch_tab': Switch to a specific tab. Requires 'tab_id'.
            - 'reload_tab': Reload a specific tab. Requires 'tab_id'.
            - 'navigate_tab': Navigate a tab to a new URL. Requires 'tab_id' and 'url'.
        url (Optional[str]): The URL to use for 'open_tab' or 'navigate_tab'.
        tab_id (Optional[int]): The ID of the tab for 'close_tab', 'switch_tab', 'reload_tab', or 'navigate_tab'.

    Returns:
        str: A success message, a list of tabs, or an error message as a JSON string.

    Notes:
        - This tool requires a running WebSocket server at 'ws://localhost:8765/ws'.
        - If the server is not running, it will return a connection error.
    """
    class ChromeTabControllerClient:
        def __init__(self, server_url='ws://localhost:8765/ws'):
            self.server_url = server_url
            self.websocket = None
            self.pending_requests = {}

        async def connect(self):
            self.websocket = await websockets.connect(self.server_url)
            await self.websocket.send(json.dumps({'type': 'role', 'role': 'client'}))
            asyncio.create_task(self._message_handler())

        async def _message_handler(self):
            try:
                async for message in self.websocket:
                    data = json.loads(message)
                    request_id = data.get('id')
                    if request_id in self.pending_requests:
                        future = self.pending_requests.pop(request_id)
                        future.set_result(data)
            except websockets.exceptions.ConnectionClosed:
                pass # Connection closed as expected

        async def _send_command(self, cmd: str, payload: Dict = None) -> Dict[str, Any]:
            if not self.websocket:
                raise ConnectionError("Not connected to server")
            request_id = str(uuid.uuid4())
            future = asyncio.Future()
            self.pending_requests[request_id] = future
            message = {'type': 'command', 'id': request_id, 'command': cmd, 'payload': payload or {}}
            await self.websocket.send(json.dumps(message))
            try:
                return await asyncio.wait_for(future, timeout=10.0)
            except asyncio.TimeoutError:
                self.pending_requests.pop(request_id, None)
                return {'error': 'Request timeout'}

        async def list_tabs(self):
            return await self._send_command('list_tabs')

        async def open_tab(self, target_url: str, active: bool = True):
            return await self._send_command('open_tab', {'url': target_url, 'active': active})

        async def close_tab(self, target_tab_id: int):
            return await self._send_command('close_tab', {'tabId': target_tab_id})

        async def switch_tab(self, target_tab_id: int):
            return await self._send_command('switch_tab', {'tabId': target_tab_id})

        async def reload_tab(self, target_tab_id: int):
            return await self._send_command('reload_tab', {'tabId': target_tab_id})

        async def navigate_tab(self, target_tab_id: int, target_url: str):
            return await self._send_command('navigate_tab', {'tabId': target_tab_id, 'url': target_url})

        async def disconnect(self):
            if self.websocket:
                await self.websocket.close()

    # FIX: Pass arguments explicitly to the async function
    async def run_command_async(cmd, target_url, target_tab_id):
        controller = ChromeTabControllerClient()
        try:
            await controller.connect()
            command_lower = cmd.lower()
            response = None

            if command_lower == 'list_tabs':
                response = await controller.list_tabs()
            elif command_lower == 'open_tab':
                if not target_url: return {"error": "URL is required for open_tab"}
                if not target_url.startswith(('http://', 'https://')):
                    target_url = 'https://' + target_url
                response = await controller.open_tab(target_url)
            elif command_lower == 'close_tab':
                if target_tab_id is None: return {"error": "tab_id is required for close_tab"}
                response = await controller.close_tab(target_tab_id)
            elif command_lower == 'switch_tab':
                if target_tab_id is None: return {"error": "tab_id is required for switch_tab"}
                response = await controller.switch_tab(target_tab_id)
            elif command_lower == 'reload_tab':
                if target_tab_id is None: return {"error": "tab_id is required for reload_tab"}
                response = await controller.reload_tab(target_tab_id)
            elif command_lower == 'navigate_tab':
                if target_tab_id is None or not target_url: return {"error": "tab_id and url are required for navigate_tab"}
                if not target_url.startswith(('http://', 'https://')):
                    target_url = 'https://' + target_url
                response = await controller.navigate_tab(target_tab_id, target_url)
            else:
                valid_cmds = "list_tabs, open_tab, close_tab, switch_tab, reload_tab, navigate_tab"
                return json.dumps({"error": f"Unknown command '{cmd}'. Valid commands are: {valid_cmds}."}, indent=2)

            return json.dumps(response, indent=2)
        finally:
            await controller.disconnect()

    try:
        # FIX: Pass the arguments from the tool's scope into the async runner
        return asyncio.run(run_command_async(command, url, tab_id))
    except ConnectionRefusedError:
        return json.dumps({"error": "Connection refused. Is the Chrome Tab Controller server running?"}, indent=2)
    except Exception as e:
        return json.dumps({"error": f"An unexpected error occurred: {e}"}, indent=2)


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

@tool
def create_calendar_event(
    summary: str,
    start_datetime: str,
    end_datetime: str,
    description: Optional[str] = None,
    location: Optional[str] = None,
    attendees: Optional[str] = None,
    timezone: str = "UTC",
    calendar_id: str = "primary"
) -> str:
    """
    Create a new Google Calendar event.

    Args:
        summary: Event title/summary (required)
        start_datetime: Start time in ISO format (YYYY-MM-DDTHH:MM:SS) or YYYY-MM-DD for all-day
        end_datetime: End time in ISO format (YYYY-MM-DDTHH:MM:SS) or YYYY-MM-DD for all-day
        description: Event description (optional)
        location: Event location (optional)
        attendees: Comma-separated email addresses (optional)
        timezone: Timezone (default: UTC)
        calendar_id: Calendar ID (default: primary)

    Example:
        create_calendar_event("Team Meeting", "2024-01-15T14:00:00", "2024-01-15T15:00:00",
                             description="Weekly sync", attendees="john@example.com,jane@example.com")
    """
    try:
        access_token = get_user_access_token(user_email)
        if not access_token:
            return f"❌ No access token found for {user_email}. Please login first."

        # Parse datetime and determine if all-day event
        is_all_day = len(start_datetime) == 10  # YYYY-MM-DD format

        if is_all_day:
            start_time = {"date": start_datetime}
            end_time = {"date": end_datetime}
        else:
            start_time = {"dateTime": start_datetime, "timeZone": timezone}
            end_time = {"dateTime": end_datetime, "timeZone": timezone}

        # Build event object
        event = {
            "summary": summary,
            "start": start_time,
            "end": end_time
        }

        if description:
            event["description"] = description

        if location:
            event["location"] = location

        if attendees:
            attendee_list = [{"email": email.strip()} for email in attendees.split(",")]
            event["attendees"] = attendee_list

        # Make API request
        url = f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        response = requests.post(url, headers=headers, json=event)

        if response.status_code == 200:
            result = response.json()
            event_link = result.get("htmlLink", "No link available")
            return f"✅ Calendar event created successfully!\n📅 Title: {summary}\n🔗 Link: {event_link}\n📍 Event ID: {result.get('id')}"
        else:
            return f"❌ Failed to create calendar event: {response.status_code} {response.text}"

    except Exception as e:
        return f"⚠️ Error creating calendar event: {str(e)}"


@tool
def list_calendar_events(
    time_min: Optional[str] = None,
    time_max: Optional[str] = None,
    max_results: int = 10,
    calendar_id: str = "primary",
    order_by: str = "startTime"
) -> str:
    """
    List Google Calendar events.

    Args:
        time_min: Lower bound for event start time (ISO format, optional - defaults to now)
        time_max: Upper bound for event start time (ISO format, optional - defaults to 1 week from now)
        max_results: Maximum number of events to return (1-250, default: 10)
        calendar_id: Calendar ID (default: primary)
        order_by: Order results by 'startTime' or 'updated' (default: startTime)

    Example:
        list_calendar_events(max_results=5)
        list_calendar_events(time_min="2024-01-15T00:00:00Z", time_max="2024-01-20T23:59:59Z")
    """
    try:
        access_token = get_user_access_token(user_email)
        if not access_token:
            return f"❌ No access token found for {user_email}. Please login first."

        # Set default time range if not provided
        if not time_min:
            time_min = datetime.utcnow().isoformat() + 'Z'
        if not time_max:
            time_max = (datetime.utcnow() + timedelta(days=7)).isoformat() + 'Z'

        # Build parameters
        params = {
            "timeMin": time_min,
            "timeMax": time_max,
            "maxResults": min(max_results, 250),
            "singleEvents": "true",
            "orderBy": order_by
        }

        url = f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events"
        headers = {"Authorization": f"Bearer {access_token}"}

        response = requests.get(url, headers=headers, params=params)

        if response.status_code != 200:
            return f"❌ Failed to fetch calendar events: {response.status_code} {response.text}"

        events = response.json().get("items", [])

        if not events:
            return "📅 No events found in the specified time range."

        result_string = f"📅 Found {len(events)} calendar events:\n\n"

        for i, event in enumerate(events, 1):
            title = event.get("summary", "(No Title)")
            event_id = event.get("id", "Unknown")

            # Handle start time
            start = event.get("start", {})
            if "dateTime" in start:
                start_time = start["dateTime"]
                event_type = "📍 Timed Event"
            else:
                start_time = start.get("date", "Unknown")
                event_type = "📅 All-day Event"

            # Handle end time
            end = event.get("end", {})
            if "dateTime" in end:
                end_time = end["dateTime"]
            else:
                end_time = end.get("date", "Unknown")

            description = event.get("description", "")[:200] + ("..." if len(event.get("description", "")) > 200 else "")
            location = event.get("location", "")
            attendees = event.get("attendees", [])
            attendee_emails = [att.get("email", "") for att in attendees]

            result_string += f"{'='*60}\n"
            result_string += f"📋 EVENT {i} - ID: {event_id}\n"
            result_string += f"{'='*60}\n"
            result_string += f"📝 Title: {title}\n"
            result_string += f"⏰ Type: {event_type}\n"
            result_string += f"🕐 Start: {start_time}\n"
            result_string += f"🕑 End: {end_time}\n"

            if location:
                result_string += f"📍 Location: {location}\n"
            if attendee_emails:
                result_string += f"👥 Attendees: {', '.join(attendee_emails)}\n"
            if description:
                result_string += f"📄 Description: {description}\n"

            result_string += f"🔗 Link: {event.get('htmlLink', 'No link')}\n\n"

        return result_string

    except Exception as e:
        return f"⚠️ Error listing calendar events: {str(e)}"


@tool
def update_calendar_event(
    event_id: str,
    summary: Optional[str] = None,
    start_datetime: Optional[str] = None,
    end_datetime: Optional[str] = None,
    description: Optional[str] = None,
    location: Optional[str] = None,
    attendees: Optional[str] = None,
    timezone: str = "UTC",
    calendar_id: str = "primary"
) -> str:
    """
    Update an existing Google Calendar event.

    Args:
        event_id: The ID of the event to update (required)
        summary: New event title/summary (optional)
        start_datetime: New start time in ISO format (optional)
        end_datetime: New end time in ISO format (optional)
        description: New event description (optional)
        location: New event location (optional)
        attendees: New comma-separated email addresses (optional)
        timezone: Timezone (default: UTC)
        calendar_id: Calendar ID (default: primary)

    Example:
        update_calendar_event("event123", summary="Updated Meeting Title", location="Conference Room B")
    """
    try:
        access_token = get_user_access_token(user_email)
        if not access_token:
            return f"❌ No access token found for {user_email}. Please login first."

        # First, get the existing event
        url = f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events/{event_id}"
        headers = {"Authorization": f"Bearer {access_token}"}

        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            return f"❌ Failed to fetch event: {response.status_code} {response.text}"

        event = response.json()

        # Update only provided fields
        if summary is not None:
            event["summary"] = summary

        if start_datetime is not None:
            is_all_day = len(start_datetime) == 10
            if is_all_day:
                event["start"] = {"date": start_datetime}
            else:
                event["start"] = {"dateTime": start_datetime, "timeZone": timezone}

        if end_datetime is not None:
            is_all_day = len(end_datetime) == 10
            if is_all_day:
                event["end"] = {"date": end_datetime}
            else:
                event["end"] = {"dateTime": end_datetime, "timeZone": timezone}

        if description is not None:
            event["description"] = description

        if location is not None:
            event["location"] = location

        if attendees is not None:
            attendee_list = [{"email": email.strip()} for email in attendees.split(",")]
            event["attendees"] = attendee_list

        # Update the event
        response = requests.put(url, headers={**headers, "Content-Type": "application/json"}, json=event)

        if response.status_code == 200:
            result = response.json()
            return f"✅ Calendar event updated successfully!\n📅 Title: {result.get('summary')}\n🔗 Link: {result.get('htmlLink')}"
        else:
            return f"❌ Failed to update calendar event: {response.status_code} {response.text}"

    except Exception as e:
        return f"⚠️ Error updating calendar event: {str(e)}"


@tool
def delete_calendar_event(event_id: str, calendar_id: str = "primary") -> str:
    """
    Delete a Google Calendar event.

    Args:
        event_id: The ID of the event to delete (required)
        calendar_id: Calendar ID (default: primary)

    Example:
        delete_calendar_event("event123")
    """
    try:
        access_token = get_user_access_token(user_email)
        if not access_token:
            return f"❌ No access token found for {user_email}. Please login first."

        url = f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events/{event_id}"
        headers = {"Authorization": f"Bearer {access_token}"}

        response = requests.delete(url, headers=headers)

        if response.status_code == 204:
            return f"✅ Calendar event deleted successfully! Event ID: {event_id}"
        elif response.status_code == 404:
            return f"❌ Event not found: {event_id}"
        else:
            return f"❌ Failed to delete calendar event: {response.status_code} {response.text}"

    except Exception as e:
        return f"⚠️ Error deleting calendar event: {str(e)}"


@tool
def create_meet_space(
    display_name: Optional[str] = None,
    description: Optional[str] = None
) -> str:
    """
    Create a new Google Meet space.

    Args:
        display_name: Display name for the Meet space (optional)
        description: Description for the Meet space (optional)

    Example:
        create_meet_space("Team Standup", "Daily team sync meeting")
    """
    try:
        access_token = get_user_access_token(user_email)
        if not access_token:
            return f"❌ No access token found for {user_email}. Please login first."

        # Build space object
        space = {}
        if display_name:
            space["displayName"] = display_name
        if description:
            space["description"] = description

        url = "https://meet.googleapis.com/v2/spaces"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        response = requests.post(url, headers=headers, json=space)

        if response.status_code == 200:
            result = response.json()
            space_name = result.get("name", "Unknown")
            meeting_uri = result.get("meetingUri", "No URI available")
            meeting_code = result.get("meetingCode", "No code available")

            return f"✅ Google Meet space created successfully!\n📹 Space Name: {space_name}\n🔗 Meeting URI: {meeting_uri}\n🔢 Meeting Code: {meeting_code}\n📝 Display Name: {result.get('displayName', 'Not set')}"
        else:
            return f"❌ Failed to create Meet space: {response.status_code} {response.text}"

    except Exception as e:
        return f"⚠️ Error creating Meet space: {str(e)}"


@tool
def get_meet_space(space_name: str) -> str:
    """
    Get information about a Google Meet space.

    Args:
        space_name: The name/ID of the Meet space (required)
                   Format: "spaces/{space_id}" or just the space_id

    Example:
        get_meet_space("spaces/abc123def")
        get_meet_space("abc123def")
    """
    try:
        access_token = get_user_access_token(user_email)
        if not access_token:
            return f"❌ No access token found for {user_email}. Please login first."

        # Ensure proper format
        if not space_name.startswith("spaces/"):
            space_name = f"spaces/{space_name}"

        url = f"https://meet.googleapis.com/v2/{space_name}"
        headers = {"Authorization": f"Bearer {access_token}"}

        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            result = response.json()

            space_info = f"📹 Google Meet Space Information:\n"
            space_info += f"{'='*50}\n"
            space_info += f"🏷️ Space Name: {result.get('name', 'Unknown')}\n"
            space_info += f"📝 Display Name: {result.get('displayName', 'Not set')}\n"
            space_info += f"📄 Description: {result.get('description', 'Not set')}\n"
            space_info += f"🔗 Meeting URI: {result.get('meetingUri', 'Not available')}\n"
            space_info += f"🔢 Meeting Code: {result.get('meetingCode', 'Not available')}\n"

            config = result.get('config', {})
            if config:
                space_info += f"⚙️ Configuration:\n"
                space_info += f"  🎥 Entry Point Access: {config.get('entryPointAccess', 'Unknown')}\n"
                space_info += f"  🔐 Access Type: {config.get('accessType', 'Unknown')}\n"

            active_conference = result.get('activeConference', {})
            if active_conference:
                space_info += f"🔴 Active Conference:\n"
                space_info += f"  📛 Conference Record: {active_conference.get('conferenceRecord', 'None')}\n"
            else:
                space_info += f"⚪ No active conference\n"

            return space_info
        else:
            return f"❌ Failed to get Meet space: {response.status_code} {response.text}"

    except Exception as e:
        return f"⚠️ Error getting Meet space: {str(e)}"

@tool
def update_thought_process(step: str):
    """
    Call this tool at every step of your process to update the user on your current thought or action.
    This is your way of 'thinking out loud'. Always call this before using any other tool.

    Example Usage:
    - update_thought_process(step="Analyzing the user's request...")
    - update_thought_process(step="Planning to use the read_gmail_messages tool...")
    - update_thought_process(step="Summarizing the results...")
    """
    try:
        # This tool makes a simple, non-critical POST request to our new Thoughts Server.
        # We use a short timeout because we don't want this to slow down the agent.
        # If it fails, it's not a big deal; the agent's main task can continue.
        response = requests.post(
            "http://localhost:8001/thought",
            json={"step": step}, # Send the thought as a JSON payload
            timeout=2 # 2-second timeout
        )
        # Check if the request was successful
        if response.status_code == 200:
            print(f"✅ Thought sent successfully: '{step}'")
        else:
            print(f"⚠️ Warning: Failed to send thought. Server responded with {response.status_code}")

    except requests.RequestException as e:
        # This will catch connection errors, timeouts, etc.
        print(f"⚠️ Warning: Could not send thought to the thoughts_server: {e}")

    # It is important that this tool returns a confirmation message back to the agent,
    # so the agent knows the action was acknowledged and can move on.
    return f"Successfully updated the user with the current step: {step}"


@tool
def end_meet_space(space_name: str) -> str:
    """
    End an active Google Meet space.

    Args:
        space_name: The name/ID of the Meet space to end (required)
                   Format: "spaces/{space_id}" or just the space_id

    Example:
        end_meet_space("spaces/abc123def")
        end_meet_space("abc123def")
    """
    try:
        access_token = get_user_access_token(user_email)
        if not access_token:
            return f"❌ No access token found for {user_email}. Please login first."

        # Ensure proper format
        if not space_name.startswith("spaces/"):
            space_name = f"spaces/{space_name}"

        url = f"https://meet.googleapis.com/v2/{space_name}:endActiveConference"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        response = requests.post(url, headers=headers, json={})

        if response.status_code == 200:
            return f"✅ Google Meet space ended successfully!\n📹 Space: {space_name}"
        elif response.status_code == 404:
            return f"❌ Meet space not found: {space_name}"
        else:
            return f"❌ Failed to end Meet space: {response.status_code} {response.text}"

    except Exception as e:
        return f"⚠️ Error ending Meet space: {str(e)}"


@tool
def list_calendar_list() -> str:
    """
    List all calendars accessible to the user.

    Example:
        list_calendar_list()
    """
    try:
        access_token = get_user_access_token(user_email)
        if not access_token:
            return f"❌ No access token found for {user_email}. Please login first."

        url = "https://www.googleapis.com/calendar/v3/users/me/calendarList"
        headers = {"Authorization": f"Bearer {access_token}"}

        response = requests.get(url, headers=headers)

        if response.status_code != 200:
            return f"❌ Failed to fetch calendar list: {response.status_code} {response.text}"

        calendars = response.json().get("items", [])

        if not calendars:
            return "📅 No calendars found."

        result_string = f"📅 Found {len(calendars)} calendars:\n\n"

        for i, calendar in enumerate(calendars, 1):
            calendar_id = calendar.get("id", "Unknown")
            summary = calendar.get("summary", "No Title")
            description = calendar.get("description", "")
            access_role = calendar.get("accessRole", "Unknown")
            primary = " (PRIMARY)" if calendar.get("primary", False) else ""

            result_string += f"📋 Calendar {i}{primary}:\n"
            result_string += f"   📛 ID: {calendar_id}\n"
            result_string += f"   📝 Summary: {summary}\n"
            result_string += f"   🔐 Access Role: {access_role}\n"
            if description:
                result_string += f"   📄 Description: {description}\n"
            result_string += f"   🌈 Background Color: {calendar.get('backgroundColor', 'Not set')}\n\n"

        return result_string

    except Exception as e:
        return f"⚠️ Error listing calendars: {str(e)}"



safe_tools = [get_current_time, calculate, get_chat_history_summary, task_planner, youtube_search, list_calendar_events, get_meet_space, list_calendar_list,chrome_tab_controller,update_thought_process]
sensitive_tools = [read_gmail_messages, send_gmail_message,create_calendar_event,update_calendar_event, delete_calendar_event,create_meet_space, end_meet_space]
sensitive_tool_names = {t.name for t in sensitive_tools}
all_tools = safe_tools + sensitive_tools

def handle_tool_error(state) -> dict:
    error, tool_calls = state.get("error"), state["messages"][-1].tool_calls
    return {"messages": [ToolMessage(content=f"Error: {repr(error)}\nPlease fix your mistakes.", tool_call_id=tc["id"]) for tc in tool_calls]}

def create_tool_node_with_fallback(tools: list):
    from langchain_core.runnables import RunnableLambda
    return ToolNode(tools).with_fallbacks([RunnableLambda(handle_tool_error)], exception_key="error")


# In test.py

def get_user_authorization(tool_calls):
    """⭐ UPDATED to handle user-modified tool arguments from the auth server."""
    global current_api_session_id

    if not current_api_session_id:
        raise Exception("Authorization failed: API Session ID not found.")

    authorized_calls = []
    AUTH_BASE_URL = "http://localhost:9000/auth"

    for tool_call in tool_calls:
        tool_name = tool_call["name"]
        if tool_name in REQUIRES_AUTHORIZATION:
            print(f"\n🔐 AUTHORIZATION REQUIRED for {tool_name} in session {current_api_session_id}")

            # 1. Post the request (no change here)
            request_payload = {
                "session_id": current_api_session_id,
                "tool_name": tool_name,
                "tool_args": tool_call['args']
            }
            try:
                requests.post(f"{AUTH_BASE_URL}/request", json=request_payload, timeout=5)
            except requests.RequestException as e:
                denied_call = tool_call.copy()
                denied_call["denied"] = True
                authorized_calls.append(denied_call)
                continue

            # 2. Poll for the result (no change here)
            start_time = time.time()
            timeout_seconds = 120 # Increased timeout for user modification
            final_auth_data = None

            while time.time() - start_time < timeout_seconds:
                try:
                    resp = requests.get(f"{AUTH_BASE_URL}/status/{current_api_session_id}", timeout=5)
                    if resp.status_code == 200:
                        status_data = resp.json()
                        if status_data.get("authorization") is not None:
                            final_auth_data = status_data
                            break
                except requests.RequestException as e:
                    print(f"Error polling auth status: {e}")

                time.sleep(1)

            # 3. ⭐ Process the decision, checking for modified arguments
            if final_auth_data and final_auth_data.get("authorization") == "A":
                print("User approved the action.")

                # Create a copy of the original tool call to modify
                approved_call = tool_call.copy()

                # Check if the user provided new arguments
                if final_auth_data.get("tool_args"):
                    print("Applying user modifications to tool arguments.")
                    # Update the arguments with the user's changes
                    approved_call["args"] = final_auth_data["tool_args"]

                authorized_calls.append(approved_call)
            else:
                if not final_auth_data:
                    print("Authorization timed out. Denying tool call.")
                else:
                    print("User denied the action.")
                denied_call = tool_call.copy()
                denied_call["denied"] = True
                authorized_calls.append(denied_call)
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
        ("system", """You are Luna, an advanced AI assistant powered by Google Gemini with comprehensive productivity and automation capabilities. You have access to a powerful suite of tools for managing emails, calendars, meetings, files, web content, and system operations.

**⭐ CRITICAL NEW RULE: NARRATE YOUR ACTIONS ⭐**
        Your HIGHEST PRIORITY is to be transparent with the user. Before you perform any significant action or call any other tool, you MUST first call the `update_thought_process` tool to explain what you are about to do. This is how you "think out loud."

        **CORRECT WORKFLOW EXAMPLE:**
        User: "Read my latest email and tell me the summary."

        1.  **Your First Action:** Call `update_thought_process(step="Analyzing the request to read an email...")`
        2.  **Your Second Action:** Call `update_thought_process(step="Planning to use the `read_gmail_messages` tool...")`
        3.  **Your Third Action:** Call the actual tool, `read_gmail_messages(top=1)`
        4.  **(After getting the tool's result back)**
        5.  **Your Fourth Action:** Call `update_thought_process(step="Summarizing the email content...")`
        6.  **Your Final Action:** Provide the final summary to the user.

        **INCORRECT WORKFLOW:**
        User: "Read my latest email."
        - Calling `read_gmail_messages(top=1)` immediately. <== THIS IS WRONG. You forgot to think out loud first.

        Always, always call `update_thought_process` to narrate your plan and your actions as you perform them. This is not optional.

**🎯 CORE IDENTITY:**
- **Name**: Luna - Your intelligent productivity companion
- **Personality**: Professional, helpful, proactive, and detail-oriented
- **Goal**: Maximize user productivity through intelligent automation and seamless task management

  REMEBER WHEN THE VERIFICATION FAILS FOR ANY SENTITIVE TOOLS AND USER TELLS YOU TO DO IT AGAIN , YOU NEED TO DO IT AGAIN,
  DONT TELL THE USER THAT YOU THAT IT CANT BE DONE,JUST CALL THE TOOL AGAIN.

**🛠️ AVAILABLE TOOL CATEGORIES:**

**📧 EMAIL MANAGEMENT (Gmail API)**
- `read_gmail_messages`: Read and analyze Gmail messages with detailed content extraction
- `send_gmail_message`: Compose and send professional emails to any recipient

**📅 CALENDAR MANAGEMENT (Google Calendar API)**
- `create_calendar_event`: Create meetings, appointments, and events with full details
- `list_calendar_events`: View upcoming events with filtering and date range options
- `update_calendar_event`: Modify existing events (time, location, attendees, etc.)
- `delete_calendar_event`: Remove events from calendar
- `list_calendar_list`: View all available calendars

**🎥 MEETING MANAGEMENT (Google Meet API)**
- `create_meet_space`: Generate new Meet rooms for video conferences
- `get_meet_space`: Retrieve meeting details, links, and status
- `end_meet_space`: Terminate active meeting sessions

**💻 SYSTEM & FILE OPERATIONS**
- `file_operations`: Read, write, and list files in current directory (secure sandbox)
- `run_command`: Execute safe shell commands (ls, pwd, date, etc.)
- `get_current_time`: Get precise current date and time
- `calculate`: Perform mathematical calculations safely

**🌐 WEB & CONTENT TOOLS**
- `youtube_search`: Search YouTube for videos, channels, and playlists with detailed results
- `chrome_tab_controller`: Control browser tabs (requires WebSocket server)
- `get_weather`: Get weather information for any city

**🧠 PRODUCTIVITY & ANALYSIS**
- `task_planner`: Break down complex requests into actionable steps
- `get_chat_history_summary`: Analyze conversation context and history

**⚡ INTELLIGENT TOOL USAGE POLICY:**

**1. PROACTIVE ASSISTANCE**
- Anticipate user needs based on context and time patterns
- Suggest relevant actions (e.g., "Shall I schedule this as a calendar event?")
- Combine multiple tools intelligently for complex workflows

**2. SMART AUTOMATION WORKFLOWS**
- **Meeting Setup**: Create calendar event → Generate Meet space → Send invites → Confirm details
- **Email Management**: Read messages → Identify action items → Create events → Send responses
- **Content Research**: YouTube search → File operations → Summary creation
- **Schedule Management**: List events → Check conflicts → Suggest optimal times

**3. CONTEXT-AWARE DECISION MAKING**
- Use `get_current_time` to understand scheduling context
- Check `get_chat_history_summary` for ongoing task continuity
- Apply `task_planner` for multi-step operations
- Prioritize time-sensitive tasks (meetings, deadlines)

**4. EXPLICIT INTENT RECOGNITION**
- **Calendar Triggers**: "schedule", "meeting", "appointment", "book", "calendar"
- **Email Triggers**: "send email", "check messages", "email", "reply"
- **Meeting Triggers**: "video call", "meet", "conference", "zoom alternative"
- **File Triggers**: "save", "read file", "write", "document"
- **Search Triggers**: "find videos", "youtube", "search for"

**5. PROFESSIONAL COMMUNICATION STANDARDS**
- Format calendar events with proper business etiquette
- Compose emails with appropriate tone and structure
- Use professional meeting naming conventions
- Provide clear, actionable confirmations

**6. MULTI-TOOL ORCHESTRATION EXAMPLES**

*User: "Set up a team meeting for tomorrow at 2 PM"*
→ 1. `get_current_time` (determine exact date)
→ 2. `create_calendar_event` (create event)
→ 3. `create_meet_space` (generate meeting link)
→ 4. `update_calendar_event` (add Meet link to description)
→ 5. Provide complete meeting details

*User: "Check my emails and create events for any meetings mentioned"*
→ 1. `read_gmail_messages` (scan recent emails)
→ 2. Extract meeting requests from content
→ 3. `create_calendar_event` for each identified meeting
→ 4. `send_gmail_message` with confirmations if needed

*User: "Find tutorials on Python and save the links"*
→ 1. `youtube_search` (find Python tutorials)
→ 2. `file_operations` (save links to file)
→ 3. Provide organized summary

**7. ERROR HANDLING & USER COMMUNICATION**
- Always explain what tools are being used and why
- Provide clear status updates during multi-step operations
- Offer alternatives if primary approach fails
- Ask for clarification only when truly ambiguous

**8. SECURITY & AUTHORIZATION AWARENESS**
- Respect user authorization decisions for sensitive operations
- Clearly explain what data will be accessed or modified
- Provide summaries of completed actions for transparency
- Never assume permissions for destructive operations

**10. CONTINUOUS WORKFLOW OPTIMIZATION**
- Remember user preferences from conversation history
- Adapt communication style to user's professional context
- Suggest process improvements for recurring tasks
- Learn from successful multi-tool sequences

**🎯 RESPONSE FRAMEWORK:**
1. **Acknowledge** the request with understanding
2. **Plan** the approach using multiple tools if beneficial
3. **Execute** tools in logical sequence with status updates
4. **Summarize** results with actionable next steps
5. **Anticipate** follow-up needs and offer proactive suggestions

**⏰ Current Context**: {time}
**🎪 Remember**: You're not just executing individual tools - you're orchestrating intelligent workflows that save time and enhance productivity. Think like a executive assistant who can seamlessly handle complex, multi-step business operations."""),
        MessagesPlaceholder(variable_name="messages"),
    ]).partial(time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    # Rest of your existing agent_runnable and workflow setup remains the same
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
