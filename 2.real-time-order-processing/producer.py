"""
Producer Service
----------------

This script simulates users placing orders and sends them to a Kafka topic
called "orders".

It demonstrates:
- How to connect to Kafka using kafka-python
- How to serialize messages as JSON
- How to handle basic errors and retries
"""

import json
import random
import time
import uuid
from typing import Dict

from kafka import KafkaProducer
from kafka.errors import KafkaError

from config import (
    KAFKA_BOOTSTRAP_SERVERS,
    ORDERS_TOPIC,
    current_utc_timestamp,
    setup_logging,
)


logger = setup_logging("producer")


def create_order() -> Dict:
    """
    Create a fake order with:
    - order_id: unique UUID
    - user_id: fake user identifier
    - amount: random amount between 10 and 500
    - timestamp: current UTC time
    """
    order = {
        "order_id": str(uuid.uuid4()),
        "user_id": f"user-{random.randint(1, 100)}",
        "amount": round(random.uniform(10.0, 500.0), 2),
        "timestamp": current_utc_timestamp(),
    }
    return order


def create_kafka_producer() -> KafkaProducer:
    """
    Create and return a KafkaProducer instance.

    - bootstrap_servers: where Kafka is running
    - value_serializer: how to convert Python dict -> bytes before sending
    - retries: number of automatic retries for transient errors
    """
    logger.info(f"Connecting to Kafka at {KAFKA_BOOTSTRAP_SERVERS}...")

    producer = KafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        # Convert Python dict to JSON string, then to bytes
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        # Basic retry configuration
        retries=5,
    )

    logger.info("Kafka producer created.")
    return producer


def send_order(producer: KafkaProducer, order: Dict) -> None:
    """
    Send a single order to the Kafka 'orders' topic.

    We use the order_id as the message key to ensure that all messages
    for the same order go to the same partition (ordering guarantee per key).
    """
    key_bytes = order["order_id"].encode("utf-8")

    try:
        future = producer.send(topic=ORDERS_TOPIC, key=key_bytes, value=order)

        # Block until the message is actually sent or an error occurs
        record_metadata = future.get(timeout=10)

        logger.info(
            f"Sent order_id={order['order_id']} "
            f"to topic={record_metadata.topic}, "
            f"partition={record_metadata.partition}, "
            f"offset={record_metadata.offset}"
        )
    except KafkaError as e:
        # In a real-world system, you might log this and push the message to a DLQ
        logger.error(f"Failed to send order {order['order_id']}: {e}")


def main(num_orders: int = 10, delay_seconds: float = 0.5) -> None:
    """
    Main loop:
    - Create a Kafka producer
    - Generate `num_orders` fake orders
    - Send each order to Kafka with a small delay
    """
    producer = create_kafka_producer()

    try:
        for i in range(num_orders):
            order = create_order()
            logger.info(f"Creating order {i + 1}/{num_orders}: {order}")
            send_order(producer, order)

            # Sleep a bit to simulate time between user orders
            time.sleep(delay_seconds)

    finally:
        # Ensure all buffered messages are sent before exiting
        logger.info("Flushing producer and closing connection...")
        producer.flush()
        producer.close()


if __name__ == "__main__":
    # You can change these values to simulate more orders or faster traffic.
    main(num_orders=20, delay_seconds=0.2)

