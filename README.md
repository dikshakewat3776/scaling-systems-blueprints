# Scaling Systems Blueprints

A collection of system design projects demonstrating key concepts for building scalable, production-ready distributed systems.

## 🎯 Purpose

This repository contains hands-on implementations of critical system design patterns and concepts. Each project is a complete, runnable system that demonstrates real-world solutions to common distributed systems challenges.

## 📚 Projects

### 1. [Payment Idempotency Simple](./1.payment-idempotency-simple)

**Problem Solved:** Preventing duplicate charges when clients retry the same payment request.

**Key Concepts:**
- Idempotency patterns
- Request deduplication with idempotency keys
- Stable retry responses
- Side-effect safety in distributed systems

**Tech Stack:** Python (in-memory demo)

**Status:** ✅ Complete

[View Project →](./1.payment-idempotency-simple)

---

### 2. [Real-Time Order Processing](./2.real-time-order-processing)

**Problem Solved:** Building an event-driven order pipeline with scalable ingestion and reliable asynchronous processing.

**Key Concepts:**
- Event-driven architecture
- Kafka topics and partitions
- Consumer groups and rebalancing
- Throughput and reliability trade-offs
- Retry handling patterns

**Tech Stack:** Python, Apache Kafka, Docker

**Status:** ✅ Complete

[View Project →](./2.real-time-order-processing)

---

## 📖 Learning Path

These projects are designed to be studied in order, building complexity:

1. **Idempotency** - Foundation for safe retries and duplicate prevention
2. **Kafka Pipelines** - Event-driven processing with scalable consumers
3. *More projects coming soon...*

## 📝 Contributing

Each project is designed to be:
- Self-contained and runnable
- Well-documented with explanations
- Production-ready patterns