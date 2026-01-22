"""
Payment Service - Core Business Logic

This module implements the payment processing logic with state management.
It handles the complete payment lifecycle: INITIATED → PROCESSING → SUCCESS/FAILED

Key Design Decisions:
1. State Machine: Payments transition through explicit states to track progress
2. Database Constraints: Unique constraint on order_id prevents duplicate orders
3. Gateway Simulation: Realistic failure scenarios (timeout, rejection) for testing
4. Error Handling: Proper rollback on failures, clear error messages
"""

import uuid
import random
import time
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status
from app.models import Payment
from app.schemas import PaymentRequest, PaymentResponse


class PaymentService:
    """
    Payment Service handles all payment processing operations.
    
    This service implements:
    - Payment state machine (INITIATED → PROCESSING → SUCCESS/FAILED)
    - Gateway integration simulation
    - Database constraint enforcement (unique order_id)
    - Error handling and rollback mechanisms
    """
    
    # Probability constants for realistic gateway simulation
    TIMEOUT_PROBABILITY = 0.1  # 10% chance of timeout (simulates network issues)
    FAILURE_PROBABILITY = 0.05  # 5% chance of failure (simulates gateway rejection)

    @staticmethod
    def generate_payment_id() -> str:
        """
        Generate a unique payment identifier.
        
        Format: pay_{12-char-hex}
        Example: pay_a1b2c3d4e5f6
        
        Returns:
            str: Unique payment ID
        """
        return f"pay_{uuid.uuid4().hex[:12]}"

    @staticmethod
    def simulate_gateway_call() -> tuple[bool, Optional[str]]:
        """
        Simulate a payment gateway API call with realistic failure scenarios.
        
        This simulates:
        - Network latency (100-500ms delay)
        - Timeout errors (10% probability)
        - Gateway rejections (5% probability)
        
        In production, this would be replaced with actual gateway API calls
        (e.g., Stripe, PayPal, Razorpay).
        
        Returns:
            tuple[bool, Optional[str]]: 
                - (True, None) on success
                - (False, error_message) on gateway rejection
                
        Raises:
            TimeoutError: When gateway times out (simulates network failure)
        """
        # Simulate realistic network delay (100-500ms)
        # In production, this is actual network latency to payment gateway
        time.sleep(random.uniform(0.1, 0.5))

        # Simulate timeout scenario (10% chance)
        # This represents network timeouts, gateway unavailability, etc.
        if random.random() < PaymentService.TIMEOUT_PROBABILITY:
            raise TimeoutError("Payment gateway timeout")

        # Simulate gateway rejection (5% chance)
        # This represents declined cards, insufficient funds, fraud detection, etc.
        if random.random() < PaymentService.FAILURE_PROBABILITY:
            return False, "Payment gateway rejected transaction"

        # Successful payment processing
        return True, None

    @staticmethod
    def create_payment(db: Session, request: PaymentRequest) -> Payment:
        """
        Create and process a payment transaction.
        
        This method implements the payment state machine:
        1. INITIATED: Payment record created in database
        2. PROCESSING: Payment sent to gateway
        3. SUCCESS/FAILED: Final state based on gateway response
        
        Database Constraints:
        - Unique constraint on order_id prevents duplicate orders
        - This works in conjunction with idempotency keys:
          * Same idempotency key → cached response (no DB insert)
          * Different idempotency key + same order_id → 409 Conflict
        
        Args:
            db: Database session
            request: Payment request with order_id, amount, currency, customer_id
            
        Returns:
            Payment: Created payment object with final status
            
        Raises:
            HTTPException 409: If order_id already exists (duplicate order)
            HTTPException 500: If database operation fails
            HTTPException 504: If payment gateway times out
        """
        # Generate unique payment identifier
        payment_id = PaymentService.generate_payment_id()

        # Step 1: Create payment record with INITIATED status
        # This ensures we have a record even if gateway call fails
        payment = Payment(
            payment_id=payment_id,
            order_id=request.order_id,
            amount=request.amount,
            currency=request.currency,
            customer_id=request.customer_id,
            status="INITIATED"  # Initial state in state machine
        )

        try:
            # Insert payment into database
            # This will fail if order_id already exists (unique constraint)
            db.add(payment)
            db.commit()
            db.refresh(payment)
        except IntegrityError as e:
            # Rollback transaction on constraint violation
            db.rollback()
            
            # Check if error is due to duplicate order_id
            # This is a critical check: even with different idempotency keys,
            # we should not allow duplicate orders
            if "order_id" in str(e):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Order {request.order_id} already exists"
                )
            # Other integrity errors (e.g., duplicate payment_id - very unlikely)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create payment"
            )

        # Step 2: Update status to PROCESSING
        # This indicates payment is being sent to gateway
        payment.status = "PROCESSING"
        db.commit()
        db.refresh(payment)

        try:
            # Step 3: Call payment gateway
            # This simulates the actual payment processing
            success, error_message = PaymentService.simulate_gateway_call()
            
            # Step 4: Update final status based on gateway response
            if success:
                payment.status = "SUCCESS"
            else:
                payment.status = "FAILED"
                # Store error details in payment_metadata for debugging/auditing
                payment.payment_metadata = {"error": error_message}
            
            # Record when payment was processed
            payment.processed_at = datetime.utcnow()
            db.commit()
            db.refresh(payment)

        except TimeoutError:
            # Gateway timeout scenario
            # Payment remains in PROCESSING state (not yet completed)
            # In production, this would trigger:
            # - Async retry mechanism
            # - Webhook to handle eventual completion
            # - Manual review queue for stuck payments
            payment.status = "PROCESSING"
            payment.payment_metadata = {"error": "Gateway timeout"}
            db.commit()
            db.refresh(payment)
            
            # Return timeout error to client
            # Client can retry with same idempotency key
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="Payment gateway timeout - please retry"
            )

        return payment

    @staticmethod
    def get_payment_by_id(db: Session, payment_id: str) -> Payment:
        """Get payment by payment_id"""
        payment = db.query(Payment).filter(Payment.payment_id == payment_id).first()
        if not payment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Payment {payment_id} not found"
            )
        return payment

    @staticmethod
    def get_payment_by_order_id(db: Session, order_id: str) -> Payment:
        """Get payment by order_id"""
        payment = db.query(Payment).filter(Payment.order_id == order_id).first()
        if not payment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Payment for order {order_id} not found"
            )
        return payment
