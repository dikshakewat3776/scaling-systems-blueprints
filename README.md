# Scaling Systems Blueprints

A collection of system design projects demonstrating key concepts for building scalable, production-ready distributed systems.

## 🎯 Purpose

This repository contains hands-on implementations of critical system design patterns and concepts. Each project is a complete, runnable system that demonstrates real-world solutions to common distributed systems challenges.

## 📚 Projects

### 1. [Idempay - Payment Service with Idempotency](./payment-service-idempotency)

**Problem Solved:** Preventing duplicate payments in distributed systems when retries occur.

**Key Concepts:**
- Idempotency patterns
- Distributed locking
- Race condition handling
- Database constraints
- Caching strategies

**Tech Stack:** FastAPI, PostgreSQL, Redis

**Status:** ✅ Complete

[View Project →](./payment-service-idempotency)

---

### 2. [Realtime Chat Queue - WhatsApp-like Messaging](./realtime-chat-queue)

**Problem Solved:** Building a scalable messaging system with ordering guarantees and reliable delivery.

**Key Concepts:**
- Async processing
- At-least-once delivery
- Ordering guarantees (per chat)
- Consumer groups
- Backpressure handling
- WebSocket real-time delivery

**Tech Stack:** FastAPI, PostgreSQL, Redis Streams, WebSocket

**Status:** ✅ Complete

[View Project →](./realtime-chat-queue)

---

## 🚀 Getting Started

Each project is self-contained with its own README, Docker setup, and documentation. Navigate to a project directory to get started:

```bash
cd payment-service-idempotency
```

See each project's README for detailed setup and run instructions.

## 📖 Learning Path

These projects are designed to be studied in order, building complexity:

1. **Idempotency** - Foundation for safe retries in distributed systems
2. **Queue-Based Systems** - Async processing with ordering guarantees
3. *More projects coming soon...*

## Preparation

Each project includes:
- Detailed explanations of the problem and solution
- Architecture diagrams
- Failure scenario testing
- Production considerations
- Talking points

## 📝 Contributing

Each project is designed to be:
- Self-contained and runnable
- Well-documented with explanations
- Production-ready patterns (not just demos)
- Interview-ready with clear talking points
