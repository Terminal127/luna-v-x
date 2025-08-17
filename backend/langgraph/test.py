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

warnings.filterwarnings("ignore", message="Convert_system_message_to_human will be deprecated!")

# Global variables
chatmap = {}
session_id = None
HISTORY_FILE = "chat_history.json"
COMMAND_HISTORY_FILE = os.path.expanduser("~/.langchain_chat_history")

# Authorization settings - tools that require user permission
REQUIRES_AUTHORIZATION = {
    "read_gmail_messages": "This will read your Gmail messages. Do you want to proceed?",
    "send_gmail_message": "This will send a gmail to the appopriate authority, Fo you want to proceed"
}

# State for LangGraph - Corrected according to tutorial patterns
class AgentState(TypedDict):
    messages: Annotated[List[HumanMessage | AIMessage | ToolMessage], add_messages]

def setup_readline():
    """Setup readline for command history and arrow key support"""
    try:
        readline.parse_and_bind("tab: complete")
        if os.path.exists(COMMAND_HISTORY_FILE):
            readline.read_history_file(COMMAND_HISTORY_FILE)
        readline.set_history_length(1000)
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
def chrome_tab_controller(command: str, url: Optional[str] = None, tab_id: Optional[int] = None) -> str:
    """Control Google Chrome tabs by connecting to a WebSocket server."""
    # Implementation similar to your original but simplified for brevity
    return f"Chrome tab controller executed: {command} (requires WebSocket server)"

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
    with open("/home/anubhav/courses/luna-version-x/frontend/saved-tokens/google_token.json", "r") as f:
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

@tool
def send_gmail_message(to: str, title: str, body: str):
    """
    Send an email using Gmail API with a saved OAuth token.

    Args:
        to (str): Recipient email address
        title (str): Email subject
        body (str): Email body (plain text)

    Returns:
        str: API response status
    """
    try:
        # Read the access token from saved file
        with open("/home/anubhav/courses/luna-version-x/frontend/saved-tokens/google_token.json", "r") as f:
            data = json.load(f)

        access_token = data["accessToken"]

        # Build the MIME message
        message = MIMEText(body)
        message["to"] = to
        message["subject"] = title

        # Encode message as base64url
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")

        url = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        payload = {"raw": raw_message}

        response = requests.post(url, headers=headers, json=payload)

        if response.status_code == 200:
            return f"✅ Message successfully sent to {to} with subject '{title}'"
        else:
            return f"❌ Failed to send message: {response.status_code} {response.text}"

    except Exception as e:
        return f"⚠️ Error sending message: {str(e)}"

# Separate tools into safe and sensitive categories
safe_tools = [
    get_current_time,
    calculate,
    get_weather,
    get_chat_history_summary,
    task_planner,
    youtube_search
]

sensitive_tools = [
    read_gmail_messages,
    send_gmail_message

]

# Get tool names for routing
sensitive_tool_names = {t.name for t in sensitive_tools}
all_tools = safe_tools + sensitive_tools

# Create error handling tool nodes
def handle_tool_error(state) -> dict:
    error = state.get("error")
    tool_calls = state["messages"][-1].tool_calls
    return {
        "messages": [
            ToolMessage(
                content=f"Error: {repr(error)}\nPlease fix your mistakes.",
                tool_call_id=tc["id"],
            )
            for tc in tool_calls
        ]
    }

def create_tool_node_with_fallback(tools: list):
    from langchain_core.runnables import RunnableLambda
    return ToolNode(tools).with_fallbacks(
        [RunnableLambda(handle_tool_error)], exception_key="error"
    )

def get_user_authorization(tool_calls):
    """Get user authorization for sensitive tool calls"""
    authorized_calls = []

    for tool_call in tool_calls:
        tool_name = tool_call["name"]

        if tool_name in REQUIRES_AUTHORIZATION:
            print(f"\n🔐 AUTHORIZATION REQUIRED for {tool_name}")
            print(f"📋 {REQUIRES_AUTHORIZATION[tool_name]}")
            print(f"🔧 Parameters: {json.dumps(tool_call['args'], indent=2)}")
            AUTH_URL  = "http://localhost:9000/"

            data = {
                "tool_name": tool_name,
                "tool_args": tool_call['args'],
                "authorization": "null"
            }

            basic_data = {
                "tool_name": "default_tool",
                "tool_args": {},
                "authorization": "null"
            }

            print("changed the state of authorization")

            requests.post(AUTH_URL, json=data)
            while True:
                # Fetch latest config from server
                resp = requests.get(AUTH_URL)
                config_data = resp.json()  # now a dict

                # Check if server has already set authorization
                if config_data.get("authorization") is not None:
                    auth = config_data["authorization"].upper()

                    if auth == "A":
                        authorized_calls.append(tool_call)
                        print("✅ Approved via server!")
                        requests.post(AUTH_URL,json=basic_data)
                        break

                    elif auth == "D":
                        print("❌ Denied via server!")
                        denied_call = tool_call.copy()
                        denied_call["denied"] = True
                        authorized_calls.append(denied_call)
                        requests.post(AUTH_URL,json=basic_data)
                        break

                    elif auth == "M":
                        print(f"\n📝 Current parameters: {json.dumps(tool_call['args'], indent=2)}")
                        print("📝 Enter new parameters as JSON (or press Enter to keep current):")

                        try:
                            new_params_input = input("New params: ").strip()
                            if new_params_input:
                                new_params = json.loads(new_params_input)
                                tool_call["args"] = new_params
                                print("✅ Parameters updated (via server trigger)!")
                            else:
                                print("📝 Keeping current parameters")
                        except json.JSONDecodeError:
                            print("❌ Invalid JSON. Keeping original parameters.")

                        authorized_calls.append(tool_call)
                        print("✅ Approved with parameters via server!")
                        break


        else:
            # Safe tool - auto-approve
            authorized_calls.append(tool_call)

    return authorized_calls

class MixedToolNode:
    """Tool node that handles both safe and sensitive tools in one call"""

    def __init__(self, safe_tools, sensitive_tools):
        self.safe_tools = {tool.name: tool for tool in safe_tools}
        self.sensitive_tools = {tool.name: tool for tool in sensitive_tools}
        self.all_tools = {**self.safe_tools, **self.sensitive_tools}

    def __call__(self, state: AgentState):
        # Debug: Print state type and content
        print(f"DEBUG: MixedToolNode state type: {type(state)}, State keys: {list(state.keys()) if isinstance(state, dict) else 'Not a dict'}")

        # Ensure state is properly formatted as a dictionary
        if not isinstance(state, dict):
            print(f"ERROR: State is not a dict, got {type(state)}: {str(state)[:100]}")
            return {"messages": []}

        if "messages" not in state:
            print(f"ERROR: No messages in state: {list(state.keys())}")
            return {"messages": []}

        messages = state["messages"]
        if not messages:
            return {"messages": messages}

        last_message = messages[-1]

        if not hasattr(last_message, 'tool_calls') or not last_message.tool_calls:
            return {"messages": messages}

        # Separate safe and sensitive tool calls
        safe_calls = [tc for tc in last_message.tool_calls if tc["name"] not in sensitive_tool_names]
        sensitive_calls = [tc for tc in last_message.tool_calls if tc["name"] in sensitive_tool_names]

        results = []

        # Execute safe tools immediately
        for tool_call in safe_calls:
            tool_name = tool_call["name"]
            tool_id = tool_call["id"]

            try:
                if tool_name in self.safe_tools:
                    tool_instance = self.safe_tools[tool_name]
                    result_content = tool_instance.invoke(tool_call["args"])
                    result = ToolMessage(
                        content=str(result_content),
                        tool_call_id=tool_id
                    )
                    results.append(result)
                else:
                    result = ToolMessage(
                        content=f"Error: Safe tool {tool_name} not found",
                        tool_call_id=tool_id
                    )
                    results.append(result)
            except Exception as e:
                print(f"ERROR in safe tool {tool_name}: {e}")
                result = ToolMessage(
                    content=f"Error executing {tool_name}: {str(e)}",
                    tool_call_id=tool_id
                )
                results.append(result)

        # Handle sensitive tools with authorization
        if sensitive_calls:
            try:
                authorized_calls = get_user_authorization(sensitive_calls)

                for tool_call in authorized_calls:
                    tool_name = tool_call["name"]
                    tool_id = tool_call["id"]

                    # Check if this call was denied
                    if tool_call.get("denied", False):
                        result = ToolMessage(
                            content="Authorization denied by user.",
                            tool_call_id=tool_id
                        )
                        results.append(result)
                        continue

                    # Execute the tool
                    try:
                        if tool_name in self.sensitive_tools:
                            tool_instance = self.sensitive_tools[tool_name]
                            result_content = tool_instance.invoke(tool_call["args"])
                            result = ToolMessage(
                                content=str(result_content),
                                tool_call_id=tool_id
                            )
                            results.append(result)
                        else:
                            result = ToolMessage(
                                content=f"Error: Sensitive tool {tool_name} not found",
                                tool_call_id=tool_id
                            )
                            results.append(result)
                    except Exception as e:
                        print(f"ERROR in sensitive tool {tool_name}: {e}")
                        result = ToolMessage(
                            content=f"Error executing {tool_name}: {str(e)}",
                            tool_call_id=tool_id
                        )
                        results.append(result)
            except Exception as e:
                print(f"ERROR in authorization: {e}")
                for tool_call in sensitive_calls:
                    result = ToolMessage(
                        content=f"Authorization error: {str(e)}",
                        tool_call_id=tool_call["id"]
                    )
                    results.append(result)

        return {"messages": messages + results}

def create_agent_graph():
    """Create the LangGraph workflow with authorization following tutorial patterns"""

    # Setup model
    model = setup_model()
    if not model:
        return None

    # Create agent prompt
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are Luna, an intelligent AI assistant powered by Google Gemini. You have access to various tools to help users with their requests.

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
        5. Gmail message reading and sending:
        - Only call `read_gmail_messages` if the user explicitly asks to read their Gmail messages.
        - If user wants general info (e.g. “Explain Gmail usage”), answer directly—do NOT read messages.
        - Never fabricate Gmail messages; if tool not used, clearly state you did not perform a live read.
        - Call the 'send_gmail_message' fucntion if the use wants to send a gmail and then proceed with the autorization
        - Remember you dont need authorization for this , just implement the logic to read messages without authorization.
        6. Tool decision protocol:
        - BEFORE calling a tool, internally verify: (a) Is a tool strictly required? (b) Is there explicit user intent? If not both, answer directly.
        7. Output integrity:
        - Never claim to have executed a tool you didn’t actually call.
        - If a tool fails or returns no data, transparently state that and offer next steps.

        8. **SEQUENTIAL NARRATION FOR MULTI-TOOL TASKS:** If a user's request requires more than one distinct tool, you MUST structure your final response as a step-by-step narration.
        - First, state the result of the first tool's operation.
        - Then, explicitly state that you are moving to the next task (e.g., "Now, I will check your emails...").
        - Finally, present the result of the second tool's operation and a concluding summary.
        - **Example format:** "The result of [first task] is [result 1]. Now, proceeding to [second task]. The result of [second task] is [result 2]. To summarize..."

        9. Conversational style:
        - Be concise, helpful, and natural. Avoid meta-commentary about tools unless user asks.
        10. Focus & relevance:
        - Answer only what was asked; offer optional extensions briefly if clearly valuable.

        If a request is ambiguous about needing a tool, first clarify or answer with what you can WITHOUT calling tools.

        Remember: Precision in deciding NOT to call a tool is as important as correct tool usage.

        Current time: {time}
        Ready to help! Ask me anything or request a task that requires using tools."""),
        MessagesPlaceholder(variable_name="messages"),
    ]).partial(
        tool_names=[tool.name for tool in all_tools],
        time=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )

    # Create the agent runnable
    agent_runnable = prompt | model.bind_tools(all_tools)

    # Assistant class following tutorial pattern
# Just replace your Assistant class with this one - everything handled internally

    class Assistant:
        def __init__(self, runnable):
            self.runnable = runnable

        def __call__(self, state: AgentState):
            # Debug: Print state type and content
            print(f"DEBUG: Assistant state type: {type(state)}")

            # Ensure state is properly formatted
            if not isinstance(state, dict) or "messages" not in state:
                print(f"ERROR: Invalid state format in Assistant: {type(state)}")
                return {"messages": [AIMessage(content="I encountered an error processing your request.")]}

            while True:
                try:
                    result = self.runnable.invoke(state)


                    # NORMALIZE CONTENT INTERNALLY - handle both string and array formats
                    if hasattr(result, 'content'):
                        content = result.content

                        # If it's a list/array, join it to make it a string
                        if isinstance(content, list):
                            normalized_parts = []
                            for item in content:
                                if isinstance(item, str):
                                    normalized_parts.append(item)
                                elif isinstance(item, dict) and "text" in item:
                                    normalized_parts.append(item["text"])
                                else:
                                    normalized_parts.append(str(item))
                            result.content = "".join(normalized_parts)
                        # If it's not a string and not a list, convert to string
                        elif not isinstance(content, str):
                            result.content = str(content)

                    # Check if result has tool calls
                    has_tool_calls = hasattr(result, 'tool_calls') and result.tool_calls

                    # Check if result has valid content (now always a string)
                    has_valid_content = bool(result.content and result.content.strip()) if hasattr(result, 'content') else False

                    # If no tool calls and no valid content, re-prompt
                    if not has_tool_calls and not has_valid_content:
                        messages = state["messages"] + [HumanMessage(content="Respond with a real output.")]
                        state = {"messages": messages}
                    else:
                        break

                except Exception as e:
                    print(f"ERROR in Assistant runnable: {e}")
                    return {"messages": [AIMessage(content=f"I encountered an error: {str(e)}")]}

            return {"messages": [result]}

    # Route tools based on sensitivity

    # Build the graph
    workflow = StateGraph(AgentState)

    # Add nodes - simplified to use one mixed tool node
    workflow.add_node("assistant", Assistant(agent_runnable))
    workflow.add_node("tools", MixedToolNode(safe_tools, sensitive_tools))

    # Add edges - much simpler routing
    workflow.add_edge(START, "assistant")
    workflow.add_conditional_edges(
        "assistant",
        tools_condition,  # Use built-in tools condition
        ["tools", END]
    )
    workflow.add_edge("tools", "assistant")

    # Compile the graph with checkpointer
    memory = MemorySaver()
    app = workflow.compile(checkpointer=memory)

    return app

def load_chat_history():
    """Load chat history from file"""
    global chatmap, session_id
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r') as f:
                data = json.load(f)
                session_id = data.get('session_id', str(uuid.uuid4()))
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
    """Initialize the Gemini model"""
    api_key = os.getenv("MODEL_API_KEY")
    if not api_key:
        return None
    return ChatGoogleGenerativeAI(
        model=os.getenv("MODEL_NAME", "gemini-2.5-flash"),
        temperature=float(os.getenv("TEMPERATURE", "0.3")),
        google_api_key=api_key,
        convert_system_message_to_human=True
    )

def print_welcome():
    """Print welcome message"""
    global session_id
    sid_display = (session_id[:8] + "...") if session_id and len(session_id) >= 8 else "N/A"
    print("\n" + "="*60)
    print("🤖 ENHANCED LANGCHAIN AGENT WITH AUTHORIZATION")
    print("="*60)
    print("✨ Powered by Google Gemini with LangGraph Authorization")
    print(f"📱 Session ID: {sid_display}")
    print("🔐 Tools requiring authorization will ask for permission")
    print("🛠️  Available Tools: time, calculator, weather, files, commands, gmail, youtube, chrome")
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
    print("\n🔐 AUTHORIZATION FEATURES:")
    print("  • Some tools require user permission before execution")
    print("  • You can approve, deny, or modify tool parameters")
    print("  • Gmail reading and file operations require authorization")
    print()

def run_chat_loop(app):
    """Interactive chat loop with authorization support"""
    global session_id
    config = {"configurable": {"thread_id": session_id}}

    try:
        while True:
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
                elif command == '/clear':
                    print("🗑️ Chat history cleared!")
                elif command == '/tools':
                    print("\n🛠️  AVAILABLE TOOLS:")
                    for tool in all_tools:
                        auth_required = "🔐" if tool.name in REQUIRES_AUTHORIZATION else "✅"
                        print(f"  {auth_required} {tool.name} - {tool.description}")
                    print()
                else:
                    print("❌ Unknown command. Type /help for available commands.\n")
                continue

            print("🤖 AI: ", end="", flush=True)

            # Run the graph - simplified approach
            try:
                final_state = None
                for event in app.stream(
                    {"messages": [HumanMessage(content=user_input)]},
                    config,
                    stream_mode="values"
                ):
                    final_state = event

                if final_state and final_state.get("messages"):
                    last_message = final_state["messages"][-1]
                    if hasattr(last_message, 'content') and last_message.content:
                        print(last_message.content)
                    else:
                        print("Response generated successfully")
                else:
                    print("No response generated")

            except Exception as e:
                print(f"Error: {str(e)}")

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
    """Entry point with authorization support"""
    global session_id

    load_dotenv(override=False)

    if not os.getenv("MODEL_API_KEY"):
        print("⚠️ MODEL_API_KEY not found.")
        print("   1. Copy .env.example to .env")
        print("   2. Add your key: MODEL_API_KEY=YOUR_MODEL_API_KEY")
        print("   3. (Optional) Add YOUTUBE_API_KEY for youtube_search tool")
        print("   4. Re-run this program.")
        sys.exit(1)

    setup_readline()
    load_chat_history()

    # Create the agent graph with authorization
    app = create_agent_graph()
    if not app:
        print("❌ Failed to initialize the agent. Check your API key.")
        sys.exit(1)

    print_welcome()
    run_chat_loop(app)
    sys.exit(0)

if __name__ == "__main__":
    main()
