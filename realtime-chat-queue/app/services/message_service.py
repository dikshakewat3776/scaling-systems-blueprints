"""
Message Service

Handles message creation, storage, and queuing logic.
"""

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import and_
from fastapi import HTTPException, status
from app.models import Message, MessageDelivery
from app.schemas import MessageCreate
from app.redis_client import message_queue


class MessageService:
    """Service for message operations"""
    
    @staticmethod
    def create_message(db: Session, request: MessageCreate) -> Message:
        """
        Create a message and queue it for delivery.
        
        Flow:
        1. Store message in database
        2. Queue message in Redis Stream
        3. Return message with QUEUED status
        """
        # Create message record
        message = Message(
            message_id=request.message_id,
            chat_id=request.chat_id,
            sender_id=request.sender_id,
            message=request.message,
            status="QUEUED"
        )
        
        try:
            db.add(message)
            db.commit()
            db.refresh(message)
        except IntegrityError:
            # Message with this message_id already exists (duplicate)
            db.rollback()
            existing_message = db.query(Message).filter(
                Message.message_id == request.message_id
            ).first()
            if existing_message:
                return existing_message
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create message"
            )
        
        # Queue message in Redis Stream
        # This enables async processing by consumer workers
        try:
            message_queue.enqueue_message(
                chat_id=request.chat_id,
                message_data={
                    "message_id": request.message_id,
                    "chat_id": request.chat_id,
                    "sender_id": request.sender_id,
                    "message": request.message,
                }
            )
        except Exception as e:
            # If queuing fails, mark message as failed
            # In production, you might want to retry or use a dead letter queue
            message.status = "FAILED"
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to queue message: {str(e)}"
            )
        
        return message
    
    @staticmethod
    def get_messages_by_chat(
        db: Session,
        chat_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> tuple[list[Message], int]:
        """Get messages for a chat with pagination"""
        query = db.query(Message).filter(Message.chat_id == chat_id)
        total = query.count()
        messages = query.order_by(Message.created_at.desc()).offset(offset).limit(limit).all()
        return messages, total
    
    @staticmethod
    def get_pending_messages_for_user(db: Session, user_id: str) -> list[Message]:
        """Get pending messages for a user (offline delivery)"""
        # Get all deliveries that are pending for this user
        pending_deliveries = db.query(MessageDelivery).filter(
            and_(
                MessageDelivery.user_id == user_id,
                MessageDelivery.status == "PENDING"
            )
        ).all()
        
        message_ids = [d.message_id for d in pending_deliveries]
        if not message_ids:
            return []
        
        messages = db.query(Message).filter(Message.message_id.in_(message_ids)).all()
        return messages
    
    @staticmethod
    def mark_message_delivered(
        db: Session,
        message_id: str,
        user_id: str
    ) -> MessageDelivery:
        """Mark a message as delivered to a user"""
        delivery = db.query(MessageDelivery).filter(
            and_(
                MessageDelivery.message_id == message_id,
                MessageDelivery.user_id == user_id
            )
        ).first()
        
        if delivery:
            delivery.status = "DELIVERED"
            from datetime import datetime
            delivery.delivered_at = datetime.utcnow()
        else:
            # Create new delivery record
            delivery = MessageDelivery(
                message_id=message_id,
                user_id=user_id,
                status="DELIVERED"
            )
            db.add(delivery)
        
        db.commit()
        db.refresh(delivery)
        return delivery
    
    @staticmethod
    def create_delivery_record(
        db: Session,
        message_id: str,
        user_id: str,
        status: str = "PENDING"
    ) -> MessageDelivery:
        """Create a delivery record for tracking"""
        delivery = MessageDelivery(
            message_id=message_id,
            user_id=user_id,
            status=status
        )
        
        try:
            db.add(delivery)
            db.commit()
            db.refresh(delivery)
        except IntegrityError:
            # Delivery record already exists, update it
            db.rollback()
            delivery = db.query(MessageDelivery).filter(
                and_(
                    MessageDelivery.message_id == message_id,
                    MessageDelivery.user_id == user_id
                )
            ).first()
            if delivery:
                delivery.status = status
                db.commit()
                db.refresh(delivery)
        
        return delivery
