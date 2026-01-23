"""
FastAPI Application - Chat Messaging Service

Main application entry point with API endpoints and WebSocket support.
"""

from fastapi import FastAPI, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.database import get_db, engine, Base
from app.models import Message
from app.schemas import MessageCreate, MessageResponse, MessageListResponse
from app.services.message_service import MessageService
from app.websocket_manager import connection_manager
from app.config import settings

# Create database tables on startup
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Realtime Chat Queue - Messaging Service",
    description="A production-ready messaging service with queue-based delivery",
    version="1.0.0"
)


@app.get("/")
async def root():
    return {
        "message": "Realtime Chat Queue Service",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.post("/messages", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def send_message(
    request: MessageCreate,
    db: Session = Depends(get_db)
):
    """
    Send a message to a chat.
    
    The message is:
    1. Stored in the database
    2. Queued in Redis Stream for async processing
    3. Processed by consumer worker for delivery
    """
    try:
        message = MessageService.create_message(db, request)
        message_dict = message.to_dict()
        message_dict["created_at"] = message.created_at.isoformat() if message.created_at else None
        return MessageResponse(**message_dict)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@app.get("/messages/chat/{chat_id}", response_model=MessageListResponse)
async def get_chat_messages(
    chat_id: str,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """Get messages for a chat with pagination"""
    messages, total = MessageService.get_messages_by_chat(db, chat_id, limit, offset)
    message_list = [
        MessageResponse(
            message_id=m.message_id,
            chat_id=m.chat_id,
            sender_id=m.sender_id,
            message=m.message,
            status=m.status,
            created_at=m.created_at
        )
        for m in messages
    ]
    return MessageListResponse(
        messages=message_list,
        total=total,
        limit=limit,
        offset=offset
    )


@app.get("/messages/pending/{user_id}", response_model=MessageListResponse)
async def get_pending_messages(
    user_id: str,
    db: Session = Depends(get_db)
):
    """Get pending messages for a user (for offline delivery)"""
    messages = MessageService.get_pending_messages_for_user(db, user_id)
    message_list = [
        MessageResponse(
            message_id=m.message_id,
            chat_id=m.chat_id,
            sender_id=m.sender_id,
            message=m.message,
            status=m.status,
            created_at=m.created_at
        )
        for m in messages
    ]
    return MessageListResponse(
        messages=message_list,
        total=len(message_list),
        limit=len(message_list),
        offset=0
    )


@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    """
    WebSocket endpoint for real-time message delivery.
    
    When a user connects:
    1. Register connection
    2. Send any pending messages
    3. Keep connection alive for real-time delivery
    """
    await connection_manager.connect(websocket, user_id)
    
    # Send pending messages when user connects
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        pending_messages = MessageService.get_pending_messages_for_user(db, user_id)
        for message in pending_messages:
            await connection_manager.send_personal_message(
                user_id,
                {
                    "type": "message",
                    "data": message.to_dict()
                }
            )
            # Mark as delivered
            MessageService.mark_message_delivered(db, message.message_id, user_id)
    finally:
        db.close()
    
    try:
        # Keep connection alive and handle incoming messages
        while True:
            data = await websocket.receive_text()
            # Echo back (or handle client messages)
            await websocket.send_json({"type": "ack", "data": data})
    except WebSocketDisconnect:
        await connection_manager.disconnect(user_id)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
