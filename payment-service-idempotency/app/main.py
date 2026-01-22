"""
FastAPI Application - Payment Service Entry Point

This is the main application file that sets up:
1. FastAPI application with middleware
2. Database connection and table creation
3. API endpoints for payment processing
4. Request/response validation via Pydantic schemas

The idempotency middleware is added globally to intercept
all POST /pay requests and ensure idempotent behavior.
"""

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.database import get_db, engine, Base
from app.models import Payment
from app.schemas import PaymentRequest, PaymentResponse
from app.services.payment_service import PaymentService
from app.middleware.idempotency import IdempotencyMiddleware
from app.config import settings

# Create database tables on startup
# In production, use Alembic migrations instead
Base.metadata.create_all(bind=engine)

# Initialize FastAPI application
app = FastAPI(
    title="Idempay - Payment Service with Idempotency",
    description="A production-ready payment service demonstrating idempotency patterns",
    version="1.0.0"
)

# Add idempotency middleware globally
# This middleware intercepts all requests and applies idempotency
# logic to POST /pay endpoints
app.add_middleware(IdempotencyMiddleware)


@app.get("/")
async def root():
    return {
        "message": "Idempay Payment Service",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.post("/pay", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
async def process_payment(
    request: PaymentRequest,
    db: Session = Depends(get_db)
):
    """
    Process a payment request.
    
    Requires Idempotency-Key header to prevent duplicate payments.
    """
    try:
        payment = PaymentService.create_payment(db, request)
        payment_dict = payment.to_dict()
        payment_dict["processed_at"] = payment.processed_at.isoformat() if payment.processed_at else None
        payment_dict["created_at"] = payment.created_at.isoformat() if payment.created_at else None
        return PaymentResponse(**payment_dict)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@app.get("/payments/{payment_id}", response_model=PaymentResponse)
async def get_payment(
    payment_id: str,
    db: Session = Depends(get_db)
):
    """Get payment details by payment_id"""
    payment = PaymentService.get_payment_by_id(db, payment_id)
    payment_dict = payment.to_dict()
    payment_dict["processed_at"] = payment.processed_at.isoformat() if payment.processed_at else None
    payment_dict["created_at"] = payment.created_at.isoformat() if payment.created_at else None
    return PaymentResponse(**payment_dict)


@app.get("/payments/order/{order_id}", response_model=PaymentResponse)
async def get_payment_by_order(
    order_id: str,
    db: Session = Depends(get_db)
):
    """Get payment details by order_id"""
    payment = PaymentService.get_payment_by_order_id(db, order_id)
    payment_dict = payment.to_dict()
    payment_dict["processed_at"] = payment.processed_at.isoformat() if payment.processed_at else None
    payment_dict["created_at"] = payment.created_at.isoformat() if payment.created_at else None
    return PaymentResponse(**payment_dict)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
