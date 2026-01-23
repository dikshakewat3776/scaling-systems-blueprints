"""
WebSocket Manager

Manages WebSocket connections for real-time message delivery.
Tracks online users and delivers messages via WebSocket.
"""

from typing import Dict, Set
from fastapi import WebSocket
import json
import asyncio


class ConnectionManager:
    """
    Manages WebSocket connections for real-time messaging.
    
    Features:
    - Track online users
    - Deliver messages to connected users
    - Handle disconnections gracefully
    """
    
    def __init__(self):
        # Map user_id -> WebSocket connection
        self.active_connections: Dict[str, WebSocket] = {}
        # Set of all connected user IDs
        self.connected_users: Set[str] = set()
        # Lock for thread-safe operations
        self.lock = asyncio.Lock()
    
    async def connect(self, websocket: WebSocket, user_id: str) -> bool:
        """
        Connect a user via WebSocket.
        
        Args:
            websocket: WebSocket connection
            user_id: User identifier
            
        Returns:
            bool: True if connected successfully
        """
        await websocket.accept()
        
        async with self.lock:
            # If user already connected, close old connection
            if user_id in self.active_connections:
                try:
                    await self.active_connections[user_id].close()
                except:
                    pass
            
            self.active_connections[user_id] = websocket
            self.connected_users.add(user_id)
        
        return True
    
    async def disconnect(self, user_id: str):
        """Disconnect a user"""
        async with self.lock:
            if user_id in self.active_connections:
                try:
                    await self.active_connections[user_id].close()
                except:
                    pass
                del self.active_connections[user_id]
                self.connected_users.discard(user_id)
    
    async def send_personal_message(self, user_id: str, message: dict) -> bool:
        """
        Send a message to a specific user via WebSocket.
        
        Args:
            user_id: Target user ID
            message: Message data to send
            
        Returns:
            bool: True if sent successfully, False if user offline
        """
        async with self.lock:
            if user_id not in self.active_connections:
                return False
            
            websocket = self.active_connections[user_id]
        
        try:
            await websocket.send_json(message)
            return True
        except Exception as e:
            # Connection lost, remove from active connections
            await self.disconnect(user_id)
            return False
    
    def is_user_online(self, user_id: str) -> bool:
        """Check if a user is currently online"""
        return user_id in self.connected_users
    
    def get_online_users(self) -> Set[str]:
        """Get set of all online user IDs"""
        return self.connected_users.copy()


# Global instance
connection_manager = ConnectionManager()
