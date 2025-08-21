import os
from langchain_core.tools import tool
from dotenv import load_dotenv
from pymongo.mongo_client import MongoClient
import requests
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
chatmap = {}
session_id = os.getenv("DEFAULT_SESSION_ID")
user_email = os.getenv("DEFAULT_USER_EMAIL")

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

from typing import Optional

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
