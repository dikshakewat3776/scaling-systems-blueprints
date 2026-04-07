class IdempotencyStore:
    """Stores one response per idempotency key."""

    def __init__(self) -> None:
        print("Initializing idempotency store...")
        self._responses = {}

    def get(self, key: str):
        print(f"Getting response for key: {key}")
        """Return cached response if key already exists."""
        return self._responses.get(key)

    def set(self, key: str, response: dict) -> None:
        print(f"Caching response for key: {key}")
        """Cache the first successful response for this key."""
        self._responses[key] = response
