from beanie import Document, Indexed
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Literal, Annotated
from datetime import datetime
from enum import Enum

class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"

class UserPlan(str, Enum):
    FREE = "free"
    PRO = "pro"

class UserPreferences(BaseModel):
    default_tone: str = "professional"
    email_signature: str = ""

class User(Document):
    # Authentication - Fix the Indexed syntax
    email: Annotated[EmailStr, Indexed(unique=True)]
    password_hash: str = Field(..., exclude=True)
    
    # Profile
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)
    company_name: str = Field(..., min_length=1, max_length=100)
    role: UserRole = UserRole.USER
    
    # Subscription
    plan: UserPlan = UserPlan.FREE
    credits_remaining: int = 100
    
    # Settings
    preferences: UserPreferences = UserPreferences()
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None
    status: Literal["active", "inactive", "pending"] = "active"  # Add pending for email verification

    # ADD THESE NEW FIELDS for email verification and password reset
    email_verified: bool = False
    verification_code: Optional[str] = None
    verification_code_expires: Optional[datetime] = None
    reset_code: Optional[str] = None
    reset_code_expires: Optional[datetime] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        collection = "users"
        
    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"
    
    # Method to check if user can perform action (credit-based)
    def can_use_credits(self, credits_needed: int = 1) -> bool:
        return self.credits_remaining >= credits_needed
    
    def use_credits(self, credits_used: int = 1) -> bool:
        if self.can_use_credits(credits_used):
            self.credits_remaining -= credits_used
            return True
        return False

# Pydantic models for API requests/responses (these remain the same)
class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=100)
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)
    company_name: str = Field(..., min_length=1, max_length=100)

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: str
    email: EmailStr
    first_name: str
    last_name: str
    company_name: str
    role: UserRole
    plan: UserPlan
    credits_remaining: int
    preferences: UserPreferences
    created_at: datetime
    last_login: Optional[datetime]
    status: str
    email_verified: bool = False  # ADD THIS
    
    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse
