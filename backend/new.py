import os
import sys
import uuid
import json
import requests
import subprocess
import readline
from datetime import datetime
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.messages import HumanMessage, AIMessage
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.tools import tool
from dotenv import load_dotenv
import warnings
import asyncio
import websockets
import base64
import html
from typing import Dict, Any, Optional, List

warnings.filterwarnings("ignore", message="Convert_system_message_to_human will be deprecated!")

# Global variables
chatmap = {}
session_id = None
HISTORY_FILE = "chat_history.json"
COMMAND_HISTORY_FILE = os.path.expanduser("~/.langchain_chat_history")

def setup_readline():
    """Setup readline for command history and arrow key support"""
    try:
        # Enable tab completion
        readline.parse_and_bind("tab: complete")

        # Set history file
        if os.path.exists(COMMAND_HISTORY_FILE):
            readline.read_history_file(COMMAND_HISTORY_FILE)

        # Set maximum history length
        readline.set_history_length(1000)

        # Enable arrow keys and command editing
        readline.parse_and_bind("set editing-mode emacs")
        readline.parse_and_bind("set show-all-if-ambiguous on")
        readline.parse_and_bind("set completion-ignore-case on")

    except Exception as e:
        print(f"⚠️  Warning: Could not setup readline: {e}")

def save_readline_history():
    """Save command history to file"""
    try:
        readline.write_history_file(COMMAND_HISTORY_FILE)
    except Exception as e:
        print(f"⚠️  Warning: Could not save command history: {e}")

# Define tools for the agent
@tool
def get_current_time() -> str:
    """Get the current date and time."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

@tool
def calculate(expression: str) -> str:
    """Safely evaluate a mathematical expression.

    Allowed:
      - Numbers (int/float)
      - Parentheses
      - Operators: + - * / ** %
    Disallowed:
      - Names, attribute access, function calls, indexing, binaries, etc.

    Args:
        expression (str): The arithmetic expression to evaluate.

    Returns:
        str: The numeric result or an error message.
    """
    import ast, operator as op
    try:
        operators = {
            ast.Add: op.add,
            ast.Sub: op.sub,
            ast.Mult: op.mul,
            ast.Div: op.truediv,
            ast.Mod: op.mod,
            ast.Pow: op.pow,
            ast.USub: op.neg,
            ast.UAdd: op.pos,
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
        # Using a free weather API (replace with your preferred service)
        # This is a mock implementation - you'd need to sign up for a real API
        return f"Mock weather data for {city}: Sunny, 22°C, Light breeze"
    except Exception as e:
        return f"Error getting weather: {str(e)}"

@tool
def file_operations(operation: str, filename: str, content: str = "") -> str:
    """
    Perform controlled file system interactions in the CURRENT working directory only.

    Operations:
        read  - Read and return the text contents of a file
        write - Create or overwrite a text file with provided content
        list  - List entries in a directory (defaults to current directory if blank)

    Security / Safety Rules:
        - Absolute paths are rejected (must be relative)
        - Parent directory traversal ('..') is disallowed
        - Paths are constrained to the current working directory
        - Maximum write size: 100 KB
        - Binary files are not specially handled (assumed UTF-8 text)

    Args:
        operation (str): One of: read | write | list
        filename  (str): Target file or directory path (relative). For list, may be ''.
        content   (str): Content to write (used only for write)

    Returns:
        str: Result message or file contents / directory listing.

    Errors:
        Returns a descriptive error string instead of raising exceptions.
    """
    try:
        operation = operation.lower().strip()
        allowed_ops = {"read", "write", "list"}
        if operation not in allowed_ops:
            return "Error: Invalid operation. Use one of: read, write, list"

        # Normalize and validate path (allow empty for list)
        base_dir = os.getcwd()
        target = filename.strip()
        if target == "" and operation == "list":
            target_path = base_dir
        elif target == "":
            return "Error: filename required for this operation"
        else:
            # Reject absolute and traversal attempts
            if os.path.isabs(target):
                return "Error: Absolute paths are not allowed"
            if ".." in target.split(os.sep):
                return "Error: Parent directory traversal is not allowed"

            # Resolve real path and ensure containment
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
            # Basic size guard (2 MB read limit)
            if os.path.getsize(target_path) > 2 * 1024 * 1024:
                return "Error: File too large to read (>2MB)"
            with open(target_path, "r", encoding="utf-8", errors="replace") as f:
                return f.read()

        if operation == "write":
            if len(content) > 100_000:
                return "Error: Content exceeds 100KB write limit"
            # Ensure parent directory exists (but still within base_dir)
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
    try:
        # Whitelist of safe commands
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
    """Get a summary of the current chat session history including recent questions and responses."""
    global chatmap, session_id

    if session_id not in chatmap or not chatmap[session_id].messages:
        return "No chat history found in current session."

    history = chatmap[session_id].messages

    # Get recent messages (last 10 interactions)
    recent_messages = history[-20:] if len(history) > 20 else history

    summary = "Recent chat history:\n"
    for i, msg in enumerate(recent_messages):
        role = "User" if msg.type == "human" else "Assistant"
        content = msg.content[:100] + "..." if len(msg.content) > 100 else msg.content
        summary += f"{i+1}. {role}: {content}\n"

    return summary

@tool
def task_planner(user_request: str) -> str:
    """Plan out the steps needed to complete a complex user request. Use this when the user asks for multiple things to be done."""
    # This tool helps the AI think through complex requests step by step
    return f"Planning steps for: {user_request}\n" \
           f"1. Identify all requested actions\n" \
           f"2. Determine which tools are needed\n" \
           f"3. Execute tools in proper sequence\n" \
           f"4. Verify all tasks are completed\n" \
           f"Remember: Actually use the tools, don't just describe what you would do!"

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

    Args:
        query (str):
            Search term or keywords. Examples: "valorant montage", "python tutorial"
        max_results (int, optional):
            Maximum number of results to return (1–50). Defaults to 5.
        video_type (str, optional):
            One of: "video", "playlist", "channel". Defaults to "video".
        output_format (str, optional):
            "text" (default) for human-readable summary or "json" for a JSON array
            of result objects.

    Returns:
        str:
            - Human-readable multiline string (output_format="text")
            - JSON string (output_format="json") of structure:
              {
                "query": "...",
                "type": "...",
                "count": N,
                "results": [
                  {
                    "index": 1,
                    "title": "...",
                    "channel": "...",
                    "published": "...",
                    "url": "...",
                    "description": "...",
                    "kind": "video|playlist|channel"
                  },
                  ...
                ]
              }

    Notes:
        - Requires YOUTUBE_API_KEY environment variable for live results.
        - If missing, returns mock data (in requested format).
        - Descriptions are truncated to 100 chars for brevity.

    Error Handling:
        Returns an error message string if request/processing fails.
    """
    try:
        api_key = os.getenv('YOUTUBE_API_KEY')
        output_format = (output_format or "text").lower()
        if output_format not in {"text", "json"}:
            output_format = "text"

        # Validate max_results & type
        max_results = max(1, min(int(max_results), 50))
        valid_types = {"video", "playlist", "channel"}
        if video_type not in valid_types:
            video_type = "video"

        # Mock fallback if no API key
        if not api_key:
            mock_items = [
                {
                    "index": 1,
                    "title": "Sample Valorant Montage - Epic Plays",
                    "channel": "ProGamer123",
                    "published": "Unknown",
                    "url": "https://youtube.com/watch?v=sample123",
                    "description": "Amazing valorant highlights and clutch moments...",
                    "kind": "video"
                },
                {
                    "index": 2,
                    "title": "Best Valorant Montage 2024",
                    "channel": "EsportsHighlights",
                    "published": "Unknown",
                    "url": "https://youtube.com/watch?v=sample456",
                    "description": "Top valorant plays compilation from professional matches...",
                    "kind": "video"
                }
            ]
            if output_format == "json":
                return json.dumps({
                    "query": query,
                    "type": video_type,
                    "count": len(mock_items),
                    "results": mock_items,
                    "mock": True,
                    "note": "Set YOUTUBE_API_KEY for live results"
                }, indent=2)
            # Text format
            lines = [
                f"YouTube Search Results for '{query}' (MOCK DATA - set YOUTUBE_API_KEY for live results):",
                ""
            ]
            for item in mock_items:
                lines.append(
f"{item['index']}. {item['title']}\n   Channel: {item['channel']}\n   Published: {item['published']}\n   URL: {item['url']}\n   Description: {item['description']}"
                )
            return "\n".join(lines)

        # Live API call
        base_url = "https://www.googleapis.com/youtube/v3/search"
        params = {
            "part": "snippet",
            "q": query,
            "type": video_type,
            "maxResults": max_results,
            "key": api_key,
            "order": "relevance"
        }
        response = requests.get(base_url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()

        items = data.get("items", [])
        if not items:
            if output_format == "json":
                return json.dumps({
                    "query": query,
                    "type": video_type,
                    "count": 0,
                    "results": []
                }, indent=2)
            return f"No YouTube results found for query: '{query}'"

        structured_results = []
        text_blocks = [f"YouTube Search Results for '{query}':", ""]

        for idx, item in enumerate(items, 1):
            snippet = item.get("snippet", {})
            id_part = item.get("id", {})
            video_id = id_part.get("videoId", "")
            playlist_id = id_part.get("playlistId", "")
            channel_id = id_part.get("channelId", "")

            if video_id:
                url = f"https://youtube.com/watch?v={video_id}"
                kind = "video"
            elif playlist_id:
                url = f"https://youtube.com/playlist?list={playlist_id}"
                kind = "playlist"
            elif channel_id:
                url = f"https://youtube.com/channel/{channel_id}"
                kind = "channel"
            else:
                url = "URL not available"
                kind = "unknown"

            title = snippet.get("title", "No title")
            channel = snippet.get("channelTitle", "Unknown channel")
            description = snippet.get("description", "No description") or "No description"
            published = snippet.get("publishTime", snippet.get("publishedAt", "Unknown date"))

            if len(description) > 100:
                description = description[:100] + "..."

            structured_results.append({
                "index": idx,
                "title": title,
                "channel": channel,
                "published": published,
                "url": url,
                "description": description,
                "kind": kind
            })

            if output_format == "text":
                text_blocks.append(
f"{idx}. {title}\n   Channel: {channel}\n   Published: {published}\n   URL: {url}\n   Description: {description}"
                )

        if output_format == "json":
            return json.dumps({
                "query": query,
                "type": video_type,
                "count": len(structured_results),
                "results": structured_results
            }, indent=2)
        return "\n".join(text_blocks)

    except requests.exceptions.RequestException as e:
        if output_format == "json":
            return json.dumps({"error": "request_exception", "message": str(e)}, indent=2)
        return f"Error making YouTube API request: {e}"
    except ValueError as e:
        if output_format == "json":
            return json.dumps({"error": "value_error", "message": str(e)}, indent=2)
        return f"Error parsing YouTube API response: {e}"
    except Exception as e:
        if output_format == "json":
            return json.dumps({"error": "unexpected_error", "message": str(e)}, indent=2)
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

## the gmail tool
@tool
def read_gmail_messages(top=5):
    """Main function to read Gmail messages with all helper functions defined inside"""
    top = int(top)
    # Initialize the result string
    result_string = ""

    def decode_base64_url(data):
        """Decode base64url-encoded data"""
        # Add padding if needed
        missing_padding = len(data) % 4
        if missing_padding:
            data += '=' * (4 - missing_padding)

        # Replace URL-safe characters
        data = data.replace('-', '+').replace('_', '/')

        try:
            return base64.b64decode(data).decode('utf-8')
        except:
            return "[Unable to decode content]"

    def extract_message_body(payload):
        """Extract the message body from Gmail API payload"""
        body = ""

        # Handle multipart messages
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain' and 'data' in part['body']:
                    body += decode_base64_url(part['body']['data'])
                elif part['mimeType'] == 'text/html' and 'data' in part['body']:
                    html_content = decode_base64_url(part['body']['data'])
                    # You might want to strip HTML tags here
                    body += f"\n[HTML Content]: {html_content[:200]}..." if len(html_content) > 200 else f"\n[HTML Content]: {html_content}"
                elif 'parts' in part:  # Nested parts
                    body += extract_message_body(part)

        # Handle simple messages (not multipart)
        elif 'data' in payload.get('body', {}):
            body = decode_base64_url(payload['body']['data'])

        return body

    def get_attachments_info(payload):
        """Extract attachment information"""
        attachments = []

        def process_parts(parts):
            for part in parts:
                if part.get('filename'):
                    attachment_info = {
                        'filename': part['filename'],
                        'mimeType': part['mimeType'],
                        'size': part['body'].get('size', 0)
                    }
                    attachments.append(attachment_info)

                if 'parts' in part:
                    process_parts(part['parts'])

        if 'parts' in payload:
            process_parts(payload['parts'])

        return attachments

    # Main execution starts here
    # Read tokens from file
    with open("/home/anubhav/courses/luna-version-x/frontend/saved-tokens/google_token_terminalishere127_at_gmail_com.json", "r") as f:
        data = json.load(f)

    access_token = data["accessToken"]

    # Step 1: Get list of messages
    list_url = "https://gmail.googleapis.com/gmail/v1/users/me/messages"
    params = {
        "maxResults": top,
        "labelIds": "INBOX"
    }

    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    list_response = requests.get(list_url, headers=headers, params=params)

    if list_response.status_code != 200:
        error_msg = f"Error fetching messages: {list_response.status_code} {list_response.text}"
        result_string += error_msg + "\n"
        return result_string

    messages = list_response.json().get("messages", [])
    result_string += f"Found {len(messages)} messages\n\n"

    # Step 2: Fetch detailed information for each message
    for i, msg in enumerate(messages, 1):
        msg_id = msg["id"]

        # Use 'full' format to get complete message data
        detail_url = f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{msg_id}"
        detail_params = {"format": "full"}

        detail_response = requests.get(detail_url, headers=headers, params=detail_params)

        if detail_response.status_code != 200:
            error_msg = f"Error fetching message {i} details: {detail_response.status_code} {detail_response.text}"
            result_string += error_msg + "\n"
            continue

        msg_data = detail_response.json()

        # Extract all available headers
        headers_list = msg_data.get("payload", {}).get("headers", [])

        # Create a dictionary of headers for easy access
        email_headers = {h["name"]: h["value"] for h in headers_list}

        # Extract key information
        subject = email_headers.get("Subject", "(No Subject)")
        sender = email_headers.get("From", "(No Sender)")
        recipient = email_headers.get("To", "(No Recipient)")
        date = email_headers.get("Date", "(No Date)")
        cc = email_headers.get("Cc", "")
        bcc = email_headers.get("Bcc", "")
        reply_to = email_headers.get("Reply-To", "")
        message_id = email_headers.get("Message-ID", "")

        # Extract message body
        payload = msg_data.get("payload", {})
        body = extract_message_body(payload)

        # Get attachments info
        attachments = get_attachments_info(payload)

        # Get snippet
        snippet = msg_data.get("snippet", "").strip()

        # Get labels
        label_ids = msg_data.get("labelIds", [])

        # Get thread ID
        thread_id = msg_data.get("threadId", "")

        # Print comprehensive information
        result_string += f"{'='*80}\n"
        result_string += f"MESSAGE {i} - ID: {msg_id}\n"
        result_string += f"{'='*80}\n"
        result_string += f"📧 Subject: {subject}\n"
        result_string += f"👤 From: {sender}\n"
        result_string += f"👥 To: {recipient}\n"
        if cc:
            result_string += f"📋 CC: {cc}\n"
        if bcc:
            result_string += f"📋 BCC: {bcc}\n"
        if reply_to:
            result_string += f"↩️  Reply-To: {reply_to}\n"
        result_string += f"📅 Date: {date}\n"
        result_string += f"🆔 Message ID: {message_id}\n"
        result_string += f"🧵 Thread ID: {thread_id}\n"
        result_string += f"🏷️  Labels: {', '.join(label_ids)}\n"

        result_string += f"\n📄 SNIPPET:\n"
        result_string += f"{snippet}\n"

        result_string += f"\n📃 FULL BODY:\n"
        result_string += "-" * 40 + "\n"
        if body.strip():
            result_string += (body[:1000] + "..." if len(body) > 1000 else body) + "\n"  # Limit body length for readability
        else:
            result_string += "[No plain text body found]\n"

        if attachments:
            result_string += f"\n📎 ATTACHMENTS ({len(attachments)}):\n"
            for att in attachments:
                result_string += f"  • {att['filename']} ({att['mimeType']}, {att['size']} bytes)\n"

        # Show additional headers (optional)
        result_string += f"\n📋 ALL HEADERS:\n"
        result_string += "-" * 40 + "\n"
        for header_name, header_value in email_headers.items():
            if header_name not in ['Subject', 'From', 'To', 'Date', 'Cc', 'Bcc', 'Reply-To', 'Message-ID']:
                result_string += f"{header_name}: {header_value}\n"

        result_string += "\n" + "="*80 + "\n\n"

    result_string += "✅ Email extraction completed!\n"
    return result_string


# List of available tools
tools = [
    get_current_time,
    calculate,
    get_weather,
    file_operations,
    run_command,
    get_chat_history_summary,
    task_planner,
    youtube_search,
    chrome_tab_controller,
    read_gmail_messages
]

def load_chat_history():
    """Load chat history from file"""
    global chatmap, session_id

    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r') as f:
                data = json.load(f)
                session_id = data.get('session_id', str(uuid.uuid4()))

                # Reconstruct chat history
                if 'messages' in data:
                    history = InMemoryChatMessageHistory()
                    for msg in data['messages']:
                        if msg['type'] == 'human':
                            history.add_message(HumanMessage(content=msg['content']))
                        else:
                            history.add_message(AIMessage(content=msg['content']))
                    chatmap[session_id] = history
        except Exception as e:
            print(f"⚠️  Error loading history: {e}")
            session_id = str(uuid.uuid4())
    else:
        session_id = str(uuid.uuid4())

def save_chat_history():
    """Save chat history to file"""
    global chatmap, session_id

    try:
        data = {'session_id': session_id, 'messages': []}

        if session_id in chatmap:
            for msg in chatmap[session_id].messages:
                data['messages'].append({
                    'type': msg.type,
                    'content': msg.content,
                    'timestamp': datetime.now().isoformat()
                })

        with open(HISTORY_FILE, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"⚠️  Error saving history: {e}")

def setup_model():
    """Initialize the Gemini model.

    Loads environment variables (expects GOOGLE_API_KEY). If the key is missing,
    returns None so the caller can handle a graceful shutdown with guidance.
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return None

    return ChatGoogleGenerativeAI(
        model=os.getenv("MODEL_NAME", "gemini-1.5-flash"),
        temperature=float(os.getenv("TEMPERATURE", "0.3")),
        google_api_key=api_key,
        convert_system_message_to_human=True
    )

def get_chat_history(session_id: str) -> InMemoryChatMessageHistory:
    """Get or create chat history for a session"""
    global chatmap
    if session_id not in chatmap:
        chatmap[session_id] = InMemoryChatMessageHistory()
    return chatmap[session_id]

def setup_agent_executor(model):
    """Setup the LangChain agent executor with tools and chat history"""
    # Create agent prompt with scratchpad
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an intelligent AI named Luna assistant. Your primary goal is to provide helpful, accurate, and direct responses to user queries.

CRITICAL INSTRUCTIONS (Tool Governance & Response Policy):
1. Answer from knowledge first: For general questions, explanations, definitions, coding help, conceptual reasoning, or widely known facts, respond directly from your internal knowledge. DO NOT call tools when you already know the answer with high confidence.
2. When to use tools (only on explicit need):
   - `get_current_time`: User explicitly asks for current time/date (not historical time facts).
   - `calculate`: Non-trivial arithmetic or when user explicitly requests calculation/compute/evaluate.
   - `get_weather`: Only when user asks current weather/forecast for a city (do not guess).
   - `file_operations`: Only if user explicitly says read/show/open file, write/save/create file, or list directory contents (never for scratch memory).
   - `run_command`: Only if user explicitly asks to run/execute a shell command that is in the safe whitelist (never speculate).
   - `get_chat_history_summary`: User asks what was said before / summarize / recap.
   - `task_planner`: User asks for a plan, multi-step strategy, roadmap, breakdown, or workflow.
   - `youtube_search`: User explicitly wants YouTube / video / channel / playlist / montage / highlights / tutorial search or links. Never use for general info you can summarize yourself.
   - `chrome_tab_controller`: User explicitly asks to list, open, close, switch, reload, or navigate browser/Chrome tabs.
3. File & command safety:
   - Never create, overwrite, or list files unless explicitly requested.
   - Never run commands not in the safe whitelist. If unsafe, explain refusal and offer alternatives.
4. YouTube usage rules:
   - Only call `youtube_search` if the user requests discovering/finding videos, playlists, channels, montages, highlight reels, or explicitly says "YouTube", "YT", "video search".
   - If user wants general info (e.g. “Explain Valorant agents”), answer directly—do NOT search.
   - Never fabricate YouTube results; if tool not used, clearly state you did not perform a live search.
5. Gmail message reading:
   - Only call `read_gmail_messages` if the user explicitly asks to read their Gmail messages.
   - If user wants general info (e.g. “Explain Gmail usage”), answer directly—do NOT read messages.
   - Never fabricate Gmail messages; if tool not used, clearly state you did not perform a live read.
6. Tool decision protocol:
   - BEFORE calling a tool, internally verify: (a) Is a tool strictly required? (b) Is there explicit user intent? If not both, answer directly.
6. Output integrity:
   - Never claim to have executed a tool you didn’t actually call.
   - If a tool fails or returns no data, transparently state that and offer next steps.
7. Conversational style:
   - Be concise, helpful, and natural. Avoid meta-commentary about tools unless user asks.
8. Focus & relevance:
   - Answer only what was asked; offer optional extensions briefly if clearly valuable.

If a request is ambiguous about needing a tool, first clarify or answer with what you can WITHOUT calling tools.

Remember: Precision in deciding NOT to call a tool is as important as correct tool usage."""),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad")
    ])
    # Create the agent
    agent = create_tool_calling_agent(model, tools, prompt)

    # Create agent executor
    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        handle_parsing_errors=True,
        max_iterations=5  # Allow more iterations for complex tasks
    )

    # Wrap with message history
    agent_with_history = RunnableWithMessageHistory(
        runnable=agent_executor,
        get_session_history=get_chat_history,
        input_messages_key="input",
        history_messages_key="chat_history"
    )

    return agent_with_history

def get_response(agent_executor, question: str) -> str:
    """Get response from the AI agent safely handling varied return structures."""
    global session_id
    try:
        raw = agent_executor.invoke(
            {"input": question},
            config={"configurable": {"session_id": session_id}}
        )
        result = None
        if isinstance(raw, dict):
            # Try common keys in order
            for key in ("output", "answer", "content", "result"):
                if key in raw and isinstance(raw[key], str) and raw[key].strip():
                    result = raw[key]
                    break
        if result is None:
            if isinstance(raw, str):
                result = raw
            elif raw is None:
                result = "No response generated"
            else:
                result = str(raw)
        return result
    except Exception as e:
        return f"Error: {e}"

def print_welcome():
    """Print welcome message"""
    global session_id
    sid_display = "N/A"
    if isinstance(session_id, str):
        # Show first 8 chars if available
        sid_display = (session_id[:8] + "...") if len(session_id) >= 8 else session_id
    print("\n" + "="*60)
    print("🤖 LANGCHAIN AGENT CHAT APPLICATION")
    print("="*60)
    print("✨ Powered by Google Gemini 1.5 Flash with Tools")
    print(f"📱 Session ID: {sid_display}")
    print("📝 Type your message and press Enter")
    print("⌨️  Use ↑/↓ arrow keys to navigate command history")
    print("🛠️  Available Tools: time, calculator, weather, files, commands, search, chrome")
    print("💡 Commands: /help, /history, /clear, /quit, /tools")
    print("="*60 + "\n")

def print_help():
    """Print help message"""
    print("\n📚 AVAILABLE COMMANDS:")
    print("  /help     - Show this help message")
    print("  /history  - Show chat history")
    print("  /clear    - Clear chat history")
    print("  /quit     - Exit the application")
    print("  /session  - Show current session info")
    print("  /new      - Start new chat session")
    print("  /tools    - Show available tools")
    print()

def print_tools():
    """Print available tools"""
    print("\n🛠️  AVAILABLE TOOLS:")
    print("  get_current_time          - Get current date and time")
    print("  calculate                 - Perform safe mathematical calculations")
    print("  get_weather               - Get (mock) weather information for a city")
    print("  file_operations           - Read, write, or list files (current directory only)")
    print("  run_command               - Execute safe whitelisted shell commands")
    print("  get_chat_history_summary  - Access recent chat history summary")
    print("  task_planner              - Plan out steps for complex requests")
    print("  youtube_search            - Search YouTube videos (requires API key)")
    print("  chrome_tab_controller     - Control Chrome tabs (requires WebSocket server)")
    print("\n💡 Just ask naturally, like:")
    print("  - 'What time is it?'")
    print("  - 'Calculate 15 * 23 + 7'")
    print("  - 'What's the weather in London?'")
    print("  - 'Search YouTube for python concurrency tutorials'")
    print("  - 'List files in current directory'")
    print("  - 'Can you open a new tab to google.com?'")
    print("  - 'List all my open chrome tabs'")
    print("  - 'What questions have I asked?'")
    print("  - 'Create a story and save it to a file'")
    print()

def print_history():
    """Print chat history"""
    global chatmap, session_id
    history = chatmap.get(session_id)
    if not history or not history.messages:
        print("📝 No chat history found.")
        return

    print("\n📜 CHAT HISTORY:")
    print("-" * 50)
    for i, msg in enumerate(history.messages, 1):
        timestamp = datetime.now().strftime("%H:%M:%S")
        role = "🧑 You" if msg.type == "human" else "🤖 AI"
        content = msg.content[:100] + "..." if len(msg.content) > 100 else msg.content
        print(f"{i}. [{timestamp}] {role}: {content}")
    print("-" * 50 + "\n")

def clear_history():
    """Clear chat history"""
    global chatmap, session_id
    if session_id in chatmap:
        chatmap[session_id].clear()
    # Also clear the file
    if os.path.exists(HISTORY_FILE):
        os.remove(HISTORY_FILE)
    print("🗑️ Chat history cleared!\n")

def new_session():
    """Start a new chat session"""
    global session_id
    # Save current session before creating new one
    save_chat_history()
    session_id = str(uuid.uuid4())
    print(f"🆕 New session started: {session_id[:8]}...\n")

def print_session_info():
    """Print current session information"""
    global chatmap, session_id
    history = chatmap.get(session_id)
    msg_count = len(history.messages) if history else 0
    print(f"\n📊 SESSION INFO:")
    print(f"   Session ID: {session_id}")
    print(f"   Messages: {msg_count}")
    print(f"   Model: Gemini 1.5 Flash (Agent)")
    print(f"   Tools: {len(tools)} available")
    print()

def run_chat_loop(agent_executor):
    """Interactive chat loop.

    Streaming Placeholder:
      - To implement token streaming, replace the direct get_response() call
        with a streaming generator from the model (e.g. model.stream()) and
        incrementally print tokens.
      - Provide a /stream toggle or CLI flag to enable/disable.
      - Maintain a buffer to still persist the full response to history.

    Future Extensions:
      - Multi-modal inputs (images/audio) routed before tool use.
      - Background tasks (cron-style) triggered between user turns.
      - Thought visibility toggle for agent reasoning traces.
    """
    global session_id
    try:
        while True:
            # Input acquisition (could be abstracted for GUI / API / WebSocket)
            try:
                user_input = input("🧑 You: ").strip()
            except EOFError:
                print("\n👋 Goodbye! Thanks for chatting!")
                break

            if not user_input:
                continue

            # Command handling
            if user_input.startswith('/'):
                command = user_input.lower()
                if command in ('/quit', '/exit'):
                    save_chat_history()
                    save_readline_history()
                    print("👋 Goodbye! Thanks for chatting!")
                    break
                elif command == '/help':
                    print_help()
                elif command == '/history':
                    print_history()
                elif command == '/clear':
                    clear_history()
                elif command == '/session':
                    print_session_info()
                elif command == '/new':
                    new_session()
                elif command == '/tools':
                    print_tools()
                else:
                    print("❌ Unknown command. Type /help for available commands.\n")
                continue

            # Response (non-streaming baseline)
            print("🤖 AI: ", end="", flush=True)
            response = get_response(agent_executor, user_input)

            # Streaming Placeholder:
            # for token in stream_model_response(user_input):
            #     print(token, end='', flush=True)
            # print()  # final newline after streaming

            print(response)
            print()

            save_chat_history()
    except KeyboardInterrupt:
        print("\n\n👋 Chat interrupted. Goodbye!")
        save_chat_history()
        save_readline_history()
    except Exception as e:
        print(f"\n❌ An error occurred: {str(e)}")
        save_chat_history()
        save_readline_history()


def main():
    """Entry point: initialize environment, model, agent, and launch interactive loop.

    Initialization Steps:
      1. Validate environment (API keys, optional feature flags)
      2. Setup readline (history, key bindings)
      3. Load persisted chat history
      4. Instantiate model + tools agent
      5. Display welcome banner
      6. Enter chat loop (run_chat_loop)

    Future Enhancements:
      - CLI args (e.g. --stream, --config path, --model override)
      - Config file parsing (YAML/TOML) for tool & model settings
      - Plugin auto-discovery & dynamic tool registry
      - Structured logging / telemetry hooks
    """
    global session_id

    # Load .env values (if not already loaded implicitly elsewhere)
    load_dotenv(override=False)

    if not os.getenv("GOOGLE_API_KEY"):
        print("⚠️ GOOGLE_API_KEY not found.")
        print("   1. Copy .env.example to .env")
        print("   2. Add your key: GOOGLE_API_KEY=YOUR_GOOGLE_API_KEY")
        print("   3. (Optional) Add YOUTUBE_API_KEY for youtube_search tool")
        print("   4. Re-run this program.")
        sys.exit(1)

    setup_readline()
    load_chat_history()
    model = setup_model()
    agent_executor = setup_agent_executor(model)
    print_welcome()
    run_chat_loop(agent_executor)
    sys.exit(0)


if __name__ == "__main__":
    main()
