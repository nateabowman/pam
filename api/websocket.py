"""
WebSocket handlers for real-time updates in World P.A.M.
"""

from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, Set, Optional
import json
import asyncio
from datetime import datetime
from logger import get_logger


class ConnectionManager:
    """Manages WebSocket connections."""
    
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.subscriptions: Dict[WebSocket, Set[str]] = {}  # WebSocket -> set of scenario names
        self.logger = get_logger("websocket")
    
    async def connect(self, websocket: WebSocket):
        """Accept a new WebSocket connection."""
        await websocket.accept()
        self.active_connections.add(websocket)
        self.subscriptions[websocket] = set()
        self.logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection."""
        self.active_connections.discard(websocket)
        self.subscriptions.pop(websocket, None)
        self.logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Send message to a specific connection."""
        try:
            await websocket.send_json(message)
        except Exception as e:
            self.logger.error(f"Error sending message: {e}")
            self.disconnect(websocket)
    
    async def broadcast(self, message: dict, scenario: Optional[str] = None):
        """Broadcast message to all connections, optionally filtered by scenario subscription."""
        disconnected = set()
        for connection in self.active_connections:
            # If scenario specified, only send to subscribers
            if scenario:
                if scenario not in self.subscriptions.get(connection, set()):
                    continue
            
            try:
                await connection.send_json(message)
            except Exception as e:
                self.logger.error(f"Error broadcasting to connection: {e}")
                disconnected.add(connection)
        
        # Clean up disconnected connections
        for conn in disconnected:
            self.disconnect(conn)
    
    def subscribe(self, websocket: WebSocket, scenario: str):
        """Subscribe connection to a scenario."""
        if websocket in self.subscriptions:
            self.subscriptions[websocket].add(scenario)
            self.logger.debug(f"Subscribed to scenario: {scenario}")
    
    def unsubscribe(self, websocket: WebSocket, scenario: str):
        """Unsubscribe connection from a scenario."""
        if websocket in self.subscriptions:
            self.subscriptions[websocket].discard(scenario)
            self.logger.debug(f"Unsubscribed from scenario: {scenario}")


# Global connection manager
manager = ConnectionManager()


async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time updates.
    
    Message format:
    - Subscribe: {"action": "subscribe", "scenario": "global_war_risk"}
    - Unsubscribe: {"action": "unsubscribe", "scenario": "global_war_risk"}
    - Ping: {"action": "ping"}
    """
    await manager.connect(websocket)
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                action = message.get("action")
                
                if action == "subscribe":
                    scenario = message.get("scenario")
                    if scenario:
                        manager.subscribe(websocket, scenario)
                        await manager.send_personal_message({
                            "type": "subscribed",
                            "scenario": scenario
                        }, websocket)
                
                elif action == "unsubscribe":
                    scenario = message.get("scenario")
                    if scenario:
                        manager.unsubscribe(websocket, scenario)
                        await manager.send_personal_message({
                            "type": "unsubscribed",
                            "scenario": scenario
                        }, websocket)
                
                elif action == "ping":
                    await manager.send_personal_message({
                        "type": "pong"
                    }, websocket)
                
                else:
                    await manager.send_personal_message({
                        "type": "error",
                        "message": f"Unknown action: {action}"
                    }, websocket)
            
            except json.JSONDecodeError:
                await manager.send_personal_message({
                    "type": "error",
                    "message": "Invalid JSON"
                }, websocket)
            except Exception as e:
                manager.logger.error(f"Error processing WebSocket message: {e}")
                await manager.send_personal_message({
                    "type": "error",
                    "message": str(e)
                }, websocket)
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        manager.logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


async def broadcast_signal_update(signal_name: str, value: float, scenario: Optional[str] = None):
    """Broadcast signal update to subscribed connections."""
    await manager.broadcast({
        "type": "signal_update",
        "signal": signal_name,
        "value": value,
        "scenario": scenario,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }, scenario=scenario)


async def broadcast_evaluation_update(
    hypothesis_name: str,
    probability: float,
    details: Optional[dict] = None
):
    """Broadcast hypothesis evaluation update."""
    await manager.broadcast({
        "type": "evaluation_update",
        "hypothesis": hypothesis_name,
        "probability": probability,
        "details": details,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }, scenario=hypothesis_name)

