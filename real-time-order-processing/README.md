## Real-Time Order Processing System (Kafka, Python)

This project is a **beginner-friendly system design and implementation** of a real-time order processing system using **Apache Kafka** and **Python**.  
It is designed to help you prepare for **system design interviews** and understand how Kafka fits into a distributed architecture.

---

### 1. High-Level Architecture

At a high level, the system looks like this:

```text
+-----------+        +----------------------+        +----------------------+
|  Producer |  --->  |   Kafka Topic:       |  --->  |      Consumer        |
|  Service  |        |      "orders"        |        |   (Order Processor)   |
+-----------+        +----------------------+        +----------------------+
        (Python)                 (Kafka)                    (Python)
```

- **Producer Service**: Simulates users placing orders and sends messages to Kafka.
- **Kafka**: Acts as a **durable, scalable, distributed log** that stores order events.
- **Consumer Service**: Reads messages from the `orders` topic, validates them, and (in a real system) would store them in a database.

#### Why Kafka in the Middle?

Without Kafka:
- The producer would call the consumer (or database) directly.
- If the consumer is down, orders are lost or the producer fails.
- Scaling consumers is harder (tight coupling).

With Kafka:
- The producer only needs to know **Kafka**, not who will consume the data.
- Kafka **durably stores** messages until they are processed.
- You can add **multiple consumers** later (e.g., billing, analytics) without changing the producer.

---

### 2. Kafka Concepts Used Here (Beginner-Friendly)

- **Topic (`orders`)**: A named stream of messages. Think of it as a "category" of events.
- **Partition**: Each topic is split into partitions for scalability.
  - More partitions ⇒ more parallelism (more consumers can work in parallel).
  - Ordering is **guaranteed only within a partition**, not across the whole topic.
- **Producer**: A client that writes messages to a topic.
- **Consumer**: A client that reads messages from a topic.
- **Consumer Group**: A group of consumers sharing work.
  - Kafka ensures that **each partition is consumed by only one consumer** in a group.

#### Scalability Discussion

- To scale **throughput**, you:
  - Increase the **number of partitions** for the `orders` topic.
  - Run **multiple consumer instances** in the same consumer group.
- Kafka will **rebalance** partitions among consumers:
  - Example: 4 partitions, 2 consumers ⇒ each consumer will process 2 partitions.
  - If you add a 3rd consumer, Kafka will redistribute partitions dynamically.

---

### 3. Error Handling & Reliability (High-Level)

- **Producer Side**
  - Use **retries** when sending to Kafka (in case of transient network failures).
  - Use **acks** configuration (e.g., `acks='all'`) for stronger durability.
- **Consumer Side**
  - Process messages safely and **handle exceptions**.
  - Avoid losing messages by committing offsets **after** successful processing.
  - Optionally, move failed messages to a **dead-letter queue** (DLQ topic).

In this beginner project, we:
- Log errors clearly.
- Retry processing in a simple loop when possible.

---

### 4. Folder Structure

We will create the following structure:

```text
real-time-order-processing/
├─ docker-compose.yml        # Kafka + Zookeeper (local)
├─ requirements.txt          # Python dependencies
├─ config.py                 # Shared configuration (Kafka host, topic, etc.)
├─ producer.py               # Order producer service
├─ consumer.py               # Order consumer service
└─ README.md                 # (this file) explanation & usage
```

---

### 5. Running Kafka Locally (Docker)

We will use **Docker Compose** to run:
- **Zookeeper** (required by some Kafka distributions)
- **Kafka broker**

See `docker-compose.yml` in this folder for the full config.

Basic steps:

```bash
cd real-time-order-processing

# Start Kafka and Zookeeper
docker compose up -d

# (Optional) Check running containers
docker ps
```

Kafka will be accessible on `localhost:9092`.

---

### 6. Python Setup

Install dependencies (preferably in a virtualenv):

```bash
cd real-time-order-processing
pip install -r requirements.txt
```

---

### 7. Running the Producer and Consumer

1. **Start the consumer first** (so it is ready to process incoming orders):

```bash
python consumer.py
```

2. In another terminal, **run the producer** to simulate multiple orders:

```bash
python producer.py
```

You should see:
- Producer logs showing orders being sent.
- Consumer logs showing orders being received and processed.

---

### 8. Order Schema

Each order has the following fields:

```json
{
  "order_id": "uuid-string",
  "user_id": "user-123",
  "amount": 49.99,
  "timestamp": "2025-01-26T10:00:00Z"
}
```

We will send JSON-encoded orders from the producer to Kafka.  
The consumer will parse the JSON and "process" it (here, by validating & logging).

---

### 9. Step-by-Step Coding Guide

We will build:

1. `config.py` – shared settings (Kafka host, topic name, logging config).
2. `producer.py` – simulates user orders and sends them to Kafka.
3. `consumer.py` – reads from Kafka and processes orders.

Each file will contain **detailed comments** to guide you.

---

### 10. How to Test the System

1. Start Kafka via Docker.
2. Run the consumer to start listening for orders.
3. Run the producer to send a batch of simulated orders.
4. Observe logs:
   - Check that every produced order is consumed.
   - Try stopping the consumer and restarting it to see that Kafka delivers remaining messages.

---

### 11. Possible Improvements (For Interviews)

- **Persistence Layer**: Store processed orders into PostgreSQL or MongoDB.
- **Validation**: Add stricter schema validation (e.g., Pydantic) before processing.
- **Retries & DLQ**: If an order fails processing N times, send it to a `orders_dlq` topic.
- **Monitoring**:
  - Expose metrics (e.g., Prometheus) for:
    - Number of orders produced/consumed.
    - Consumer lag.
  - Add structured logging and correlation IDs.
- **Security**:
  - Use SSL and authentication for Kafka in production.
- **Scaling**:
  - Increase partitions and add more consumer instances in the same consumer group.

These are good **follow-up talking points** in system design interviews.

---

### 12. Follow-Up Interview Questions You Can Practice

- **Kafka Basics**
  - Why use Kafka instead of a traditional message queue?
  - What happens if a consumer crashes while processing a message?
  - How does Kafka ensure ordering?
- **Scalability**
  - How would you handle 10x more orders per second?
  - How many partitions would you choose and why?
  - How does a consumer group help with scaling?
- **Reliability**
  - How do you avoid losing messages?
  - When would you use a dead-letter queue?
  - How do you handle poison messages (messages that always fail)?
- **Extensions**
  - How would you add an "analytics" service to compute revenue in real time?
  - How would you build an "email notification" service using the same `orders` topic?

You can now move on to the actual code files: `config.py`, `producer.py`, and `consumer.py`.

