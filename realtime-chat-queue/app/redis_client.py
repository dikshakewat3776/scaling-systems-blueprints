"""
Redis Client for Message Queue

Handles Redis Streams operations for message queuing.
Redis Streams provides:
- Ordered message delivery
- Consumer groups for parallel processing
- Automatic message acknowledgment
"""

import redis
import json
from typing import Dict, Any, Optional
from app.config import settings

redis_client = redis.from_url(settings.redis_url, decode_responses=True)


class MessageQueue:
    """
    Redis Streams-based message queue.
    
    Each chat gets its own stream: chat:{chat_id}
    This enables:
    - Per-chat ordering
    - Parallel processing of different chats
    - Independent scaling
    """
    
    STREAM_PREFIX = "chat:"
    CONSUMER_GROUP = "message_workers"
    
    def __init__(self, client: redis.Redis):
        self.client = client
    
    def get_stream_key(self, chat_id: str) -> str:
        """Get Redis Stream key for a chat"""
        return f"{self.STREAM_PREFIX}{chat_id}"
    
    def enqueue_message(self, chat_id: str, message_data: Dict[str, Any]) -> str:
        """
        Add message to queue for a specific chat.
        
        Args:
            chat_id: Chat identifier
            message_data: Message data to queue
            
        Returns:
            str: Stream entry ID
        """
        stream_key = self.get_stream_key(chat_id)
        
        # Add message to stream
        # Redis Streams automatically assigns sequence number for ordering
        entry_id = self.client.xadd(
            stream_key,
            {
                "message_id": message_data["message_id"],
                "chat_id": message_data["chat_id"],
                "sender_id": message_data["sender_id"],
                "message": message_data["message"],
                "data": json.dumps(message_data)
            },
            maxlen=10000  # Keep last 10k messages per chat
        )
        
        return entry_id
    
    def create_consumer_group(self, chat_id: str) -> None:
        """
        Create consumer group for a chat stream.
        
        Consumer groups enable:
        - Multiple workers processing same stream
        - Load balancing
        - Automatic failover
        """
        stream_key = self.get_stream_key(chat_id)
        
        try:
            # Create consumer group starting from beginning
            self.client.xgroup_create(
                stream_key,
                self.CONSUMER_GROUP,
                id="0",  # Start from beginning
                mkstream=True  # Create stream if it doesn't exist
            )
        except redis.exceptions.ResponseError as e:
            # Group already exists, that's fine
            if "BUSYGROUP" not in str(e):
                raise
    
    def read_messages(self, chat_id: str, consumer_name: str, count: int = 10) -> List[Dict[str, Any]]:
        """
        Read messages from stream for a consumer.
        
        Args:
            chat_id: Chat identifier
            consumer_name: Unique consumer identifier
            count: Number of messages to read
            
        Returns:
            List of message dictionaries
        """
        stream_key = self.get_stream_key(chat_id)
        
        # Ensure consumer group exists
        self.create_consumer_group(chat_id)
        
        # Read messages from stream
        # > means: read new messages not yet seen by this consumer
        messages = self.client.xreadgroup(
            self.CONSUMER_GROUP,
            consumer_name,
            {stream_key: ">"},
            count=count,
            block=1000  # Block for 1 second if no messages
        )
        
        result = []
        for stream, entries in messages:
            for entry_id, data in entries:
                message_data = json.loads(data.get("data", "{}"))
                message_data["_entry_id"] = entry_id
                message_data["_stream_key"] = stream_key
                result.append(message_data)
        
        return result
    
    def acknowledge_message(self, chat_id: str, entry_id: str) -> None:
        """
        Acknowledge message processing.
        
        After successful processing, acknowledge to remove from pending list.
        """
        stream_key = self.get_stream_key(chat_id)
        self.client.xack(stream_key, self.CONSUMER_GROUP, entry_id)
    
    def get_pending_messages(self, chat_id: str, consumer_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get pending messages (not yet acknowledged).
        
        Useful for retry logic when consumer fails.
        """
        stream_key = self.get_stream_key(chat_id)
        
        # Get pending entries
        pending = self.client.xpending_range(
            stream_key,
            self.CONSUMER_GROUP,
            min="-",
            max="+",
            count=100
        )
        
        result = []
        for entry in pending:
            entry_id = entry["message_id"]
            # Read the actual message
            messages = self.client.xrange(stream_key, entry_id, entry_id)
            if messages:
                _, data = messages[0]
                message_data = json.loads(data.get("data", "{}"))
                message_data["_entry_id"] = entry_id
                message_data["_stream_key"] = stream_key
                result.append(message_data)
        
        return result


# Global instance
message_queue = MessageQueue(redis_client)
