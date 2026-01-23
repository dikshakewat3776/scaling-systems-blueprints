"""
Pydantic Schemas for Request/Response Validation

Defines the data structures for API requests and responses.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class MessageCreate(BaseModel):
    """Schema for creating a new message"""
    chat_id: str = Field(..., description="Chat/Conversation identifier")
    sender_id: str = Field(..., description="User ID of the sender")
    message: str = Field(..., description="Message content")
    message_id: str = Field(..., description="Unique message identifier for deduplication")


class MessageResponse(BaseModel):
    """Schema for message response"""
    message_id: str
    chat_id: str
    sender_id: str
    message: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class MessageListResponse(BaseModel):
    """Schema for paginated message list"""
    messages: List[MessageResponse]
    total: int
    limit: int
    offset: int
