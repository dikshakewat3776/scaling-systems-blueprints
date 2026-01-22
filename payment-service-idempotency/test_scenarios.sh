#!/bin/bash

# Test scenarios for Idempay Payment Service
# Make sure the service is running: docker-compose up

BASE_URL="http://localhost:8000"

echo "🧪 Testing Idempay Payment Service"
echo "=================================="
echo ""

# Generate a unique idempotency key
IDEMPOTENCY_KEY=$(uuidgen)

echo "📝 Scenario 1: Normal Payment Request"
echo "Idempotency Key: $IDEMPOTENCY_KEY"
echo ""

RESPONSE=$(curl -s -X POST "$BASE_URL/pay" \
  -H "Idempotency-Key: $IDEMPOTENCY_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "order_id": "order_test_1",
    "amount": 100.50,
    "currency": "INR",
    "customer_id": "cust_123"
  }')

echo "Response: $RESPONSE"
echo ""

echo "🔄 Scenario 2: Retry with Same Idempotency Key (Should Return Cached Response)"
echo ""

RETRY_RESPONSE=$(curl -s -X POST "$BASE_URL/pay" \
  -H "Idempotency-Key: $IDEMPOTENCY_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "order_id": "order_test_1",
    "amount": 100.50,
    "currency": "INR",
    "customer_id": "cust_123"
  }')

echo "Response: $RETRY_RESPONSE"
echo ""

if echo "$RETRY_RESPONSE" | grep -q "cached"; then
  echo "✅ SUCCESS: Cached response returned"
else
  echo "❌ FAILED: Expected cached response"
fi
echo ""

echo "🚫 Scenario 3: Duplicate Order ID with Different Idempotency Key"
echo ""

NEW_KEY=$(uuidgen)
DUPLICATE_RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X POST "$BASE_URL/pay" \
  -H "Idempotency-Key: $NEW_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "order_id": "order_test_1",
    "amount": 100.50,
    "currency": "INR",
    "customer_id": "cust_123"
  }')

HTTP_CODE=$(echo "$DUPLICATE_RESPONSE" | grep "HTTP_CODE" | cut -d: -f2)
RESPONSE_BODY=$(echo "$DUPLICATE_RESPONSE" | grep -v "HTTP_CODE")

echo "Response: $RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"
echo ""

if [ "$HTTP_CODE" = "409" ]; then
  echo "✅ SUCCESS: Duplicate order correctly rejected"
else
  echo "❌ FAILED: Expected 409 Conflict"
fi
echo ""

echo "❌ Scenario 4: Missing Idempotency Key"
echo ""

MISSING_KEY_RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X POST "$BASE_URL/pay" \
  -H "Content-Type: application/json" \
  -d '{
    "order_id": "order_test_no_key",
    "amount": 50.00,
    "currency": "INR"
  }')

HTTP_CODE=$(echo "$MISSING_KEY_RESPONSE" | grep "HTTP_CODE" | cut -d: -f2)
RESPONSE_BODY=$(echo "$MISSING_KEY_RESPONSE" | grep -v "HTTP_CODE")

echo "Response: $RESPONSE_BODY"
echo "HTTP Status: $HTTP_CODE"
echo ""

if [ "$HTTP_CODE" = "400" ]; then
  echo "✅ SUCCESS: Missing key correctly rejected"
else
  echo "❌ FAILED: Expected 400 Bad Request"
fi
echo ""

echo "🏁 Test Scenarios Complete!"
