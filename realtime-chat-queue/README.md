# Realtime Chat Queue - WhatsApp-like Messaging System

A production-ready messaging backend demonstrating queue-based systems with ordering guarantees, at-least-once delivery, and async processing.

## 🎯 Why This Matters

Modern messaging systems like WhatsApp handle billions of messages daily. This project demonstrates the core patterns used in production messaging systems:

- **Queue-based architecture** for reliable message delivery
- **Ordering guarantees** per conversation
- **At-least-once delivery** for message reliability
- **Async processing** for scalability
- **Consumer groups** for parallel processing
- **Backpressure handling** for system stability

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.11+

### Run with Docker Compose

```bash
cd realtime-chat-queue
docker-compose up --build
```

The service will be available at `http://localhost:8000` with interactive API docs at `/docs`.

### Run Locally

For local development with Python (outside Docker):

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Create environment file:**
   
   Create a `.env` file in the project root:
   ```bash
   cat > .env << 'EOF'
   DATABASE_URL=postgresql://chat:chat123@localhost:5434/chat_db
   REDIS_URL=redis://localhost:6379/0
   ENVIRONMENT=development
   EOF
   ```
   
   **Note:** PostgreSQL uses port `5434` by default to avoid conflicts. Adjust if needed.

3. **Start Docker services (PostgreSQL and Redis):**
   ```bash
   docker-compose up -d redis postgres
   ```
   
   Wait for services to be healthy:
   ```bash
   docker-compose ps
   ```

4. **Run database migrations:**
   ```bash
   alembic upgrade head
   ```

5. **Start the API server:**
   ```bash
   uvicorn app.main:app --reload
   ```

6. **Start the message consumer worker (in a separate terminal):**
   ```bash
   python -m app.worker.consumer
   ```

The API will be available at `http://localhost:8000` and WebSocket at `ws://localhost:8000/ws/{user_id}`.

## 📚 API Documentation

### POST /messages

Send a message to a chat.

**Request Body:**
```json
{
  "chat_id": "chat_123",
  "sender_id": "user_456",
  "message": "Hello, world!",
  "message_id": "msg_789"
}
```

**Response (201 Created):**
```json
{
  "message_id": "msg_789",
  "chat_id": "chat_123",
  "sender_id": "user_456",
  "message": "Hello, world!",
  "status": "QUEUED",
  "created_at": "2024-01-15T10:30:00Z"
}
```

### GET /messages/chat/{chat_id}

Get messages for a chat (paginated).

**Query Parameters:**
- `limit`: Number of messages to return (default: 50)
- `offset`: Offset for pagination (default: 0)

### WebSocket: ws://localhost:8000/ws/{user_id}

Connect to receive real-time messages.

**Connection:**
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/user_123');
ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  console.log('Received:', message);
};
```

## 🏗️ Architecture

```
┌─────────┐
│  Client │
└────┬────┘
     │ POST /messages
     │
     ▼
┌─────────────────┐
│   FastAPI App   │
│  ┌───────────┐  │
│  │  Message  │  │
│  │   API     │  │
│  └─────┬─────┘  │
│        │        │
│  ┌─────▼─────┐  │
│  │  Message  │  │
│  │  Service  │  │
│  └─────┬─────┘  │
└────────┼────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
┌────────┐ ┌──────────┐
│PostgreSQL│ │Redis Stream│
│(Messages)│ │  (Queue)   │
└────────┘ └─────┬────┘
                 │
                 ▼
         ┌──────────────┐
         │   Consumer   │
         │    Worker    │
         └──────┬───────┘
                │
                ▼
         ┌──────────────┐
         │  WebSocket   │
         │   Delivery   │
         └──────────────┘
```

## ❓ Questions & Answers

### Q1: Why Is Ordering Per Chat (Not Global)?

**Answer:**

In messaging systems, we need **per-chat ordering**, not global ordering across all chats. Here's why:

**The Problem with Global Ordering:**
- If we globally order all messages, a slow chat would block messages from all other chats
- User A sending a message in Chat 1 shouldn't delay User B's message in Chat 2
- Global ordering creates unnecessary dependencies between unrelated conversations

**Per-Chat Ordering Benefits:**
1. **Parallelism**: Different chats can be processed independently
2. **Performance**: Slow chats don't block fast chats
3. **Scalability**: Can partition by chat_id across multiple consumers
4. **User Experience**: Messages in each conversation appear in correct order

**Implementation:**
- Redis Streams uses `chat_id` as the stream key
- Each chat gets its own stream: `chat:{chat_id}`
- Consumers process each stream independently
- Messages within a chat are ordered by sequence number

**Example:**
```
Chat 1: [msg1, msg2, msg3] ← Ordered
Chat 2: [msgA, msgB, msgC] ← Ordered independently
Chat 3: [msgX, msgY, msgZ] ← Ordered independently

All three chats process in parallel!
```

---

### Q2: Why Is At-Least-Once Delivery Acceptable?

**Answer:**

At-least-once delivery means a message may be delivered **one or more times**, but never zero times. This is acceptable (and often preferred) in messaging systems.

**Why Not Exactly-Once?**
- Exactly-once delivery is extremely difficult to achieve in distributed systems
- Requires complex coordination and can impact performance
- Often not worth the complexity for messaging use cases

**Why At-Least-Once Works:**
1. **Idempotency**: Messages have unique `message_id` for deduplication
2. **User Experience**: Receiving a message twice is better than missing it
3. **Performance**: Simpler implementation, better throughput
4. **Reliability**: Guarantees no message loss

**Handling Duplicates:**
- Client checks `message_id` before displaying
- Database has unique constraint on `message_id`
- WebSocket delivery checks if message already delivered
- Consumer tracks processed message IDs

**Trade-offs:**
- ✅ No message loss
- ✅ Better performance
- ✅ Simpler implementation
- ⚠️ Possible duplicates (handled via deduplication)

**Real-World Example:**
WhatsApp, Telegram, and most messaging apps use at-least-once delivery. Users rarely notice duplicates because:
- Network retries are usually fast
- Deduplication happens at multiple layers
- Duplicates are filtered before display

---

### Q3: How Are Offline Users Handled?

**Answer:**

Offline users need messages delivered when they come back online. This is handled through a combination of:

1. **Message Persistence**: All messages stored in PostgreSQL
2. **Delivery Status Tracking**: Track which users received which messages
3. **WebSocket Reconnection**: When user reconnects, fetch undelivered messages
4. **Polling Fallback**: Periodic sync for missed messages

**Flow for Offline User:**

```
User sends message → Stored in DB → Queued in Redis Stream
                                    │
                                    ▼
                            Consumer processes message
                                    │
                                    ├─→ Online user? → Deliver via WebSocket
                                    │
                                    └─→ Offline user? → Mark as PENDING
                                                         │
                                    User comes online ←──┘
                                    │
                                    ▼
                            Fetch PENDING messages
                                    │
                                    ▼
                            Deliver via WebSocket
                                    │
                                    ▼
                            Mark as DELIVERED
```

**Implementation Details:**

1. **Message Status:**
   - `QUEUED`: Message in queue, not yet processed
   - `PENDING`: Processed but user offline, waiting for delivery
   - `DELIVERED`: Successfully delivered to user
   - `FAILED`: Delivery failed after retries

2. **Reconnection Handling:**
   ```python
   # When user connects via WebSocket
   async def on_connect(user_id: str):
       # Fetch undelivered messages
       pending = get_pending_messages(user_id)
       for message in pending:
           await send_via_websocket(user_id, message)
           mark_as_delivered(message.id, user_id)
   ```

3. **Polling Fallback:**
   - Client periodically polls `/messages/pending/{user_id}`
   - Ensures messages aren't lost if WebSocket fails
   - Acts as backup delivery mechanism

4. **Message Retention:**
   - Keep undelivered messages for 30 days
   - After that, mark as expired
   - User can still see in chat history

**Benefits:**
- ✅ No message loss for offline users
- ✅ Automatic delivery on reconnection
- ✅ Works even with unreliable networks
- ✅ Fallback mechanisms ensure delivery

---

## 🔑 Key Features

### 1. Partitioning by Chat ID

Messages are partitioned by `chat_id` to enable:
- Parallel processing of different chats
- Independent scaling per chat
- Isolation of slow/fast chats

**Implementation:**
```python
# Each chat gets its own Redis Stream
stream_key = f"chat:{chat_id}"
redis_client.xadd(stream_key, message_data)
```

### 2. Order Preservation

Messages within a chat maintain order using:
- Redis Streams sequence numbers
- Single consumer per chat partition
- Sequential processing within partition

### 3. Retry on Failure

Consumer implements retry logic:
- Exponential backoff for transient failures
- Dead letter queue for permanent failures
- Max retry attempts (default: 3)

### 4. Deduplication

Prevents duplicate messages using:
- Unique `message_id` in database
- Redis Set for processed message tracking
- Client-side deduplication

### 5. Consumer Groups

Redis Streams consumer groups enable:
- Multiple workers processing same stream
- Load balancing across consumers
- Automatic failover if consumer dies

## 🧪 Testing Scenarios

### Scenario 1: Message Ordering

Send multiple messages to the same chat and verify they're delivered in order.

### Scenario 2: Offline User

1. Send message to offline user
2. Verify message stored as PENDING
3. User connects via WebSocket
4. Verify message delivered automatically

### Scenario 3: Consumer Failure

1. Start consumer
2. Send messages
3. Kill consumer mid-processing
4. Restart consumer
5. Verify all messages eventually delivered

### Scenario 4: Duplicate Messages

1. Send same message_id twice
2. Verify only one stored in database
3. Verify only one delivered to user

## 🛠️ Tech Stack

- **FastAPI**: Modern Python web framework
- **PostgreSQL**: Persistent message storage
- **Redis Streams**: Message queue with ordering
- **WebSocket**: Real-time message delivery
- **SQLAlchemy**: ORM for database operations
- **Alembic**: Database migrations

## 📊 Database Schema

```sql
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id VARCHAR(100) UNIQUE NOT NULL,
    chat_id VARCHAR(100) NOT NULL,
    sender_id VARCHAR(100) NOT NULL,
    message TEXT NOT NULL,
    status VARCHAR(20) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_chat_id (chat_id),
    INDEX idx_sender_id (sender_id),
    INDEX idx_status (status)
);

CREATE TABLE message_deliveries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id VARCHAR(100) NOT NULL,
    user_id VARCHAR(100) NOT NULL,
    status VARCHAR(20) NOT NULL,
    delivered_at TIMESTAMP,
    UNIQUE(message_id, user_id),
    INDEX idx_user_status (user_id, status)
);
```

## 🎓 What This Project Demonstrates

### 1. Async Processing
- Messages processed asynchronously via queue
- Non-blocking API responses
- Background workers handle delivery

### 2. At-Least-Once Delivery
- Messages guaranteed to be delivered
- Deduplication prevents duplicates
- Retry mechanism ensures delivery

### 3. Ordering Guarantees
- Per-chat ordering maintained
- Redis Streams sequence numbers
- Sequential processing within partition

### 4. Consumer Groups
- Multiple workers process messages
- Load balancing across consumers
- Automatic failover

### 5. Backpressure Handling
- Queue size monitoring
- Consumer rate limiting
- Graceful degradation

---

**Built as part of the [Scaling Systems Blueprints](../README.md) learning series.**
