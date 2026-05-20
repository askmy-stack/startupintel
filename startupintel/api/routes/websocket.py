"""WebSocket routes for real-time updates."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, UTC
from typing import Any
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from fastapi.responses import HTMLResponse

from startupintel.api.dependencies import get_db, get_redis_client
from startupintel.bots.base import BaseBot
from startupintel.bots.runway_bot import RunwayBot
from startupintel.bots.obituary_bot import ObituaryBot
from startupintel.bots.pmf_bot import PMFBot
from startupintel.bots.pivot_bot import PivotBot
from startupintel.bots.acqui_bot import AcquiBot
from startupintel.db.models import Startup
from startupintel.llm.client import get_llm_client
from startupintel.rag.retriever import get_retriever
from startupintel.events.producer import InMemoryEventProducer

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ws", tags=["websocket"])

# Active WebSocket connections
_connections: dict[str, WebSocket] = {}


class ConnectionManager:
    """Manage WebSocket connections."""
    
    def __init__(self):
        self._connections: dict[str, WebSocket] = {}
        self._user_rooms: dict[str, set[str]] = {}
    
    async def connect(self, websocket: WebSocket, client_id: str) -> None:
        """Accept and store a new connection."""
        await websocket.accept()
        self._connections[client_id] = websocket
        logger.info(f"WebSocket client connected: {client_id}")
    
    def disconnect(self, client_id: str) -> None:
        """Remove a connection."""
        if client_id in self._connections:
            del self._connections[client_id]
        logger.info(f"WebSocket client disconnected: {client_id}")
    
    async def send_personal_message(self, message: dict, client_id: str) -> None:
        """Send message to specific client."""
        if client_id in self._connections:
            await self._connections[client_id].send_text(json.dumps(message))
    
    async def broadcast(self, message: dict) -> None:
        """Broadcast message to all connected clients."""
        disconnected = []
        for client_id, connection in self._connections.items():
            try:
                await connection.send_text(json.dumps(message))
            except Exception:
                disconnected.append(client_id)
        
        # Clean up disconnected clients
        for client_id in disconnected:
            self.disconnect(client_id)


manager = ConnectionManager()


@router.websocket("/chat/{client_id}")
async def websocket_chat(websocket: WebSocket, client_id: str):
    """WebSocket endpoint for real-time chat.
    
    Protocol:
    - Client sends: {"type": "message", "content": "...", "conversation_id": "..."}
    - Server sends: {"type": "chunk", "content": "..."} (streaming)
    - Server sends: {"type": "complete", "content": "...", "suggested_actions": [...]}
    - Server sends: {"type": "error", "message": "..."}
    """
    await manager.connect(websocket, client_id)
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
            except json.JSONDecodeError:
                await manager.send_personal_message(
                    {"type": "error", "message": "Invalid JSON"},
                    client_id
                )
                continue
            
            msg_type = message.get("type", "message")
            
            if msg_type == "message":
                # Handle chat message
                content = message.get("content", "")
                conversation_id = message.get("conversation_id")
                
                # Echo back typing indicator
                await manager.send_personal_message(
                    {"type": "typing", "conversation_id": conversation_id},
                    client_id
                )
                
                # Simulate streaming response (replace with actual LLM streaming)
                response_text = f"I received your message: {content[:50]}..."
                words = response_text.split()
                
                for i, word in enumerate(words):
                    await manager.send_personal_message(
                        {
                            "type": "chunk",
                            "content": word + " ",
                            "conversation_id": conversation_id,
                            "index": i,
                        },
                        client_id
                    )
                    await asyncio.sleep(0.05)  # Simulate streaming delay
                
                # Send complete message
                await manager.send_personal_message(
                    {
                        "type": "complete",
                        "content": response_text,
                        "conversation_id": conversation_id or "new-id",
                        "suggested_actions": [
                            "Tell me more",
                            "Analyze runway",
                            "Check PMF",
                        ],
                        "timestamp": datetime.now(UTC).isoformat(),
                    },
                    client_id
                )
            
            elif msg_type == "ping":
                await manager.send_personal_message({"type": "pong"}, client_id)
            
            else:
                await manager.send_personal_message(
                    {"type": "error", "message": f"Unknown message type: {msg_type}"},
                    client_id
                )
                
    except WebSocketDisconnect:
        manager.disconnect(client_id)
    except Exception as e:
        logger.error(f"WebSocket error for {client_id}: {e}", exc_info=True)
        manager.disconnect(client_id)


@router.websocket("/bot-stream/{startup_id}")
async def websocket_bot_stream(websocket: WebSocket, startup_id: str):
    """WebSocket endpoint for streaming bot analysis results.
    
    Client sends: {"bot_name": "runway", "action": "start"}
    Server streams progress updates and final result.
    """
    client_id = f"bot-{startup_id}"
    await manager.connect(websocket, client_id)
    
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            bot_name = message.get("bot_name", "runway")
            action = message.get("action", "start")
            
            if action == "start":
                # Start bot analysis
                await manager.send_personal_message(
                    {
                        "type": "status",
                        "bot_name": bot_name,
                        "status": "starting",
                        "message": f"Starting {bot_name} analysis...",
                    },
                    client_id
                )
                
                # Simulate bot progress
                for progress in [10, 30, 50, 70, 90, 100]:
                    await manager.send_personal_message(
                        {
                            "type": "progress",
                            "bot_name": bot_name,
                            "progress": progress,
                            "message": f"Analyzing... {progress}%",
                        },
                        client_id
                    )
                    await asyncio.sleep(0.5)
                
                # Send final result
                await manager.send_personal_message(
                    {
                        "type": "complete",
                        "bot_name": bot_name,
                        "startup_id": startup_id,
                        "score": 65.5,
                        "risk_level": "medium",
                        "timestamp": datetime.now(UTC).isoformat(),
                    },
                    client_id
                )
    
    except WebSocketDisconnect:
        manager.disconnect(client_id)
    except Exception as e:
        logger.error(f"Bot stream error: {e}", exc_info=True)
        manager.disconnect(client_id)


@router.get("/demo")
async def websocket_demo_page() -> HTMLResponse:
    """Serve a simple WebSocket demo page."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>WebSocket Demo</title>
        <style>
            body { font-family: system-ui; max-width: 800px; margin: 40px auto; padding: 20px; }
            #messages { border: 1px solid #ccc; height: 300px; overflow-y: auto; padding: 10px; margin: 20px 0; }
            .message { margin: 5px 0; padding: 8px; background: #f0f0f0; border-radius: 4px; }
            .sent { background: #e3f2fd; text-align: right; }
            input { width: 70%; padding: 10px; font-size: 16px; }
            button { padding: 10px 20px; font-size: 16px; cursor: pointer; }
            #status { color: #666; font-size: 14px; margin: 10px 0; }
        </style>
    </head>
    <body>
        <h1>WebSocket Chat Demo</h1>
        <div id="status">Disconnected</div>
        <div id="messages"></div>
        <input type="text" id="messageInput" placeholder="Type a message...">
        <button onclick="sendMessage()">Send</button>
        <button onclick="connect()">Connect</button>
        <button onclick="disconnect()">Disconnect</button>
        
        <script>
            let ws = null;
            const clientId = 'demo-' + Math.random().toString(36).substr(2, 9);
            
            function connect() {
                if (ws) return;
                
                ws = new WebSocket(`ws://${window.location.host}/api/ws/chat/${clientId}`);
                
                ws.onopen = () => {
                    document.getElementById('status').textContent = 'Connected';
                    document.getElementById('status').style.color = 'green';
                };
                
                ws.onmessage = (event) => {
                    const data = JSON.parse(event.data);
                    const div = document.createElement('div');
                    div.className = 'message';
                    div.textContent = `[${data.type}] ${JSON.stringify(data)}`;
                    document.getElementById('messages').appendChild(div);
                    document.getElementById('messages').scrollTop = 999999;
                };
                
                ws.onclose = () => {
                    document.getElementById('status').textContent = 'Disconnected';
                    document.getElementById('status').style.color = 'red';
                    ws = null;
                };
            }
            
            function disconnect() {
                if (ws) {
                    ws.close();
                    ws = null;
                }
            }
            
            function sendMessage() {
                if (!ws) {
                    alert('Connect first!');
                    return;
                }
                const input = document.getElementById('messageInput');
                const message = input.value;
                if (message) {
                    ws.send(JSON.stringify({type: 'message', content: message}));
                    const div = document.createElement('div');
                    div.className = 'message sent';
                    div.textContent = 'You: ' + message;
                    document.getElementById('messages').appendChild(div);
                    input.value = '';
                }
            }
            
            document.getElementById('messageInput').addEventListener('keypress', (e) => {
                if (e.key === 'Enter') sendMessage();
            });
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html)
