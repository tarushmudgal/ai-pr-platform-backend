from datetime import datetime, timedelta
from typing import Optional, List
from pydantic import BaseModel, Field
from beanie import Document, Indexed
from enum import Enum


class PlanType(str, Enum):
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"
    TOPUP = "topup"


class CreditTransaction(BaseModel):
    """Individual credit transaction record"""
    transaction_id: str
    amount: float
    transaction_type: str  # "purchase", "usage", "expiry", "refund"
    description: str
    feature: Optional[str] = None  # "pitch_generation", "email_send", "ai_chat"
    metadata: dict = {}
    created_at: datetime = Field(default_factory=datetime.utcnow)


class CreditBalance(BaseModel):
    """Credit balance with expiry tracking"""
    amount: float
    purchased_at: datetime
    expires_at: datetime
    plan_type: PlanType
    is_expired: bool = False
    
    def is_valid(self) -> bool:
        """Check if credits are still valid"""
        return not self.is_expired and datetime.utcnow() < self.expires_at


class SubscriptionPlan(Document):
    """Subscription plans available for purchase"""
    plan_id: Indexed(str, unique=True)
    name: str
    plan_type: PlanType
    price: float  # in INR
    credits: float
    validity_days: int = 90  # Credits expire after 90 days
    
    # Features included
    features: dict = {
        "pitch_generation": True,
        "email_sending": True,
        "ai_chat": True,
        "journalist_management": True,
        "analytics": True,
        "api_access": False,
        "priority_support": False
    }
    
    # Usage rates (credits per action)
    usage_rates: dict = {
        "pitch_generation": 2.0,
        "pitch_regeneration": 2.0,
        "pitch_rewrite": 1.0,
        "email_send_per_recipient": 0.1,
        "ai_chat_message": 0.5
    }
    
    is_active: bool = True
    display_order: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        name = "subscription_plans"
        indexes = ["plan_id", "plan_type"]


class UserSubscription(Document):
    """User's subscription and credit management"""
    user_id: Indexed(str)
    
    # Current plan
    current_plan_type: Optional[PlanType] = None
    
    # Credit balances (multiple balances with different expiry dates)
    credit_balances: List[CreditBalance] = []
    
    # Transaction history
    transactions: List[CreditTransaction] = []
    
    # Usage statistics
    usage_stats: dict = {
        "pitch_generation": 0,
        "pitch_regeneration": 0,
        "pitch_rewrite": 0,
        "email_send": 0,
        "ai_chat_messages": 0,
        "total_credits_purchased": 0.0,
        "total_credits_used": 0.0,
        "total_credits_expired": 0.0
    }
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        name = "user_subscriptions"
        indexes = ["user_id"]
    
    def get_total_credits(self) -> float:
        """Get total available credits (excluding expired)"""
        self._expire_old_credits()
        return sum(balance.amount for balance in self.credit_balances if balance.is_valid())
    
    def _expire_old_credits(self):
        """Mark expired credits"""
        now = datetime.utcnow()
        for balance in self.credit_balances:
            if not balance.is_expired and now >= balance.expires_at:
                balance.is_expired = True
                self.usage_stats["total_credits_expired"] += balance.amount
                self.transactions.append(CreditTransaction(
                    transaction_id=f"exp_{datetime.utcnow().timestamp()}",
                    amount=-balance.amount,
                    transaction_type="expiry",
                    description=f"Credits expired from {balance.plan_type} plan"
                ))
    
    def deduct_credits(self, amount: float, feature: str, description: str) -> bool:
        """
        Deduct credits using FIFO (First In First Out) - oldest credits first
        Returns True if successful, False if insufficient credits
        """
        self._expire_old_credits()
        
        total_available = self.get_total_credits()
        if total_available < amount:
            return False
        
        remaining_to_deduct = amount
        
        # Sort by purchase date (oldest first)
        valid_balances = sorted(
            [b for b in self.credit_balances if b.is_valid()],
            key=lambda x: x.purchased_at
        )
        
        for balance in valid_balances:
            if remaining_to_deduct <= 0:
                break
            
            deduction = min(balance.amount, remaining_to_deduct)
            balance.amount -= deduction
            remaining_to_deduct -= deduction
        
        # Record transaction
        self.transactions.append(CreditTransaction(
            transaction_id=f"usage_{datetime.utcnow().timestamp()}",
            amount=-amount,
            transaction_type="usage",
            description=description,
            feature=feature
        ))
        
        self.usage_stats["total_credits_used"] += amount
        self.updated_at = datetime.utcnow()
        
        return True
    
    def add_credits(self, amount: float, plan_type: PlanType, validity_days: int = 90):
        """Add credits with expiry date"""
        now = datetime.utcnow()
        expires_at = now + timedelta(days=validity_days)
        
        self.credit_balances.append(CreditBalance(
            amount=amount,
            purchased_at=now,
            expires_at=expires_at,
            plan_type=plan_type
        ))
        
        self.usage_stats["total_credits_purchased"] += amount
        self.current_plan_type = plan_type
        self.updated_at = now
