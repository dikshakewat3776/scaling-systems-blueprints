"""
Database Models

Defines the database schema for messages and deliveries.
"""

from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from app.database import Base


class Message(Base):
    """
    Message model representing a chat message.
    
    Messages are stored persistently and queued for delivery.
    Each message has a unique message_id for deduplication.
    """
    __tablename__ = "messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    message_id = Column(String(100), unique=True, nullable=False, index=True)
    chat_id = Column(String(100), nullable=False, index=True)
    sender_id = Column(String(100), nullable=False, index=True)
    message = Column(Text, nullable=False)
    status = Column(String(20), nullable=False, index=True)  # QUEUED, PENDING, DELIVERED, FAILED
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # Relationship to delivery records
    deliveries = relationship("MessageDelivery", back_populates="message", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "message_id": self.message_id,
            "chat_id": self.chat_id,
            "sender_id": self.sender_id,
            "message": self.message,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class MessageDelivery(Base):
    """
    Message delivery tracking.
    
    Tracks delivery status for each message to each recipient.
    Enables handling of offline users and delivery retries.
    """
    __tablename__ = "message_deliveries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    message_id = Column(String(100), ForeignKey("messages.message_id"), nullable=False, index=True)
    user_id = Column(String(100), nullable=False, index=True)
    status = Column(String(20), nullable=False)  # PENDING, DELIVERED, FAILED
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationship to message
    message = relationship("Message", back_populates="deliveries")

    # Unique constraint: one delivery record per message per user
    __table_args__ = (
        Index('idx_message_user', 'message_id', 'user_id', unique=True),
        Index('idx_user_status', 'user_id', 'status'),
    )

    def to_dict(self):
        return {
            "message_id": self.message_id,
            "user_id": self.user_id,
            "status": self.status,
            "delivered_at": self.delivered_at.isoformat() if self.delivered_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
