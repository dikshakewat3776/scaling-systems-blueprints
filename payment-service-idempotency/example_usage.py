#!/usr/bin/env python3
"""
Example usage of Idempay Payment Service API
Demonstrates idempotency in action
"""

import requests
import uuid
import time
from concurrent.futures import ThreadPoolExecutor

BASE_URL = "http://localhost:8000"


def make_payment(idempotency_key: str, order_id: str, amount: float):
    """Make a payment request"""
    response = requests.post(
        f"{BASE_URL}/pay",
        headers={
            "Idempotency-Key": idempotency_key,
            "Content-Type": "application/json"
        },
        json={
            "order_id": order_id,
            "amount": amount,
            "currency": "INR",
            "customer_id": "cust_example"
        }
    )
    return response.json(), response.status_code


def example_1_retry_same_key():
    """Example 1: Retry with same idempotency key"""
    print("\n" + "="*60)
    print("Example 1: Retry with Same Idempotency Key")
    print("="*60)
    
    key = str(uuid.uuid4())
    order_id = f"order_{uuid.uuid4().hex[:8]}"
    
    print(f"\nFirst request with key: {key}")
    result1, status1 = make_payment(key, order_id, 100.0)
    print(f"Status: {status1}")
    print(f"Response: {result1}")
    print(f"Cached: {result1.get('cached', False)}")
    
    print(f"\nRetry with same key: {key}")
    result2, status2 = make_payment(key, order_id, 100.0)
    print(f"Status: {status2}")
    print(f"Response: {result2}")
    print(f"Cached: {result2.get('cached', False)}")
    
    if result1['payment_id'] == result2['payment_id'] and result2.get('cached'):
        print("\n✅ SUCCESS: Same payment returned, no duplicate charge!")
    else:
        print("\n❌ FAILED: Different payments or not cached")


def example_2_concurrent_requests():
    """Example 2: Concurrent requests with same key"""
    print("\n" + "="*60)
    print("Example 2: Concurrent Requests (Same Key)")
    print("="*60)
    
    key = str(uuid.uuid4())
    order_id = f"order_{uuid.uuid4().hex[:8]}"
    
    def make_request(request_num):
        result, status = make_payment(key, order_id, 50.0)
        return request_num, result, status
    
    print(f"\nSending 5 concurrent requests with key: {key}")
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(make_request, i) for i in range(5)]
        results = [f.result() for f in futures]
    
    payment_ids = [r[1]['payment_id'] for r in results]
    cached_count = sum(1 for r in results if r[1].get('cached', False))
    
    print(f"\nResults:")
    for req_num, result, status in results:
        print(f"  Request {req_num}: {result['payment_id']} (cached: {result.get('cached', False)})")
    
    unique_payments = len(set(payment_ids))
    if unique_payments == 1 and cached_count == 4:
        print("\n✅ SUCCESS: All requests returned same payment, 4 were cached!")
    else:
        print(f"\n⚠️  WARNING: {unique_payments} unique payments, {cached_count} cached")


def example_3_duplicate_order():
    """Example 3: Duplicate order ID with different key"""
    print("\n" + "="*60)
    print("Example 3: Duplicate Order ID (Different Keys)")
    print("="*60)
    
    order_id = f"order_{uuid.uuid4().hex[:8]}"
    key1 = str(uuid.uuid4())
    key2 = str(uuid.uuid4())
    
    print(f"\nFirst request - Order: {order_id}, Key: {key1}")
    result1, status1 = make_payment(key1, order_id, 200.0)
    print(f"Status: {status1}")
    print(f"Payment ID: {result1.get('payment_id', 'N/A')}")
    
    print(f"\nSecond request - Same Order: {order_id}, Different Key: {key2}")
    try:
        result2, status2 = make_payment(key2, order_id, 200.0)
        print(f"Status: {status2}")
        print(f"Response: {result2}")
    except Exception as e:
        print(f"Error: {e}")
        response = requests.post(
            f"{BASE_URL}/pay",
            headers={
                "Idempotency-Key": key2,
                "Content-Type": "application/json"
            },
            json={
                "order_id": order_id,
                "amount": 200.0,
                "currency": "INR"
            }
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 409:
            print("\n✅ SUCCESS: Duplicate order correctly rejected!")
        else:
            print("\n❌ FAILED: Expected 409 Conflict")


def example_4_missing_key():
    """Example 4: Missing idempotency key"""
    print("\n" + "="*60)
    print("Example 4: Missing Idempotency Key")
    print("="*60)
    
    order_id = f"order_{uuid.uuid4().hex[:8]}"
    
    print(f"\nRequest without Idempotency-Key header")
    response = requests.post(
        f"{BASE_URL}/pay",
        headers={"Content-Type": "application/json"},
        json={
            "order_id": order_id,
            "amount": 75.0,
            "currency": "INR"
        }
    )
    
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    
    if response.status_code == 400:
        print("\n✅ SUCCESS: Missing key correctly rejected!")
    else:
        print("\n❌ FAILED: Expected 400 Bad Request")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("Idempay Payment Service - Example Usage")
    print("="*60)
    print("\nMake sure the service is running: docker-compose up")
    print("Waiting 2 seconds for you to verify...")
    time.sleep(2)
    
    try:
        # Check if service is running
        response = requests.get(f"{BASE_URL}/health", timeout=2)
        if response.status_code != 200:
            print("⚠️  Service might not be running properly")
    except requests.exceptions.RequestException:
        print("❌ Cannot connect to service. Is it running?")
        print("   Start it with: docker-compose up")
        exit(1)
    
    # Run examples
    example_1_retry_same_key()
    time.sleep(1)
    
    example_2_concurrent_requests()
    time.sleep(1)
    
    example_3_duplicate_order()
    time.sleep(1)
    
    example_4_missing_key()
    
    print("\n" + "="*60)
    print("All examples complete!")
    print("="*60 + "\n")
