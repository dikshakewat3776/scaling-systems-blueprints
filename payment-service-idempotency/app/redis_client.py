"""
Redis Client for Idempotency Storage

This module provides a Redis-based storage layer for idempotency keys.
Redis is used for:
1. Fast response caching (O(1) lookup, < 1ms latency)
2. Distributed locking (prevents race conditions)
3. TTL-based expiration (automatic cleanup)

Why Redis?
- Sub-millisecond lookups for idempotency checks
- Built-in TTL support for automatic cache expiration
- Atomic operations for distributed locking
- High availability and scalability
"""

import redis
import json
from typing import Optional, Dict, Any
from app.config import settings

# Initialize Redis client with JSON decoding enabled
# decode_responses=True automatically decodes bytes to strings
redis_client = redis.from_url(settings.redis_url, decode_responses=True)


class IdempotencyStore:
    """
    Redis-based storage for idempotency keys and responses.
    
    This class provides:
    - Response caching: Store successful payment responses
    - Distributed locking: Prevent concurrent processing
    - TTL management: Automatic cache expiration
    
    Key Naming Convention:
    - idempotency:{key} → Cached response
    - lock:idempotency:{key} → Distributed lock
    """
    
    def __init__(self, client: redis.Redis, ttl: int = 86400):
        """
        Initialize idempotency store.
        
        Args:
            client: Redis client instance
            ttl: Time-to-live in seconds (default: 24 hours)
        """
        self.client = client
        self.ttl = ttl  # Cache entries expire after TTL seconds

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached response for an idempotency key.
        
        This is the fast path for idempotency checks.
        If a response exists in cache, it means we've processed
        this request before and can return the cached result.
        
        Args:
            key: Idempotency key from request header
            
        Returns:
            Optional[Dict]: Cached response data or None if not found
        """
        # Redis key format: idempotency:{client_provided_key}
        cached = self.client.get(f"idempotency:{key}")
        if cached:
            # Deserialize JSON response
            return json.loads(cached)
        return None

    def set(self, key: str, value: Dict[str, Any]) -> None:
        """
        Store response for an idempotency key with TTL.
        
        This caches successful payment responses so that
        retries with the same key return instantly.
        
        Args:
            key: Idempotency key from request header
            value: Response data to cache (status_code + response body)
        """
        # Use SETEX to set key with expiration
        # This ensures cache entries are automatically cleaned up
        self.client.setex(
            f"idempotency:{key}",
            self.ttl,  # Expire after TTL seconds
            json.dumps(value)  # Serialize response as JSON
        )

    def acquire_lock(self, key: str, timeout: int = 10) -> bool:
        """
        Acquire a distributed lock for processing.
        
        This prevents race conditions when multiple requests
        with the same idempotency key arrive simultaneously.
        Only one request can acquire the lock and process.
        
        Uses Redis SET with NX (only if not exists) and EX (expiration).
        This is an atomic operation, ensuring thread-safety.
        
        Args:
            key: Idempotency key to lock
            timeout: Lock expiration time in seconds (default: 10s)
            
        Returns:
            bool: True if lock acquired, False if already locked
        """
        # Redis key format: lock:idempotency:{client_provided_key}
        # NX = Only set if key doesn't exist (atomic check-and-set)
        # EX = Set expiration time
        lock_key = f"lock:idempotency:{key}"
        return self.client.set(lock_key, "1", nx=True, ex=timeout)

    def release_lock(self, key: str) -> None:
        """
        Release a distributed lock.
        
        This should always be called in a finally block
        to ensure locks are released even if processing fails.
        
        Args:
            key: Idempotency key to unlock
        """
        lock_key = f"lock:idempotency:{key}"
        self.client.delete(lock_key)


# Global instance for use throughout the application
idempotency_store = IdempotencyStore(redis_client, ttl=settings.idempotency_key_ttl)
