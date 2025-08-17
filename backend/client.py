#!/usr/bin/env python3
"""
API Client Examples for LangChain Agent Server
This demonstrates how to interact with your LangChain agent through the API
"""

import requests
import json
import time

BASE_URL = "http://localhost:8000"

class LangChainAgentClient:
    def __init__(self, base_url=BASE_URL):
        self.base_url = base_url
        self.session_id = None

    def chat(self, message, session_id=None):
        """Send a chat message to the agent"""
        url = f"{self.base_url}/chat"
        data = {
            "message": message,
            "session_id": session_id or self.session_id
        }

        response = requests.post(url, json=data)
        if response.status_code == 200:
            result = response.json()
            self.session_id = result["session_id"]  # Store session ID for future requests
            return result
        else:
            raise Exception(f"API Error: {response.status_code} - {response.text}")

    def get_authorization_request(self, request_id):
        """Get details of an authorization request"""
        url = f"{self.base_url}/authorization/{request_id}"
        response = requests.get(url)

        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"API Error: {response.status_code} - {response.text}")

    def authorize(self, request_id, action, modified_params=None):
        """Respond to an authorization request"""
        url = f"{self.base_url}/authorize"
        data = {
            "request_id": request_id,
            "action": action,  # 'approve', 'deny', or 'modify'
            "modified_params": modified_params
        }

        response = requests.post(url, json=data)
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"API Error: {response.status_code} - {response.text}")

    def list_tools(self):
        """Get list of available tools"""
        url = f"{self.base_url}/tools"
        response = requests.get(url)

        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"API Error: {response.status_code} - {response.text}")

    def get_session_history(self, session_id=None):
        """Get chat history for a session"""
        sid = session_id or self.session_id
        if not sid:
            raise Exception("No session ID available")

        url = f"{self.base_url}/sessions/{sid}/history"
        response = requests.get(url)

        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"API Error: {response.status_code} - {response.text}")

    def list_sessions(self):
        """List all sessions"""
        url = f"{self.base_url}/sessions"
        response = requests.get(url)

        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"API Error: {response.status_code} - {response.text}")

def example_basic_chat():
    """Example: Basic chat without authorization"""
    print("=== Basic Chat Example ===")
    client = LangChainAgentClient()

    try:
        # Simple chat that doesn't require authorization
        response = client.chat("What's the current time?")
        print(f"AI Response: {response['response']}")
        print(f"Session ID: {response['session_id']}")

        # Follow up message
        response = client.chat("Calculate 25 * 4")
        print(f"AI Response: {response['response']}")

    except Exception as e:
        print(f"Error: {e}")

def example_authorization_workflow():
    """Example: Handling authorization for sensitive tools"""
    print("\n=== Authorization Workflow Example ===")
    client = LangChainAgentClient()

    try:
        # Request something that requires authorization (Gmail access)
        response = client.chat("Read my latest emails")

        if response["requires_authorization"]:
            print("Authorization required!")
            print(f"Authorization Request ID: {response['authorization_request_id']}")

            # Get authorization details
            auth_details = client.get_authorization_request(response['authorization_request_id'])
            print(f"Authorization Details: {json.dumps(auth_details, indent=2)}")

            # Approve the authorization (in a real app, you'd show this to the user)
            print("Approving authorization...")
            auth_response = client.authorize(response['authorization_request_id'], "approve")
            print(f"Authorization Result: {auth_response}")

            # Now retry the original request
            print("Retrying original request with authorization...")
            final_response = client.chat("Read my latest emails")
            print(f"Final Response: {final_response['response']}")
        else:
            print(f"Direct Response: {response['response']}")

    except Exception as e:
        print(f"Error: {e}")

def example_deny_authorization():
    """Example: Denying authorization"""
    print("\n=== Deny Authorization Example ===")
    client = LangChainAgentClient()

    try:
        response = client.chat("Send an email to someone")

        if response["requires_authorization"]:
            print("Denying authorization...")
            auth_response = client.authorize(response['authorization_request_id'], "deny")
            print(f"Deny Result: {auth_response}")

            # Try the request again
            final_response = client.chat("Send an email to someone")
            print(f"Response after denial: {final_response['response']}")

    except Exception as e:
        print(f"Error: {e}")

def example_modify_parameters():
    """Example: Modifying tool parameters during authorization"""
    print("\n=== Modify Parameters Example ===")
    client = LangChainAgentClient()

    try:
        response = client.chat("Read my top 10 emails")

        if response["requires_authorization"]:
            # Modify parameters to read only 3 emails instead of 10
            modified_params = {
                "read_gmail_messages": {"top": 3}
            }

            print("Modifying parameters to read only 3 emails...")
            auth_response = client.authorize(
                response['authorization_request_id'],
                "approve",
                modified_params
            )
            print(f"Modification Result: {auth_response}")

            # Retry with modified parameters
            final_response = client.chat("Read my emails")
            print(f"Response with modified params: {final_response['response']}")

    except Exception as e:
        print(f"Error: {e}")

def example_session_management():
    """Example: Managing sessions and history"""
    print("\n=== Session Management Example ===")
    client = LangChainAgentClient()

    try:
        # Have a conversation
        client.chat("Hello, my name is Alice")
        client.chat("What's 2+2?")
        client.chat("What did I tell you my name was?")

        # Get session history
        history = client.get_session_history()
        print("Session History:")
        for msg in history['messages']:
            print(f"  {msg['type']}: {msg['content'][:100]}...")

        # List all sessions
        sessions = client.list_sessions()
        print(f"\nAll Sessions: {len(sessions['sessions'])} total")

    except Exception as e:
        print(f"Error: {e}")

def example_tool_listing():
    """Example: List available tools"""
    print("\n=== Tool Listing Example ===")
    client = LangChainAgentClient()

    try:
        tools = client.list_tools()
        print("Available Tools:")
        for tool in tools['tools']:
            auth_status = "🔐 Requires Auth" if tool['requires_authorization'] else "✅ Safe"
            print(f"  {auth_status} {tool['name']}: {tool['description']}")

    except Exception as e:
        print(f"Error: {e}")

def interactive_chat():
    """Interactive chat session"""
    print("\n=== Interactive Chat ===")
    print("Type 'quit' to exit, 'tools' to list tools, 'history' to see history")

    client = LangChainAgentClient()

    while True:
        try:
            user_input = input("\nYou: ").strip()

            if user_input.lower() == 'quit':
                break
            elif user_input.lower() == 'tools':
                tools = client.list_tools()
                print("\nAvailable Tools:")
                for tool in tools['tools']:
                    auth_status = "🔐" if tool['requires_authorization'] else "✅"
                    print(f"  {auth_status} {tool['name']}: {tool['description']}")
                continue
            elif user_input.lower() == 'history':
                if client.session_id:
                    history = client.get_session_history()
                    print("\nChat History:")
                    for msg in history['messages'][-10:]:  # Show last 10 messages
                        role = "You" if msg['type'] == 'human' else "AI"
                        content = msg['content'][:100] + "..." if len(msg['content']) > 100 else msg['content']
                        print(f"  {role}: {content}")
                else:
                    print("No active session")
                continue

            if not user_input:
                continue

            response = client.chat(user_input)

            if response["requires_authorization"]:
                print(f"\n🔐 This action requires authorization.")
                print("Authorization details:")
                auth_details = client.get_authorization_request(response['authorization_request_id'])
                for tool_call in auth_details['tool_calls']:
                    print(f"  - {tool_call['tool_name']}: {tool_call['description']}")
                    print(f"    Parameters: {tool_call['parameters']}")

                while True:
                    choice = input("\nChoose: (a)pprove, (d)eny, (m)odify: ").lower().strip()
                    if choice == 'a':
                        client.authorize(response['authorization_request_id'], "approve")
                        print("✅ Approved! Executing...")
                        retry_response = client.chat(user_input)
                        print(f"AI: {retry_response['response']}")
                        break
