from typing import Optional, Dict, List
from datetime import datetime, timedelta
from fastapi import HTTPException
from beanie import PydanticObjectId
import uuid

from app.models.subscription import (
    SubscriptionPlan, 
    UserSubscription, 
    PlanType,
    CreditTransaction,
    CreditBalance
)
from app.models.user import User


class SubscriptionService:
    
    @staticmethod
    async def initialize_default_plans():
        """Initialize the 3 default subscription plans"""
        
        plans = [
            # Starter Plan - ₹999
            {
                "plan_id": "starter_plan",
                "name": "Starter Plan",
                "plan_type": PlanType.STARTER,
                "price": 999.0,
                "credits": 100.0,
                "validity_days": 90,
                "features": {
                    "pitch_generation": True,
                    "email_sending": True,
                    "ai_chat": True,
                    "journalist_management": True,
                    "analytics": True,
                    "api_access": False,
                    "priority_support": False,
                    "max_journalists": 500,
                    "max_pitches": 50
                },
                "usage_rates": {
                    "pitch_generation": 2.0,
                    "pitch_regeneration": 2.0,
                    "pitch_rewrite": 1.0,
                    "email_send_per_recipient": 0.1,
                    "ai_chat_message": 0.5
                },
                "display_order": 1
            },
            
            # Professional Plan - ₹2,999
            {
                "plan_id": "professional_plan",
                "name": "Professional Plan",
                "plan_type": PlanType.PROFESSIONAL,
                "price": 2999.0,
                "credits": 400.0,  # 33% bonus credits
                "validity_days": 90,
                "features": {
                    "pitch_generation": True,
                    "email_sending": True,
                    "ai_chat": True,
                    "journalist_management": True,
                    "analytics": True,
                    "api_access": True,
                    "priority_support": True,
                    "max_journalists": 2000,
                    "max_pitches": 200
                },
                "usage_rates": {
                    "pitch_generation": 2.0,
                    "pitch_regeneration": 2.0,
                    "pitch_rewrite": 1.0,
                    "email_send_per_recipient": 0.1,
                    "ai_chat_message": 0.5
                },
                "display_order": 2
            },
            
            # Enterprise Plan - ₹9,999
            {
                "plan_id": "enterprise_plan",
                "name": "Enterprise Plan",
                "plan_type": PlanType.ENTERPRISE,
                "price": 9999.0,
                "credits": 1500.0,  # 50% bonus credits
                "validity_days": 90,
                "features": {
                    "pitch_generation": True,
                    "email_sending": True,
                    "ai_chat": True,
                    "journalist_management": True,
                    "analytics": True,
                    "api_access": True,
                    "priority_support": True,
                    "max_journalists": 10000,
                    "max_pitches": 1000,
                    "dedicated_account_manager": True,
                    "custom_integrations": True
                },
                "usage_rates": {
                    "pitch_generation": 1.5,  # Discounted rates
                    "pitch_regeneration": 1.5,
                    "pitch_rewrite": 0.8,
                    "email_send_per_recipient": 0.08,
                    "ai_chat_message": 0.4
                },
                "display_order": 3
            },
            
            # Top-up Pack - ₹499 (for 50 credits)
            {
                "plan_id": "topup_50",
                "name": "Credit Top-up (50 Credits)",
                "plan_type": PlanType.TOPUP,
                "price": 499.0,
                "credits": 50.0,
                "validity_days": 90,
                "features": {},
                "usage_rates": {},
                "display_order": 4
            }
        ]
        
        for plan_data in plans:
            # Use dictionary-style query instead of attribute access
            existing = await SubscriptionPlan.find_one({"plan_id": plan_data["plan_id"]})
            
            if not existing:
                plan = SubscriptionPlan(**plan_data)
                await plan.insert()
                print(f"✅ Created plan: {plan.name}")
    
    @staticmethod
    async def get_all_plans() -> List[SubscriptionPlan]:
        """Get all active subscription plans"""
        plans = await SubscriptionPlan.find({"is_active": True}).sort("+display_order").to_list()
        return plans
    
    @staticmethod
    async def get_plan_by_id(plan_id: str) -> Optional[SubscriptionPlan]:
        """Get plan by ID"""
        return await SubscriptionPlan.find_one({"plan_id": plan_id})
    
    @staticmethod
    async def get_or_create_user_subscription(user_id: str) -> UserSubscription:
        """Get or create user subscription record"""
        subscription = await UserSubscription.find_one({"user_id": user_id})
        
        if not subscription:
            subscription = UserSubscription(user_id=user_id)
            await subscription.insert()
        
        return subscription
    
    @staticmethod
    async def check_and_deduct_credits(
        user_id: str,
        feature: str,
        amount: Optional[float] = None,
        metadata: dict = {}
    ) -> Dict:
        """
        Check if user has sufficient credits and deduct them
        Returns: {"success": bool, "remaining_credits": float, "message": str}
        """
        subscription = await SubscriptionService.get_or_create_user_subscription(user_id)
        
        # Get the user's current plan to determine usage rate
        if subscription.current_plan_type:
            plan = await SubscriptionPlan.find_one({"plan_type": subscription.current_plan_type})
            
            if not plan:
                # Fallback to default rates
                usage_rates = {
                    "pitch_generation": 2.0,
                    "pitch_regeneration": 2.0,
                    "pitch_rewrite": 1.0,
                    "email_send_per_recipient": 0.1,
                    "ai_chat_message": 0.5
                }
            else:
                usage_rates = plan.usage_rates
        else:
            # No plan, use default rates
            usage_rates = {
                "pitch_generation": 2.0,
                "pitch_regeneration": 2.0,
                "pitch_rewrite": 1.0,
                "email_send_per_recipient": 0.1,
                "ai_chat_message": 0.5
            }
        
        # Calculate credit cost
        if amount is None:
            credit_cost = usage_rates.get(feature, 1.0)
        else:
            credit_cost = amount
        
        # Update usage stats key
        stats_key_map = {
            "pitch_generation": "pitch_generation",
            "pitch_regeneration": "pitch_regeneration",
            "pitch_rewrite": "pitch_rewrite",
            "email_send_per_recipient": "email_send",
            "ai_chat_message": "ai_chat_messages"
        }
        stats_key = stats_key_map.get(feature, feature)
        
        # Check and deduct credits
        success = subscription.deduct_credits(
            amount=credit_cost,
            feature=feature,
            description=f"Used {credit_cost} credits for {feature}",
        )
        
        if success:
            # Update usage stats
            if stats_key in subscription.usage_stats:
                subscription.usage_stats[stats_key] += 1
            
            await subscription.save()
            
            return {
                "success": True,
                "remaining_credits": subscription.get_total_credits(),
                "credits_used": credit_cost,
                "message": f"Successfully deducted {credit_cost} credits"
            }
        else:
            available = subscription.get_total_credits()
            return {
                "success": False,
                "remaining_credits": available,
                "credits_needed": credit_cost,
                "message": f"Insufficient credits. Need {credit_cost}, have {available}"
            }
    
    @staticmethod
    async def add_credits_after_payment(
        user_id: str,
        plan_id: str,
        payment_id: str
    ) -> UserSubscription:
        """Add credits to user after successful payment"""
        plan = await SubscriptionService.get_plan_by_id(plan_id)
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")
        
        subscription = await SubscriptionService.get_or_create_user_subscription(user_id)
        
        # Add credits
        subscription.add_credits(
            amount=plan.credits,
            plan_type=plan.plan_type,
            validity_days=plan.validity_days
        )
        
        # Record transaction
        subscription.transactions.append(CreditTransaction(
            transaction_id=payment_id,
            amount=plan.credits,
            transaction_type="purchase",
            description=f"Purchased {plan.name}",
            metadata={"plan_id": plan_id, "price": plan.price}
        ))
        
        await subscription.save()
        return subscription
    
    @staticmethod
    async def get_credit_summary(user_id: str) -> Dict:
        """Get detailed credit summary for user"""
        subscription = await SubscriptionService.get_or_create_user_subscription(user_id)
        
        # Get valid balances with expiry info
        valid_balances = []
        for balance in subscription.credit_balances:
            if balance.is_valid():
                days_until_expiry = (balance.expires_at - datetime.utcnow()).days
                valid_balances.append({
                    "amount": balance.amount,
                    "plan_type": balance.plan_type,
                    "purchased_at": balance.purchased_at,
                    "expires_at": balance.expires_at,
                    "days_until_expiry": days_until_expiry
                })
        
        return {
            "total_credits": subscription.get_total_credits(),
            "credit_balances": valid_balances,
            "current_plan": subscription.current_plan_type,
            "usage_stats": subscription.usage_stats,
            "recent_transactions": subscription.transactions[-10:]  # Last 10
        }


subscription_service = SubscriptionService()
