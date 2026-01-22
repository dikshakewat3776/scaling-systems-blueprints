from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class PaymentRequest(BaseModel):
    order_id: str = Field(..., description="Unique order identifier")
    amount: float = Field(..., gt=0, description="Payment amount")
    currency: str = Field(default="INR", description="Currency code")
    customer_id: Optional[str] = Field(None, description="Customer identifier")


class PaymentResponse(BaseModel):
    payment_id: str
    order_id: str
    amount: float
    currency: str
    customer_id: Optional[str]
    status: str
    created_at: datetime
    processed_at: Optional[datetime]
    cached: bool = False

    class Config:
        from_attributes = True
