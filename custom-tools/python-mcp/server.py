#!/usr/bin/env python3
"""
MCP Chrome Tab Controller Server
Connects to Chrome extension via WebSocket to control browser tabs
"""

import asyncio
import json
import logging
import websockets
from typing import Dict, Any, Optional, List
import uuid
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MCPChromeServer:
    def __init__(self, host='localhost', port=8765):
        self.host = host
        self.port = port
        self.extension_connection = None
        self.client_connections = set()
        self.pending_requests = {}

    async def handle_connection(self, websocket):
        """Handle new WebSocket connections"""
        logger.info(f"New connection from {websocket.remote_address}")

        try:
            async for message in websocket:
                await self.handle_message(websocket, message)
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Connection closed: {websocket.remote_address}")
        except Exception as e:
            logger.error(f"Error handling connection: {e}")
        finally:
            await self.cleanup_connection(websocket)

    async def handle_message(self, websocket, message):
        """Process incoming messages"""
        try:
            data = json.loads(message)
            msg_type = data.get('type')

            if msg_type == 'role':
                await self.handle_role_message(websocket, data)
            elif msg_type == 'command':
                await self.handle_command(websocket, data)
            elif msg_type == 'response':
                await self.handle_response(data)
            else:
                logger.warning(f"Unknown message type: {msg_type}")

        except json.JSONDecodeError:
            logger.error("Invalid JSON received")
        except Exception as e:
            logger.error(f"Error processing message: {e}")

    async def handle_role_message(self, websocket, data):
        """Handle role identification messages"""
        role = data.get('role')

        if role == 'extension':
            self.extension_connection = websocket
            logger.info("Chrome extension connected")
        elif role == 'client':
            self.client_connections.add(websocket)
            logger.info(f"Client connected. Total clients: {len(self.client_connections)}")

    async def handle_command(self, websocket, data):
        """Handle command requests from clients"""
        if not self.extension_connection:
            error_response = {
                'type': 'error',
                'id': data.get('id'),
                'error': 'Chrome extension not connected'
            }
            await websocket.send(json.dumps(error_response))
            return

        # Forward command to extension and track the request
        request_id = data.get('id') or str(uuid.uuid4())
        self.pending_requests[request_id] = websocket

        command_msg = {
            'type': 'command',
            'id': request_id,
            'command': data.get('command'),
            'payload': data.get('payload', {})
        }

        await self.extension_connection.send(json.dumps(command_msg))

    async def handle_response(self, data):
        """Handle responses from the extension"""
        request_id = data.get('id')
        if request_id in self.pending_requests:
            client_ws = self.pending_requests.pop(request_id)
            try:
                await client_ws.send(json.dumps(data))
            except websockets.exceptions.ConnectionClosed:
                logger.warning(f"Client connection closed before response could be sent")

    async def cleanup_connection(self, websocket):
        """Clean up when a connection is closed"""
        if websocket == self.extension_connection:
            self.extension_connection = None
            logger.info("Chrome extension disconnected")
        elif websocket in self.client_connections:
            self.client_connections.remove(websocket)
            logger.info(f"Client disconnected. Remaining clients: {len(self.client_connections)}")

        # Remove any pending requests for this websocket
        to_remove = [req_id for req_id, ws in self.pending_requests.items() if ws == websocket]
        for req_id in to_remove:
            del self.pending_requests[req_id]

    # MCP Tool Methods
    async def list_tabs(self) -> Dict[str, Any]:
        """List all open tabs"""
        if not self.extension_connection:
            return {'error': 'Chrome extension not connected'}

        request_id = str(uuid.uuid4())
        command = {
            'type': 'command',
            'id': request_id,
            'command': 'list_tabs'
        }

        # Send command and wait for response
        future = asyncio.Future()
        self.pending_requests[request_id] = future

        await self.extension_connection.send(json.dumps(command))

        try:
            response = await asyncio.wait_for(future, timeout=10.0)
            return response
        except asyncio.TimeoutError:
            return {'error': 'Request timeout'}

    async def open_tab(self, url: str, active: bool = True) -> Dict[str, Any]:
        """Open a new tab with the specified URL"""
        if not self.extension_connection:
            return {'error': 'Chrome extension not connected'}

        request_id = str(uuid.uuid4())
        command = {
            'type': 'command',
            'id': request_id,
            'command': 'open_tab',
            'payload': {'url': url, 'active': active}
        }

        future = asyncio.Future()
        self.pending_requests[request_id] = future

        await self.extension_connection.send(json.dumps(command))

        try:
            response = await asyncio.wait_for(future, timeout=10.0)
            return response
        except asyncio.TimeoutError:
            return {'error': 'Request timeout'}

    async def close_tab(self, tab_id: int) -> Dict[str, Any]:
        """Close a tab by ID"""
        if not self.extension_connection:
            return {'error': 'Chrome extension not connected'}

        request_id = str(uuid.uuid4())
        command = {
            'type': 'command',
            'id': request_id,
            'command': 'close_tab',
            'payload': {'tabId': tab_id}
        }

        future = asyncio.Future()
        self.pending_requests[request_id] = future

        await self.extension_connection.send(json.dumps(command))

        try:
            response = await asyncio.wait_for(future, timeout=10.0)
            return response
        except asyncio.TimeoutError:
            return {'error': 'Request timeout'}

    async def switch_tab(self, tab_id: int, window_id: Optional[int] = None) -> Dict[str, Any]:
        """Switch to a specific tab"""
        if not self.extension_connection:
            return {'error': 'Chrome extension not connected'}

        request_id = str(uuid.uuid4())
        payload = {'tabId': tab_id}
        if window_id:
            payload['windowId'] = window_id

        command = {
            'type': 'command',
            'id': request_id,
            'command': 'switch_tab',
            'payload': payload
        }

        future = asyncio.Future()
        self.pending_requests[request_id] = future

        await self.extension_connection.send(json.dumps(command))

        try:
            response = await asyncio.wait_for(future, timeout=10.0)
            return response
        except asyncio.TimeoutError:
            return {'error': 'Request timeout'}

    async def reload_tab(self, tab_id: int) -> Dict[str, Any]:
        """Reload a specific tab"""
        if not self.extension_connection:
            return {'error': 'Chrome extension not connected'}

        request_id = str(uuid.uuid4())
        command = {
            'type': 'command',
            'id': request_id,
            'command': 'reload_tab',
            'payload': {'tabId': tab_id}
        }

        future = asyncio.Future()
        self.pending_requests[request_id] = future

        await self.extension_connection.send(json.dumps(command))

        try:
            response = await asyncio.wait_for(future, timeout=10.0)
            return response
        except asyncio.TimeoutError:
            return {'error': 'Request timeout'}

    async def navigate_tab(self, tab_id: int, url: str) -> Dict[str, Any]:
        """Navigate a specific tab to a new URL"""
        if not self.extension_connection:
            return {'error': 'Chrome extension not connected'}

        request_id = str(uuid.uuid4())
        command = {
            'type': 'command',
            'id': request_id,
            'command': 'navigate_tab',
            'payload': {'tabId': tab_id, 'url': url}
        }

        future = asyncio.Future()
        self.pending_requests[request_id] = future

        await self.extension_connection.send(json.dumps(command))

        try:
            response = await asyncio.wait_for(future, timeout=10.0)
            return response
        except asyncio.TimeoutError:
            return {'error': 'Request timeout'}

    async def start_server(self):
        """Start the WebSocket server"""
        logger.info(f"Starting MCP Chrome Server on {self.host}:{self.port}")

        # Create the WebSocket server - path routing is handled in handle_connection
        server = await websockets.serve(
            self.handle_connection,
            self.host,
            self.port
        )

        logger.info(f"MCP Chrome Server running on ws://{self.host}:{self.port}/ws")
        return server

# Example usage and testing
async def main():
    server = MCPChromeServer()
    ws_server = await server.start_server()

    # Keep the server running
    try:
        await ws_server.wait_closed()
    except KeyboardInterrupt:
        logger.info("Server shutting down...")
        ws_server.close()
        await ws_server.wait_closed()

if __name__ == "__main__":
    asyncio.run(main())
