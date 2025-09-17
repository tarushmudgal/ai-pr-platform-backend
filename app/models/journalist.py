from beanie import Document
from pymongo import IndexModel
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Literal
from datetime import datetime
from enum import Enum

class JournalistCategory(str, Enum):
    TECHNOLOGY = "technology"
    BUSINESS = "business"
    HEALTHCARE = "healthcare"
    FINANCE = "finance"
    LIFESTYLE = "lifestyle"
    ENTERTAINMENT = "entertainment"
    SPORTS = "sports"
    OTHER = "other"

class JournalistStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    BOUNCED = "bounced"

class ContactPreferences(BaseModel):
    best_time: Literal["morning", "afternoon", "evening"] = "morning"
    preferred_day: Literal["weekday", "weekend", "any"] = "weekday"
    response_time_avg_hours: Optional[int] = None

class JournalistStats(BaseModel):
    emails_received: int = 0
    responses_sent: int = 0
    articles_published: int = 0
    last_contacted: Optional[datetime] = None
    response_rate: float = 0.0

class Journalist(Document):
    # Added by user reference
    added_by_user_id: str  # Reference to User ID who added this journalist
    
    # Basic Info
    name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    publication: str = Field(..., min_length=1, max_length=100)
    
    # Categorization (simplified from complex beats)
    category: JournalistCategory
    topics: List[str] = Field(default_factory=list, max_items=10)  # max 10 topics
    
    # Location (simplified)
    country: str = Field(..., min_length=1, max_length=50)
    timezone: str = Field(default="UTC", max_length=50)
    
    # Engagement Tracking
    stats: JournalistStats = JournalistStats()
    
    # Contact Preferences
    contact_info: ContactPreferences = ContactPreferences()
    
    # Data Management
    source: Literal["manual", "imported", "api"] = "manual"
    verified: bool = False
    notes: Optional[str] = Field(None, max_length=500)  # User notes about this journalist
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    status: JournalistStatus = JournalistStatus.ACTIVE
    
    class Settings:
        collection = "journalists"
        indexes = [
            IndexModel([("added_by_user_id", 1)]),  # Find by user
            IndexModel([("email", 1)]),  # Email lookup
            IndexModel([("category", 1), ("country", 1)]),  # Category + location search
            IndexModel([("publication", 1)]),  # Publication search
            IndexModel([("name", "text"), ("publication", "text")]),  # Text search
        ]
    
    def update_response_rate(self):
        """Calculate and update response rate"""
        if self.stats.emails_received > 0:
            self.stats.response_rate = self.stats.responses_sent / self.stats.emails_received
        else:
            self.stats.response_rate = 0.0
    
    def record_email_sent(self):
        """Record that an email was sent to this journalist"""
        self.stats.emails_received += 1
        self.stats.last_contacted = datetime.utcnow()
        self.update_response_rate()
    
    def record_response_received(self):
        """Record that journalist responded"""
        self.stats.responses_sent += 1
        self.update_response_rate()
    
    def record_article_published(self):
        """Record that journalist published an article"""
        self.stats.articles_published += 1

# Pydantic models for API
class JournalistCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    publication: str = Field(..., min_length=1, max_length=100)
    category: JournalistCategory
    topics: List[str] = Field(default_factory=list, max_items=10)
    country: str = Field(..., min_length=1, max_length=50)
    timezone: str = Field(default="UTC", max_length=50)
    notes: Optional[str] = Field(None, max_length=500)
    contact_info: ContactPreferences = ContactPreferences()

class JournalistUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    publication: Optional[str] = Field(None, min_length=1, max_length=100)
    category: Optional[JournalistCategory] = None
    topics: Optional[List[str]] = Field(None, max_items=10)
    country: Optional[str] = Field(None, min_length=1, max_length=50)
    timezone: Optional[str] = Field(None, max_length=50)
    notes: Optional[str] = Field(None, max_length=500)
    contact_info: Optional[ContactPreferences] = None
    status: Optional[JournalistStatus] = None

class JournalistResponse(BaseModel):
    id: str
    name: str
    email: EmailStr
    publication: str
    category: JournalistCategory
    topics: List[str]
    country: str
    timezone: str
    stats: JournalistStats
    contact_info: ContactPreferences
    source: str
    verified: bool
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime
    status: JournalistStatus

class JournalistSearch(BaseModel):
    query: Optional[str] = None  # Search name/publication
    category: Optional[JournalistCategory] = None
    country: Optional[str] = None
    publication: Optional[str] = None
    status: Optional[JournalistStatus] = None
    verified_only: bool = False
    limit: int = Field(default=20, ge=1, le=100)
    skip: int = Field(default=0, ge=0)
