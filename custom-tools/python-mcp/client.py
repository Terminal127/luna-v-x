#!/usr/bin/env python3
"""
Chrome Tab Controller Client
Uses the  server to control Chrome tabs
"""

import asyncio
import json
import websockets
import uuid
from typing import Dict, Any, Optional, List

class ChromeTabController:
    def __init__(self, server_url='ws://localhost:8765/ws'):
        self.server_url = server_url
        self.websocket = None
        self.pending_requests = {}

    async def connect(self):
        """Connect to the  server"""
        try:
            self.websocket = await websockets.connect(self.server_url)

            # Identify as a client
            await self.websocket.send(json.dumps({
                'type': 'role',
                'role': 'client'
            }))

            print("Connected to  Chrome Server")

            # Start message handler
            asyncio.create_task(self._message_handler())

        except Exception as e:
            print(f"Failed to connect: {e}")
            raise

    async def _message_handler(self):
        """Handle incoming messages from the server"""
        try:
            async for message in self.websocket:
                data = json.loads(message)
                request_id = data.get('id')

                if request_id in self.pending_requests:
                    future = self.pending_requests.pop(request_id)
                    future.set_result(data)
        except websockets.exceptions.ConnectionClosed:
            print("Connection to server closed")
        except Exception as e:
            print(f"Error in message handler: {e}")

    async def _send_command(self, command: str, payload: Dict = None) -> Dict[str, Any]:
        """Send a command to the server and wait for response"""
        if not self.websocket:
            raise ConnectionError("Not connected to server")

        request_id = str(uuid.uuid4())
        future = asyncio.Future()
        self.pending_requests[request_id] = future

        message = {
            'type': 'command',
            'id': request_id,
            'command': command,
            'payload': payload or {}
        }

        await self.websocket.send(json.dumps(message))

        try:
            response = await asyncio.wait_for(future, timeout=10.0)
            return response
        except asyncio.TimeoutError:
            self.pending_requests.pop(request_id, None)
            return {'error': 'Request timeout'}

    async def list_tabs(self) -> List[Dict]:
        """List all open Chrome tabs"""
        response = await self._send_command('list_tabs')

        if 'error' in response:
            print(f"Error listing tabs: {response['error']}")
            return []

        tabs = response.get('result', [])
        return tabs

    async def open_tab(self, url: str, active: bool = True) -> Dict[str, Any]:
        """Open a new tab with the specified URL"""
        response = await self._send_command('open_tab', {
            'url': url,
            'active': active
        })

        if 'error' in response:
            print(f"Error opening tab: {response['error']}")
            return {}

        return response.get('result', {})

    async def close_tab(self, tab_id: int) -> bool:
        """Close a tab by ID"""
        response = await self._send_command('close_tab', {'tabId': tab_id})

        if 'error' in response:
            print(f"Error closing tab: {response['error']}")
            return False

        return True

    async def switch_tab(self, tab_id: int, window_id: Optional[int] = None) -> bool:
        """Switch to a specific tab"""
        payload = {'tabId': tab_id}
        if window_id:
            payload['windowId'] = window_id

        response = await self._send_command('switch_tab', payload)

        if 'error' in response:
            print(f"Error switching tab: {response['error']}")
            return False

        return True

    async def reload_tab(self, tab_id: int) -> bool:
        """Reload a specific tab"""
        response = await self._send_command('reload_tab', {'tabId': tab_id})

        if 'error' in response:
            print(f"Error reloading tab: {response['error']}")
            return False

        return True

    async def navigate_tab(self, tab_id: int, url: str) -> bool:
        """Navigate a specific tab to a new URL"""
        response = await self._send_command('navigate_tab', {
            'tabId': tab_id,
            'url': url
        })

        if 'error' in response:
            print(f"Error navigating tab: {response['error']}")
            return False

        return True

    def print_tabs(self, tabs: List[Dict]):
        """Pretty print tab information"""
        if not tabs:
            print("No tabs found")
            return

        print(f"\n{'ID':<8} {'Active':<8} {'Title':<30} {'URL'}")
        print("-" * 80)

        for tab in tabs:
            tab_id = tab.get('id', 'N/A')
            active = '✓' if tab.get('active', False) else ''
            title = tab.get('title', 'No Title')[:30]
            url = tab.get('url', 'No URL')[:40]

            print(f"{tab_id:<8} {active:<8} {title:<30} {url}")

    async def disconnect(self):
        """Close the connection"""
        if self.websocket:
            await self.websocket.close()
            self.websocket = None

# Interactive CLI
async def interactive_mode():
    """Interactive command-line interface"""
    controller = ChromeTabController()

    try:
        await controller.connect()

        print("\nChrome Tab Controller - Interactive Mode")
        print("Commands:")
        print("  list         - List all tabs")
        print("  open <url>   - Open a new tab")
        print("  close <id>   - Close tab by ID")
        print("  switch <id>  - Switch to tab by ID")
        print("  reload <id>  - Reload tab by ID")
        print("  nav <id> <url> - Navigate tab to URL")
        print("  quit         - Exit")
        print()

        while True:
            command = input("chrome> ").strip().split()

            if not command:
                continue

            cmd = command[0].lower()

            if cmd == 'quit' or cmd == 'exit':
                break
            elif cmd == 'list':
                tabs = await controller.list_tabs()
                controller.print_tabs(tabs)
            elif cmd == 'open' and len(command) > 1:
                url = command[1]
                if not url.startswith(('http://', 'https://')):
                    url = 'https://' + url
                tab = await controller.open_tab(url)
                if tab:
                    print(f"Opened tab {tab.get('id')} with URL: {url}")
            elif cmd == 'close' and len(command) > 1:
                try:
                    tab_id = int(command[1])
                    if await controller.close_tab(tab_id):
                        print(f"Closed tab {tab_id}")
                except ValueError:
                    print("Invalid tab ID")
            elif cmd == 'switch' and len(command) > 1:
                try:
                    tab_id = int(command[1])
                    if await controller.switch_tab(tab_id):
                        print(f"Switched to tab {tab_id}")
                except ValueError:
                    print("Invalid tab ID")
            elif cmd == 'reload' and len(command) > 1:
                try:
                    tab_id = int(command[1])
                    if await controller.reload_tab(tab_id):
                        print(f"Reloaded tab {tab_id}")
                except ValueError:
                    print("Invalid tab ID")
            elif cmd == 'nav' and len(command) > 2:
                try:
                    tab_id = int(command[1])
                    url = command[2]
                    if not url.startswith(('http://', 'https://')):
                        url = 'https://' + url
                    if await controller.navigate_tab(tab_id, url):
                        print(f"Navigated tab {tab_id} to {url}")
                except ValueError:
                    print("Invalid tab ID")
            else:
                print("Invalid command or missing arguments")

    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        await controller.disconnect()

# Example automation script
async def automation_example():
    """Example of automated tab management"""
    controller = ChromeTabController()

    try:
        await controller.connect()

        print("Opening some example tabs...")

        # Open some tabs
        await controller.open_tab("https://github.com", active=False)
        await controller.open_tab("https://stackoverflow.com", active=False)
        await controller.open_tab("https://docs.python.org", active=True)

        await asyncio.sleep(2)

        # List all tabs
        print("\nCurrent tabs:")
        tabs = await controller.list_tabs()
        controller.print_tabs(tabs)

        # Switch to the first tab
        if tabs:
            first_tab = tabs[0]
            print(f"\nSwitching to tab: {first_tab.get('title')}")
            await controller.switch_tab(first_tab['id'])

        await asyncio.sleep(2)

        # Close tabs with specific patterns
        print("\nClosing GitHub and StackOverflow tabs...")
        tabs = await controller.list_tabs()
        for tab in tabs:
            url = tab.get('url', '').lower()
            if 'github.com' in url or 'stackoverflow.com' in url:
                await controller.close_tab(tab['id'])
                print(f"Closed: {tab.get('title')}")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        await controller.disconnect()

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "demo":
        asyncio.run(automation_example())
    else:
        asyncio.run(interactive_mode())
