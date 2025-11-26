import asyncio
import json
import yaml
import os
from typing import Dict, Any
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

from mcp_servers.multiMCP import MultiMCP
from coordinator import Coordinator
from io_handler import IOHandler
from memory_utils.auto_init_indices import initialize_all_indices

load_dotenv()

app = FastAPI()

# Mount static files for the frontend
app.mount("/static", StaticFiles(directory="static", html=True), name="static")

@app.get("/")
async def get():
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/static/index.html")

# --- WebSocket IO Handler ---
class WebSocketIOHandler(IOHandler):
    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        self.input_future = None

    async def output(self, message_type: str, data: Any):
        """Send structured data to the frontend"""
        try:
            await self.websocket.send_json({
                "type": message_type,
                "data": data
            })
        except Exception as e:
            print(f"Error sending to websocket: {e}")

    async def input(self, prompt: str, data: Any = None) -> str:
        """Wait for user input (HITL) via WebSocket"""
        # Send request for input
        await self.output("hitl_request", {"prompt": prompt, "context": data})
        
        # Create a future to wait for the response
        self.input_future = asyncio.get_running_loop().create_future()
        try:
            return await self.input_future
        finally:
            self.input_future = None

    def resolve_input(self, value: str):
        """Called when response is received from WebSocket"""
        if self.input_future and not self.input_future.done():
            self.input_future.set_result(value)

# --- Connection Manager ---
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[WebSocket, Dict[str, Any]] = {}

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        # Initialize MultiMCP for this connection (or share a global one if stateless)
        # For now, we'll share a global MultiMCP for efficiency, but create a new Coordinator
        io_handler = WebSocketIOHandler(websocket)
        coordinator = Coordinator(global_multi_mcp, io_handler=io_handler)
        
        self.active_connections[websocket] = {
            "coordinator": coordinator,
            "io_handler": io_handler,
            "task": None
        }

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            # Cancel any running task
            task = self.active_connections[websocket]["task"]
            if task and not task.done():
                task.cancel()
            del self.active_connections[websocket]

    async def handle_message(self, websocket: WebSocket, data: dict):
        connection = self.active_connections.get(websocket)
        if not connection:
            return

        coordinator = connection["coordinator"]
        io_handler = connection["io_handler"]
        msg_type = data.get("type")

        if msg_type == "query":
            # Start coordinator run in background
            query = data.get("query")
            hitl_config = data.get("hitl_config", {})
            
            # Cancel previous task if any
            if connection["task"] and not connection["task"].done():
                connection["task"].cancel()
            
            # Create new task
            task = asyncio.create_task(coordinator.run(query, hitl_config))
            connection["task"] = task
            
        elif msg_type == "hitl_response":
            # Resolve pending input
            response = data.get("response")
            io_handler.resolve_input(response)

manager = ConnectionManager()
global_multi_mcp = None

@app.on_event("startup")
async def startup_event():
    global global_multi_mcp
    print("🔌 Loading MCP Servers...")
    try:
        with open("config/mcp_server_config.yaml", "r") as f:
            config_data = yaml.safe_load(f)
            server_configs = config_data.get("mcp_servers", [])
    except FileNotFoundError:
        print("❌ Config file not found: config/mcp_server_config.yaml")
        server_configs = []

    global_multi_mcp = MultiMCP(server_configs=server_configs)
    await global_multi_mcp.initialize()
    
    # Auto-init indices
    initialize_all_indices()
    print("✅ Server Ready")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            await manager.handle_message(websocket, data)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"WebSocket Error: {e}")
        manager.disconnect(websocket)
