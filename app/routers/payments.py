from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import JSONResponse
import razorpay
from typing import Dict, Any
import hmac
import hashlib
from datetime import datetime

from app.config import settings
from app.models.payment import PaymentOrderCreate, PaymentVerification
from app.models.user import User  # Add this import
from app.database import get_database
from app.utils.dependencies import get_current_user
from app.services.subscription_service import subscription_service

router = APIRouter()

razorpay_client = razorpay.Client(auth=(settings.razorpay_key_id, settings.razorpay_key_secret))
razorpay_client.set_app_details({"title": "PR Platform", "version": "1.0.0"})


@router.post("/create-order")
async def create_payment_order(
    order_data: PaymentOrderCreate,
    current_user: User = Depends(get_current_user),
    db = Depends(get_database)
):
    """Create Razorpay order for plan purchase"""
    try:
        plan = await subscription_service.get_plan_by_id(order_data.plan_id)
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")
        
        # Generate shorter receipt ID (max 40 chars)
        import time
        timestamp = int(time.time())
        receipt_id = f"rcpt_{timestamp}"  # Format: rcpt_1734428400 (max ~15 chars)
        
        # Create order in Razorpay
        razorpay_order = razorpay_client.order.create({
            "amount": int(plan.price * 100),  # Convert to paise
            "currency": "INR",
            "receipt": receipt_id,  # Use shorter receipt ID
            "notes": {
                "user_id": str(current_user.id),
                "user_email": current_user.email if hasattr(current_user, 'email') else "",
                "plan_id": plan.plan_id,
                "plan_name": plan.name,
                "credits": str(plan.credits)
            }
        })
        
        payment_record = {
            "user_id": str(current_user.id),
            "razorpay_order_id": razorpay_order["id"],
            "receipt_id": receipt_id,  # Store for reference
            "amount": plan.price,
            "currency": "INR",
            "status": "created",
            "plan_id": plan.plan_id,
            "plan_name": plan.name,
            "credits": plan.credits,
            "created_at": datetime.utcnow()
        }
        
        await db.payments.insert_one(payment_record)
        
        return {
            "order_id": razorpay_order["id"],
            "amount": razorpay_order["amount"],
            "currency": razorpay_order["currency"],
            "key_id": settings.razorpay_key_id,
            "plan_name": plan.name,
            "credits": plan.credits
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Payment order creation failed: {str(e)}")


@router.post("/verify-payment")
async def verify_payment(
    payment_data: PaymentVerification,
    current_user: User = Depends(get_current_user),  # Changed to User
    db = Depends(get_database)
):
    """Verify payment and add credits to user account"""
    try:
        params_dict = {
            'razorpay_order_id': payment_data.razorpay_order_id,
            'razorpay_payment_id': payment_data.razorpay_payment_id,
            'razorpay_signature': payment_data.razorpay_signature
        }
        
        razorpay_client.utility.verify_payment_signature(params_dict)
        
        payment_record = await db.payments.find_one(
            {"razorpay_order_id": payment_data.razorpay_order_id}
        )
        
        if not payment_record:
            raise HTTPException(status_code=404, detail="Payment record not found")
        
        subscription = await subscription_service.add_credits_after_payment(
            user_id=str(current_user.id),
            plan_id=payment_record["plan_id"],
            payment_id=payment_data.razorpay_payment_id
        )
        
        await db.payments.update_one(
            {"razorpay_order_id": payment_data.razorpay_order_id},
            {
                "$set": {
                    "razorpay_payment_id": payment_data.razorpay_payment_id,
                    "razorpay_signature": payment_data.razorpay_signature,
                    "status": "success",
                    "verified_at": datetime.utcnow(),
                    "credits_added": payment_record["credits"]
                }
            }
        )
        
        payment_details = razorpay_client.payment.fetch(payment_data.razorpay_payment_id)
        
        return {
            "status": "success",
            "message": "Payment verified and credits added successfully",
            "payment_id": payment_data.razorpay_payment_id,
            "order_id": payment_data.razorpay_order_id,
            "credits_added": payment_record["credits"],
            "total_credits": subscription.get_total_credits(),
            "payment_method": payment_details.get("method")
        }
        
    except razorpay.errors.SignatureVerificationError:
        await db.payments.update_one(
            {"razorpay_order_id": payment_data.razorpay_order_id},
            {"$set": {"status": "failed", "failure_reason": "Invalid signature"}}
        )
        raise HTTPException(status_code=400, detail="Payment verification failed")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Verification error: {str(e)}")
