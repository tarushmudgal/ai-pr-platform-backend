from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class PaymentOrderCreate(BaseModel):
    plan_id: str
    #receipt_id: str = Field(default_factory=lambda: f"rcpt_{int(datetime.utcnow().timestamp())}")

class PaymentVerification(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str
    timestamp: Optional[datetime] = None
