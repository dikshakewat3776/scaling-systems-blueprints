"""
Consumer Service
----------------

This script consumes orders from the Kafka "orders" topic and processes them.

It demonstrates:
- How to connect to Kafka using kafka-python
- How to deserialize JSON messages
- Basic validation and error handling
- How consumer groups enable scaling
"""

import json
from typing import Dict

from kafka import KafkaConsumer

from config import (
    CONSUMER_GROUP_ID,
    KAFKA_BOOTSTRAP_SERVERS,
    ORDERS_TOPIC,
    setup_logging,
)


logger = setup_logging("consumer")


def create_kafka_consumer() -> KafkaConsumer:
    """
    Create and return a KafkaConsumer instance.

    Key points:
    - `group_id`: identifies the consumer group this instance belongs to.
      If you run multiple consumers with the same group_id, Kafka will share
      the work (partitions) across them.
    - `auto_offset_reset`:
        * 'earliest' -> start from the beginning if no committed offset.
        * 'latest'   -> start from new messages only.
    - `enable_auto_commit`:
        * True => Kafka will periodically commit offsets automatically.
        * In more advanced setups, you might disable this and commit manually.
    """
    logger.info(
        f"Connecting to Kafka at {KAFKA_BOOTSTRAP_SERVERS} "
        f"as group_id={CONSUMER_GROUP_ID}..."
    )

    consumer = KafkaConsumer(
        ORDERS_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        group_id=CONSUMER_GROUP_ID,
        # Deserialize bytes -> JSON -> dict
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        auto_offset_reset="earliest",
        enable_auto_commit=True,
    )

    logger.info("Kafka consumer created and subscribed to topic '%s'.", ORDERS_TOPIC)
    return consumer


def is_valid_order(order: Dict) -> bool:
    """
    Very basic validation for the order payload.
    In real systems, you might use a schema library like Pydantic or Marshmallow.
    """
    required_fields = ("order_id", "user_id", "amount", "timestamp")
    for field in required_fields:
        if field not in order:
            logger.error("Invalid order - missing field '%s': %s", field, order)
            return False

    # Additional simple checks
    if not isinstance(order["amount"], (int, float)) or order["amount"] <= 0:
        logger.error("Invalid order amount: %s", order)
        return False

    return True


def process_order(order: Dict) -> None:
    """
    Process a single order.

    For this beginner example, we simply log the order.
    In a real system, this is where you would:
    - Insert into a database
    - Call downstream services
    - Update caches, etc.
    """
    logger.info(
        "Processing order_id=%s user_id=%s amount=%.2f timestamp=%s",
        order["order_id"],
        order["user_id"],
        order["amount"],
        order["timestamp"],
    )


def main() -> None:
    """
    Main loop:
    - Create a Kafka consumer
    - Continuously poll for new messages
    - Validate and process each order

    Use Ctrl+C to stop the consumer gracefully.
    """
    consumer = create_kafka_consumer()

    try:
        logger.info("Starting to consume messages...")

        for message in consumer:
            # message.value is already a dict because of our value_deserializer
            order = message.value

            logger.info(
                "Received message from topic=%s partition=%s offset=%s",
                message.topic,
                message.partition,
                message.offset,
            )

            try:
                if not is_valid_order(order):
                    # In a real system, you might send this to a separate 'invalid-orders' topic
                    continue

                process_order(order)

            except Exception as e:
                # Catch any unexpected error so that this consumer does not crash.
                # In a production system, you would:
                # - log the full stack trace
                # - possibly retry
                # - potentially send the message to a dead-letter topic
                logger.error("Error while processing order %s: %s", order, e)

    except KeyboardInterrupt:
        logger.info("Stopping consumer (KeyboardInterrupt)...")
    finally:
        logger.info("Closing consumer connection...")
        consumer.close()


if __name__ == "__main__":
    main()

