# Idempay - Payment Service with Idempotency

A production-ready mock payment service demonstrating idempotency patterns to prevent double payments in distributed systems.

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.11+

### Run with Docker Compose

```bash
cd payment-service-idempotency
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
   
   Create a `.env` file in the project root with the following content:
   ```bash
   cat > .env << 'EOF'
   DATABASE_URL=postgresql://idempay:idempay123@localhost:5433/idempay_db
   REDIS_URL=redis://localhost:6379/0
   ENVIRONMENT=development
   IDEMPOTENCY_KEY_TTL=86400
   EOF
   ```
   
   **Note:** PostgreSQL uses port `5433` by default to avoid conflicts with local PostgreSQL instances. If port 5432 is free on your system, you can:
   - Change the port mapping in `docker-compose.yml` from `5433:5432` to `5432:5432`
   - Update the `DATABASE_URL` in `.env` to use port `5432`

3. **Start Docker services (PostgreSQL and Redis):**
   ```bash
   docker-compose up -d redis postgres
   ```
   
   Wait for services to be healthy:
   ```bash
   docker-compose ps
   ```
   
   You should see both services with status `(healthy)`.

4. **Run database migrations:**
   ```bash
   alembic upgrade head
   ```
   
   This creates the `payments` table in PostgreSQL.

5. **Start the application:**
   ```bash
   uvicorn app.main:app --reload
   ```

The service will be available at `http://localhost:8000` with interactive API docs at `/docs`.

**Troubleshooting:**

- **"role does not exist" error**: 
  - Ensure Docker containers are running: `docker-compose ps`
  - Verify PostgreSQL container is healthy: `docker exec idempay-postgres pg_isready -U idempay`

- **Port conflicts**:
  - If port 5432 is already in use by a local PostgreSQL, the setup uses port 5433 by default
  - Check what's using port 5432: `lsof -i :5432`
  - Update `docker-compose.yml` and `.env` if you want to use a different port

- **Connection refused**:
  - Verify `.env` file exists and has correct database URL
  - Check Docker containers are running: `docker ps --filter "name=idempay"`
  - Test PostgreSQL connection: `PGPASSWORD=idempay123 psql -h localhost -p 5433 -U idempay -d idempay_db -c "SELECT 1;"`

- **Migration errors**:
  - Ensure database is accessible before running migrations
  - If you see "table already exists", you may need to drop and recreate: `docker-compose down -v` (⚠️ deletes data)

## 📚 API Documentation

### POST /pay

Process a payment request with idempotency protection.

**Headers:**
- `Idempotency-Key` (required): Unique key for idempotency (UUID recommended)

**Request Body:**
```json
{
  "order_id": "order_123",
  "amount": 100.50,
  "currency": "INR",
  "customer_id": "cust_456"
}
```

**Response (200 OK):**
```json
{
  "payment_id": "pay_abc123",
  "order_id": "order_123",
  "amount": 100.50,
  "status": "SUCCESS",
  "processed_at": "2024-01-15T10:30:00Z"
}
```

**Idempotent Response (200 OK):**
If the same `Idempotency-Key` is used again, returns the cached response:
```json
{
  "payment_id": "pay_abc123",
  "order_id": "order_123",
  "amount": 100.50,
  "status": "SUCCESS",
  "processed_at": "2024-01-15T10:30:00Z",
  "cached": true
}
```

### GET /payments/{payment_id}

Retrieve payment details by ID.

### GET /payments/order/{order_id}

Retrieve payment by order ID.

---

## ❓ Questions & Answers

### Q1: Why Do Retries Cause Double Payments?

**Answer:**

In distributed systems, network failures, timeouts, and service crashes are inevitable. When a payment request fails, multiple retry mechanisms can trigger simultaneously:

1. **Client-Side Retries**: The client application retries the request when it doesn't receive a response
2. **Load Balancer Retries**: Load balancers retry requests when upstream services timeout
3. **Service Retries**: The payment service retries when calling external payment gateways
4. **Network Partitions**: Temporary network issues can cause duplicate requests to reach the server

**Example Scenario Without Idempotency:**

```
Time T1: Client sends POST /pay {order_id: "123", amount: 100}
  → Payment gateway times out after 30 seconds
  → Client receives no response

Time T2: Client retries POST /pay {order_id: "123", amount: 100}
  → This is treated as a NEW payment request
  → Payment processed successfully

Time T3: Original request finally completes
  → Payment also processed successfully

Result: Customer charged ₹200 instead of ₹100 ❌
```

**Root Causes:**
- **Stateless Requests**: Without idempotency, each HTTP request is independent
- **No Request Deduplication**: Server cannot distinguish retries from new requests
- **Race Conditions**: Multiple requests can process simultaneously
- **Partial Failures**: Network timeouts can cause requests to complete after retries

**Real-World Impact:**
- Customer complaints and chargebacks
- Financial losses and reconciliation issues
- Loss of customer trust

---

### Q2: How Does Idempotency Solve the Problem?

**Answer:**

Idempotency ensures that **multiple identical requests produce the same result as a single request**. This is achieved through idempotency keys.

**How It Works:**

1. **Client Provides Idempotency Key**: Each payment request includes a unique `Idempotency-Key` header
2. **Server Caches Response**: First request processes payment and caches the response
3. **Subsequent Requests Return Cached Response**: Retries with the same key return the cached result instantly
4. **No Duplicate Processing**: Payment is processed only once, regardless of retry count

**Example Scenario With Idempotency:**

```
Time T1: Client sends POST /pay {order_id: "123"} [Idempotency-Key: "abc-123"]
  → Server checks cache: key "abc-123" not found
  → Payment processed, stored with key "abc-123"
  → Returns: {payment_id: "pay_001", status: "SUCCESS"}
  → Response cached in Redis for 24 hours

Time T2: Client retries POST /pay {order_id: "123"} [Idempotency-Key: "abc-123"]
  → Server checks cache: key "abc-123" found
  → Returns cached response: {payment_id: "pay_001", status: "SUCCESS", cached: true}
  → No payment processing occurs
  → No duplicate charge ✅
```

**Key Mechanisms:**

1. **Idempotency Key Uniqueness**: Each unique payment attempt uses a unique key
2. **Response Caching**: Successful responses cached in Redis (fast lookup)
3. **Distributed Locking**: Prevents race conditions when multiple requests arrive simultaneously
4. **Database Constraints**: Unique constraint on `order_id` provides additional protection

**Benefits:**
- ✅ Safe retries: Clients can retry without fear of duplicate charges
- ✅ Fast responses: Cached responses return in < 1ms
- ✅ Consistency: Same request always returns same result
- ✅ Reliability: Handles network failures gracefully

---

### Q3: Architecture Diagrams

**Answer:**

#### High-Level Architecture

```
┌─────────────┐
│   Client    │
│ Application │
└──────┬──────┘
       │
       │ POST /pay
       │ Idempotency-Key: "abc-123"
       │
       ▼
┌─────────────────────────────────────┐
│      FastAPI Application             │
│  ┌───────────────────────────────┐   │
│  │  Idempotency Middleware      │   │
│  │  ┌─────────────────────────┐ │   │
│  │  │ 1. Extract Key          │ │   │
│  │  │ 2. Check Redis Cache    │ │◄──┼──┐
│  │  │ 3. Acquire Lock         │ │   │  │
│  │  │ 4. Process/Cache         │ │   │  │
│  │  │ 5. Release Lock         │ │   │  │
│  │  └─────────────────────────┘ │   │  │
│  └──────────────┬────────────────┘   │  │
│                 │                      │  │
│  ┌──────────────▼──────────────────┐  │  │
│  │     Payment Service              │  │  │
│  │  ┌────────────────────────────┐ │  │  │
│  │  │ 1. Validate Request        │ │  │  │
│  │  │ 2. Check Order Uniqueness  │ │  │  │
│  │  │ 3. Create Payment (INIT)   │ │  │  │
│  │  │ 4. Call Gateway (PROC)     │ │  │  │
│  │  │ 5. Update Status (SUCCESS) │ │  │  │
│  │  └────────────────────────────┘ │  │  │
│  └──────────────────────────────────┘  │  │
└──────────────────────────────────────────┘  │
       │                                       │
       │                                       │
   ┌───┴────┐                          ┌──────┴────┐
   │        │                          │           │
   ▼        ▼                          ▼           ▼
┌─────────┐ ┌──────────┐          ┌──────────┐ ┌──────────┐
│PostgreSQL│ │  Redis  │          │  Redis   │ │  Redis   │
│         │ │          │          │          │ │          │
│Payments │ │Idempotency│         │  Locks   │ │  Cache   │
│Table    │ │  Keys    │         │          │ │          │
└─────────┘ └──────────┘          └──────────┘ └──────────┘
```

#### Request Flow Diagram

```
Client Request
    │
    ├─► [Idempotency Middleware]
    │       │
    │       ├─► Extract Idempotency-Key
    │       │
    │       ├─► Check Redis Cache
    │       │   │
    │       │   ├─► [Cache Hit] ──► Return Cached Response (fast path)
    │       │   │
    │       │   └─► [Cache Miss] ──► Continue
    │       │
    │       ├─► Acquire Distributed Lock
    │       │   │
    │       │   ├─► [Lock Acquired] ──► Process Payment
    │       │   │
    │       │   └─► [Lock Failed] ──► Wait & Retry Cache Lookup
    │       │
    │       ├─► [Payment Service]
    │       │       │
    │       │       ├─► Validate Request
    │       │       │
    │       │       ├─► Check PostgreSQL (order_id uniqueness)
    │       │       │
    │       │       ├─► Create Payment (INITIATED)
    │       │       │
    │       │       ├─► Update Status (PROCESSING)
    │       │       │
    │       │       ├─► Call Payment Gateway
    │       │       │   │
    │       │       │   ├─► [Success] ──► Update (SUCCESS)
    │       │       │   ├─► [Failure] ──► Update (FAILED)
    │       │       │   └─► [Timeout] ──► Return 504, Keep (PROCESSING)
    │       │       │
    │       │       └─► Return Payment Response
    │       │
    │       ├─► Cache Response in Redis
    │       │
    │       └─► Release Lock
    │
    └─► Return Response to Client
```

#### State Machine Diagram

```
Payment Lifecycle States:

    [INITIATED]
        │
        │ Payment record created in DB
        │
        ▼
    [PROCESSING]
        │
        │ Gateway call in progress
        │
        ├──────────────┬──────────────┐
        │              │              │
        ▼              ▼              ▼
   [SUCCESS]      [FAILED]      [TIMEOUT]
        │              │              │
        │              │              │
        └──────────────┴──────────────┘
                    │
                    │ All final states
                    │
                    ▼
              [COMPLETED]
```

#### Data Flow: Idempotency Key Lookup

```
Request with Idempotency-Key: "abc-123"
    │
    ▼
┌─────────────────────┐
│ Redis Cache Lookup  │
│ Key: idempotency:abc-123
└──────────┬──────────┘
           │
    ┌──────┴──────┐
    │             │
    ▼             ▼
[FOUND]      [NOT FOUND]
    │             │
    │             ├─► Acquire Lock
    │             │
    │             ├─► Process Payment
    │             │
    │             ├─► Cache Response
    │             │
    │             └─► Release Lock
    │
    └─► Return Cached Response
        (< 1ms response time)
```

---

### Q4: Failure Scenarios and Testing

**Answer:**

#### Scenario 1: Network Timeout with Retry

**Problem:** Payment gateway times out, client retries with same idempotency key.

**Test:**
```bash
# First request - simulates timeout
curl -X POST http://localhost:8000/pay \
  -H "Idempotency-Key: test-key-1" \
  -H "Content-Type: application/json" \
  -d '{"order_id": "order_1", "amount": 100, "currency": "INR"}'

# Retry with same key - should return cached response
curl -X POST http://localhost:8000/pay \
  -H "Idempotency-Key: test-key-1" \
  -H "Content-Type: application/json" \
  -d '{"order_id": "order_1", "amount": 100, "currency": "INR"}'
```

**Expected Behavior:**
- First request processes payment (or times out)
- Second request returns cached response
- No duplicate payment created
- Response includes `"cached": true` flag

**How It's Handled:**
- Idempotency middleware checks Redis cache before processing
- Cached responses returned instantly (< 1ms)
- Payment service never called for cached requests

---

#### Scenario 2: Concurrent Requests (Race Condition)

**Problem:** Multiple requests with same idempotency key arrive simultaneously.

**Test:**
```bash
# Send 5 concurrent requests with same idempotency key
for i in {1..5}; do
  curl -X POST http://localhost:8000/pay \
    -H "Idempotency-Key: concurrent-test" \
    -H "Content-Type: application/json" \
    -d '{"order_id": "order_concurrent", "amount": 50, "currency": "INR"}' &
done
wait
```

**Expected Behavior:**
- Only one payment is processed
- All 5 requests return the same payment_id
- 4 requests return cached responses
- No race conditions or duplicate payments

**How It's Handled:**
- Distributed lock (Redis SET with NX) ensures only one request processes
- Other requests wait and poll cache until first completes
- Lock automatically expires after 30 seconds (prevents deadlocks)

---

#### Scenario 3: Duplicate Order ID (Different Idempotency Keys)

**Problem:** Client accidentally sends same order with different idempotency keys.

**Test:**
```bash
# Request 1
curl -X POST http://localhost:8000/pay \
  -H "Idempotency-Key: key-1" \
  -H "Content-Type: application/json" \
  -d '{"order_id": "order_duplicate", "amount": 200, "currency": "INR"}'

# Request 2 - same order_id, different key
curl -X POST http://localhost:8000/pay \
  -H "Idempotency-Key: key-2" \
  -H "Content-Type: application/json" \
  -d '{"order_id": "order_duplicate", "amount": 200, "currency": "INR"}'
```

**Expected Behavior:**
- First request succeeds
- Second request fails with `409 Conflict`
- Error message: "Order order_duplicate already exists"

**How It's Handled:**
- Database unique constraint on `order_id` column
- SQLAlchemy raises `IntegrityError` on duplicate
- Service catches error and returns 409 Conflict
- This provides defense-in-depth (idempotency + database constraint)

---

#### Scenario 4: Missing Idempotency Key

**Problem:** Client forgets to include Idempotency-Key header.

**Test:**
```bash
curl -X POST http://localhost:8000/pay \
  -H "Content-Type: application/json" \
  -d '{"order_id": "order_no_key", "amount": 100, "currency": "INR"}'
```

**Expected Behavior:**
- Request rejected with `400 Bad Request`
- Error message: "Idempotency-Key header is required"
- No payment processing occurs

**How It's Handled:**
- Middleware validates header presence before processing
- Returns error immediately (fail-fast approach)

---

#### Scenario 5: Redis Failure

**Problem:** Redis is unavailable (cache miss scenario).

**Expected Behavior:**
- System degrades gracefully
- Idempotency checks fail (no cache)
- Requests still process (but without idempotency protection)
- Database constraints still prevent duplicate orders

**Mitigation:**
- Redis connection pooling and retries
- Circuit breaker pattern for Redis failures
- Fallback to database-only idempotency (slower but safe)
- Monitoring and alerting for Redis health

---

#### Scenario 6: Database Failure During Processing

**Problem:** Database fails after payment processing starts.

**Expected Behavior:**
- Transaction rollback on failure
- Payment remains in INITIATED or PROCESSING state
- Client receives error and can retry
- No partial state persisted

**How It's Handled:**
- Database transactions ensure atomicity
- Rollback on any error
- Payment state machine prevents inconsistent states

---

### Q5: Production Considerations

**Answer:**

#### 1. Idempotency Key Generation

**Best Practices:**
- **Client-Generated Keys**: Clients should generate UUIDs for each payment attempt
- **Key Format**: Use UUID v4 (random) to ensure uniqueness
- **Key Length**: Minimum 32 characters, maximum 255 characters
- **Key Storage**: Store keys client-side for retry scenarios

**Example:**
```python
import uuid
idempotency_key = str(uuid.uuid4())  # e.g., "550e8400-e29b-41d4-a716-446655440000"
```

**Anti-Patterns to Avoid:**
- ❌ Reusing keys for different payments
- ❌ Using predictable keys (sequential IDs)
- ❌ Using order_id as idempotency key (different concept)

---

#### 2. Cache TTL Management

**Current Implementation:**
- TTL: 24 hours (configurable via `IDEMPOTENCY_KEY_TTL`)
- Automatic expiration via Redis TTL

**Production Recommendations:**
- **Short TTL (1-24 hours)**: For payment processing
- **Long TTL (7-30 days)**: For refunds, reversals
- **Configurable per Endpoint**: Different TTLs for different operations
- **Monitoring**: Track cache hit rates and TTL effectiveness

**Considerations:**
- Longer TTL = more memory usage
- Shorter TTL = more database lookups
- Balance based on retry patterns and business requirements

---

#### 3. Distributed Locking

**Current Implementation:**
- Redis SET with NX (atomic check-and-set)
- Lock timeout: 30 seconds
- Automatic expiration prevents deadlocks

**Production Enhancements:**
- **Lock Refresh**: Extend lock timeout for long-running operations
- **Lock Monitoring**: Alert on lock contention
- **Lock Timeout Tuning**: Adjust based on actual processing time
- **Deadlock Prevention**: Always release locks in finally blocks

**Edge Cases:**
- Lock expiration during processing → Handle gracefully
- Multiple lock attempts → Exponential backoff
- Lock holder crashes → Automatic expiration after timeout

---

#### 4. Database Constraints

**Current Implementation:**
- Unique constraint on `order_id` column
- Unique constraint on `payment_id` column
- Indexes on frequently queried columns

**Production Considerations:**
- **Constraint Violations**: Monitor and alert on 409 conflicts
- **Index Maintenance**: Regular VACUUM and REINDEX
- **Partitioning**: Consider table partitioning for high volume
- **Read Replicas**: Use replicas for read-heavy workloads

---

#### 5. Error Handling and Monitoring

**Key Metrics to Monitor:**
- Idempotency cache hit rate (target: > 80%)
- Lock acquisition success rate
- Payment processing latency (p50, p95, p99)
- Error rates by type (timeout, failure, conflict)
- Database constraint violations

**Alerting:**
- High error rates (> 1% of requests)
- Redis unavailability
- Database connection pool exhaustion
- Unusual cache miss patterns

**Logging:**
- All payment state transitions
- Idempotency key usage (for debugging)
- Lock acquisition/release events
- Cache hit/miss events

---

#### 6. Scalability Considerations

**Horizontal Scaling:**
- ✅ Stateless application (can scale horizontally)
- ✅ Redis cluster for high availability
- ✅ PostgreSQL read replicas for read scaling
- ✅ Load balancer with health checks

**Performance Optimizations:**
- Connection pooling (database and Redis)
- Async request processing
- Response compression
- CDN for static assets (if any)

**Capacity Planning:**
- Redis memory: ~1KB per idempotency key
- Database: ~500 bytes per payment record
- Estimate based on: requests/day × TTL × average key size

---

#### 7. Security Considerations

**Idempotency Key Security:**
- Keys should be opaque (not reveal business logic)
- Don't include sensitive data in keys
- Rate limiting on key generation
- Monitor for key enumeration attacks

**API Security:**
- Authentication and authorization
- Rate limiting per client
- Input validation (Pydantic schemas)
- SQL injection prevention (SQLAlchemy ORM)

---

#### 8. Disaster Recovery

**Backup Strategy:**
- Database: Daily backups with point-in-time recovery
- Redis: RDB snapshots + AOF (Append-Only File)
- Configuration: Version-controlled in Git

**Recovery Procedures:**
- Redis failure: Degrade to database-only mode
- Database failure: Failover to replica
- Full system failure: Restore from backups

---

## 🎓 What This Project Demonstrates

### 1. Idempotency Patterns

**Understanding:**
- Idempotency is a fundamental concept in distributed systems
- Idempotent operations can be safely retried
- Idempotency keys enable request deduplication

**Implementation:**
- Middleware-based idempotency (separation of concerns)
- Redis caching for fast lookups
- Response caching with TTL management

**Real-World Application:**
- Payment processing (this project)
- Order creation
- Email sending
- File uploads
- API webhooks

---

### 2. Distributed Systems Challenges

**Challenges Addressed:**
- **Network Failures**: Retries and timeouts
- **Race Conditions**: Distributed locking
- **Partial Failures**: Transaction rollback
- **Consistency**: Database constraints
- **Availability**: Redis caching for performance

**Solutions Demonstrated:**
- Idempotency keys for safe retries
- Distributed locks for concurrency control
- Database transactions for atomicity
- Caching for performance and availability

---

### 3. Race Condition Handling

**Problem:**
Multiple requests with same idempotency key arrive simultaneously.

**Solution:**
- Distributed lock (Redis SET with NX)
- Only one request acquires lock and processes
- Other requests wait and poll cache
- Lock automatically expires (prevents deadlocks)

**Code Example:**
```python
# Acquire lock atomically
lock_acquired = redis_client.set(lock_key, "1", nx=True, ex=30)

if not lock_acquired:
    # Another request is processing, wait for it
    await asyncio.sleep(0.5)
    cached_response = idempotency_store.get(idempotency_key)
    if cached_response:
        return cached_response
```

---

### 4. Database Constraints

**Purpose:**
- Prevent duplicate orders at database level
- Defense-in-depth (idempotency + constraints)
- Data integrity guarantee

**Implementation:**
```python
# Model definition
order_id = Column(String(100), unique=True, nullable=False)

# Error handling
except IntegrityError as e:
    if "order_id" in str(e):
        raise HTTPException(status_code=409, detail="Order already exists")
```

**Benefits:**
- Database-level enforcement (cannot be bypassed)
- Works even if application logic has bugs
- Provides audit trail of constraint violations

---

### 5. Caching Strategies

**Strategy: Write-Through Cache**
- Write to database first
- Then cache successful response
- Cache serves as fast read path

**Cache Key Design:**
- Format: `idempotency:{client_key}`
- Namespace prevents collisions
- TTL for automatic cleanup

**Cache Invalidation:**
- TTL-based expiration (no manual invalidation needed)
- Automatic cleanup after 24 hours
- Memory-efficient (bounded growth)

**Performance:**
- Cache hit: < 1ms (Redis in-memory)
- Cache miss: ~50-200ms (database + processing)
- 80%+ cache hit rate expected in production

---

## 🛠️ Tech Stack

- **FastAPI**: Modern Python web framework with async support
- **PostgreSQL**: Relational database for payment persistence
- **Redis**: In-memory cache for idempotency keys
- **SQLAlchemy**: ORM for database operations
- **Alembic**: Database migrations
- **Pydantic**: Data validation and serialization

## 📊 Database Schema

```sql
CREATE TABLE payments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    payment_id VARCHAR(50) UNIQUE NOT NULL,
    order_id VARCHAR(100) UNIQUE NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'INR',
    customer_id VARCHAR(100),
    status VARCHAR(20) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    processed_at TIMESTAMP,
    payment_metadata JSONB
);

CREATE INDEX ix_payments_payment_id ON payments(payment_id);
CREATE INDEX ix_payments_order_id ON payments(order_id);
CREATE INDEX ix_payments_status ON payments(status);
```

## 🧪 Testing

Run the test scenarios:

```bash
# Bash script
./test_scenarios.sh

# Python script
python example_usage.py
```

## 📝 Notes

- Idempotency keys are cached for 24 hours (configurable)
- Order IDs have unique constraint to prevent duplicate orders
- Payment gateway simulation includes 10% timeout rate and 5% failure rate
- All timestamps are in UTC
- Distributed locks expire after 30 seconds

## 🔗 Related Concepts

- **Idempotency**: Operations that produce the same result regardless of execution count
- **Distributed Locks**: Preventing concurrent processing of the same request
- **Eventual Consistency**: Trade-offs between consistency and availability
- **Circuit Breakers**: Preventing cascading failures in distributed systems
- **Saga Pattern**: Managing distributed transactions

---

**Built as part of the [Scaling Systems Blueprints](../README.md) learning series.**