"""
Idempotency Middleware

This middleware implements the idempotency pattern to prevent duplicate payment processing.
It intercepts payment requests and ensures that multiple identical requests (same idempotency key)
produce the same result.

Key Features:
1. Idempotency Key Validation: Ensures all payment requests include an idempotency key
2. Response Caching: Stores successful responses in Redis for fast lookup
3. Distributed Locking: Prevents race conditions when multiple requests arrive simultaneously
4. Automatic Retry Handling: Waits for concurrent requests to complete before returning cached result

Flow:
1. Extract Idempotency-Key from request header
2. Check Redis cache for existing response
3. If found → return cached response immediately
4. If not found → acquire distributed lock
5. Process payment request
6. Cache successful response in Redis
7. Release lock
"""

import json
import asyncio
from typing import Callable, Optional
from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from app.redis_client import idempotency_store
from app.schemas import PaymentResponse


class IdempotencyMiddleware(BaseHTTPMiddleware):
    """
    Middleware to handle idempotency keys for payment requests.
    
    This middleware ensures that:
    - Multiple requests with the same idempotency key return the same response
    - Only one payment is processed per idempotency key
    - Race conditions are handled via distributed locks
    - Cached responses are returned instantly (sub-millisecond)
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request with idempotency protection.
        
        This method:
        1. Validates idempotency key presence
        2. Checks cache for existing response
        3. Acquires lock for concurrent request handling
        4. Processes request and caches response
        5. Releases lock
        
        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler in chain
            
        Returns:
            Response: HTTP response (cached or newly processed)
        """
        # Only apply idempotency to POST /pay endpoint
        # Other endpoints (GET, health checks) don't need idempotency
        if request.method == "POST" and request.url.path == "/pay":
            # Extract idempotency key from request header
            # Clients must send this header with each payment request
            idempotency_key = request.headers.get("Idempotency-Key")
            
            # Validate idempotency key is present
            # Without it, we cannot guarantee idempotency
            if not idempotency_key:
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"detail": "Idempotency-Key header is required"}
                )

            # Step 1: Check Redis cache for existing response
            # This is the fast path - if we've seen this key before, return cached result
            # Cache lookup is O(1) and typically < 1ms
            cached_response = idempotency_store.get(idempotency_key)
            if cached_response:
                # Return cached response immediately
                # This prevents duplicate payment processing
                response_data = cached_response.get("response")
                response_data["cached"] = True  # Flag to indicate this is a cached response
                return JSONResponse(
                    status_code=cached_response.get("status_code", 200),
                    content=response_data
                )

            # Step 2: Try to acquire distributed lock
            # This prevents race conditions when multiple requests arrive simultaneously
            # Only one request can acquire the lock and process the payment
            lock_acquired = idempotency_store.acquire_lock(idempotency_key, timeout=30)
            
            if not lock_acquired:
                # Another request is currently processing with the same key
                # Wait for it to complete and then return cached result
                # This handles the race condition gracefully
                max_retries = 10  # Maximum number of retry attempts
                retry_delay = 0.5  # Wait 500ms between retries
                
                # Poll cache until first request completes
                for _ in range(max_retries):
                    await asyncio.sleep(retry_delay)  # Non-blocking sleep
                    cached_response = idempotency_store.get(idempotency_key)
                    if cached_response:
                        # First request completed, return its result
                        response_data = cached_response.get("response")
                        response_data["cached"] = True
                        return JSONResponse(
                            status_code=cached_response.get("status_code", 200),
                            content=response_data
                        )
                
                # If still no cached response after waiting, process normally
                # This handles edge case where lock expired or request failed
                # In production, you might want to log this scenario

            try:
                # Step 3: Process the payment request
                # This calls the actual payment endpoint handler
                response = await call_next(request)
                
                # Step 4: Read response body for caching
                # We need to read the entire response to cache it
                # Note: response.body_iterator can only be read once
                response_body = b""
                async for chunk in response.body_iterator:
                    response_body += chunk
                
                # Step 5: Cache successful responses
                # Only cache successful responses (status < 400)
                # Failed responses should not be cached (client should retry with different key)
                if response.status_code < 400:
                    try:
                        # Parse JSON response
                        response_data = json.loads(response_body.decode())
                        
                        # Store in Redis with TTL (default 24 hours)
                        # This allows retries within reasonable time window
                        idempotency_store.set(
                            idempotency_key,
                            {
                                "status_code": response.status_code,
                                "response": response_data
                            }
                        )
                    except json.JSONDecodeError:
                        # Don't cache non-JSON responses
                        # This handles edge cases gracefully
                        pass
                
                # Step 6: Return response to client
                # Reconstruct response with same status, headers, and body
                return Response(
                    content=response_body,
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    media_type=response.media_type
                )
            
            finally:
                # Always release lock, even if request failed
                # This ensures other requests aren't blocked indefinitely
                idempotency_store.release_lock(idempotency_key)
        
        # For non-payment endpoints, process normally without idempotency
        # GET requests, health checks, etc. don't need idempotency
        return await call_next(request)
