import logging
import os
from datetime import datetime

from dotenv import load_dotenv


# Load variables from a local .env file if present.
# This makes it easy to override config without changing code.
load_dotenv()


# ====================================================================================
# Kafka Configuration
# ====================================================================================

# Kafka broker address.
# In Docker, the broker is accessible as "kafka:9092" from containers.
# From your host machine (where you run Python), use "localhost:9092".
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")

# Name of the topic where orders will be published and consumed.
ORDERS_TOPIC = os.getenv("ORDERS_TOPIC", "orders")

# Consumer group ID (used for scaling with multiple consumers).
CONSUMER_GROUP_ID = os.getenv("CONSUMER_GROUP_ID", "order-processor-group")


# ====================================================================================
# Logging Configuration
# ====================================================================================

def setup_logging(service_name: str) -> logging.Logger:
    """
    Configure and return a logger with a helpful format.
    The service_name lets you distinguish producer vs consumer logs.
    """
    logger = logging.getLogger(service_name)

    # Avoid adding multiple handlers if setup_logging is called more than once.
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        fmt=f"%(asctime)s | {service_name} | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # Optional: also log to a file if desired
    log_file = os.getenv("LOG_FILE")
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def current_utc_timestamp() -> str:
    """
    Return the current UTC time as an ISO 8601 string.
    Example: '2025-01-26T10:00:00Z'
    """
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

