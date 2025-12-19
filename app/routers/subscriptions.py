from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, List
from app.models.subscription import SubscriptionPlan
from app.models.user import User  # Add this import
from app.services.subscription_service import subscription_service
from app.utils.dependencies import get_current_user


router = APIRouter()


@router.get("/plans", response_model=List[SubscriptionPlan])
async def get_subscription_plans():
    """Get all available subscription plans"""
    return await subscription_service.get_all_plans()


@router.get("/my-subscription")
async def get_my_subscription(current_user: User = Depends(get_current_user)):  # Changed to User
    """Get current user's subscription and credit details"""
    return await subscription_service.get_credit_summary(str(current_user.id))  # Use .id


@router.get("/credits/balance")
async def get_credit_balance(current_user: User = Depends(get_current_user)):  # Changed to User
    """Get user's current credit balance"""
    subscription = await subscription_service.get_or_create_user_subscription(
        str(current_user.id)  # Use .id
    )
    return {
        "total_credits": subscription.get_total_credits(),
        "current_plan": subscription.current_plan_type
    }
