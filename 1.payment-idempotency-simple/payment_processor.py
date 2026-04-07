import uuid
from idempotency_store import IdempotencyStore


class PaymentProcessor:
    """Processes payments and avoids duplicates using idempotency keys."""

    def __init__(self, store: IdempotencyStore) -> None:
        print("Initializing payment processor...")
        self.store = store
        self.total_charges = 0

    def charge(self, amount: int, idempotency_key: str) -> dict:
        """Charge once for each unique key and return stable response on retries."""
        print(f"Charging {amount} for idempotency key: {idempotency_key}")
        cached = self.store.get(idempotency_key)
        print(f"Cached response: {cached}")
        if cached:
            return {**cached, "cached": True}

        payment_id = f"pay_{uuid.uuid4().hex[:8]}"
        print(f"Payment ID: {payment_id}")
        response = {
            "payment_id": payment_id,
            "amount": amount,
            "status": "SUCCESS",
        }
        print(f"Response: {response}")
        print(f"Total charges: {self.total_charges}")
        self.total_charges += amount
        print(f"Setting response for key: {idempotency_key}")
        self.store.set(idempotency_key, response)
        print(f"Response set for key: {idempotency_key}")
        return response
