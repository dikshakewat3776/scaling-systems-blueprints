"""
## What is idempotency?

Idempotency means:

- If the same request is sent multiple times,
- the server should act as if it was processed once.

In payments, this prevents duplicate charges when clients retry after a timeout.

## Files in this demo

- `idempotency_store.py`: tiny in-memory cache (`key -> response`)
- `payment_processor.py`: charge logic that checks cache first
- `run_demo.py`: script that runs first request, retry, then new request

## How the flow works

1. Client sends payment with an `idempotency_key`.
2. System checks if this key already exists in the store.
3. If found: return cached response (`cached: true`), do not charge again.
4. If not found: process charge, save response, return it.

## Run the demo
```bash
python run_demo.py
```

## Expected output behavior

- First call with `order-101-attempt-1`: new payment created, total charged = 500
- Retry with same key: cached response returned, total charged still = 500
- New key `order-102-attempt-1`: new payment created, total charged = 1000

## Why this matters in real systems

Real systems use Redis + database + distributed locks, but the core idea is the same:

- **Same key** = **same result**, no duplicate side effects.

"""


from idempotency_store import IdempotencyStore
from payment_processor import PaymentProcessor


def main() -> None:
    print("Running idempotency demo...")
    store = IdempotencyStore()
    print("Created idempotency store")
    processor = PaymentProcessor(store)
    print("Created payment processor")
    key = "order-101-attempt-1"
    print(f"Key: {key}")
    print("1) First request (new key):")
    print(processor.charge(amount=500, idempotency_key=key))
    print(f"Total charged so far: {processor.total_charges}")
    print()

    print("2) Retry request (same key):")
    print(processor.charge(amount=500, idempotency_key=key))
    print(f"Total charged so far: {processor.total_charges}")
    print()

    print("3) New payment (different key):")
    print(processor.charge(amount=500, idempotency_key="order-102-attempt-1"))
    print(f"Total charged so far: {processor.total_charges}")


if __name__ == "__main__":
    main()
