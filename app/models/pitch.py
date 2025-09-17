from beanie import Document
from pymongo import IndexModel
from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from datetime import datetime
from enum import Enum

class AnnouncementType(str, Enum):
    PRODUCT_LAUNCH = "product_launch"
    FUNDING = "funding"
    PARTNERSHIP = "partnership"
    EXECUTIVE_HIRE = "executive_hire"
    AWARD = "award"
    RESEARCH = "research"
    OTHER = "other"

class PitchStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    SENT = "sent"
    ARCHIVED = "archived"

class PressRelease(BaseModel):
    headline: str
    body: str
    word_count: int

class EmailPitch(BaseModel):
    subject: str
    body: str
    word_count: int

class GeneratedContent(BaseModel):
    press_release: PressRelease
    email_pitch: EmailPitch

class GenerationMetadata(BaseModel):
    ai_model: str = "gpt-3.5-turbo"
    generation_time_ms: int
    quality_score: float = Field(ge=1.0, le=10.0)  # 1-10 rating
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None

class PitchPerformance(BaseModel):
    emails_sent: int = 0
    emails_opened: int = 0
    responses_received: int = 0
    articles_published: int = 0
    
    @property
    def open_rate(self) -> float:
        return self.emails_opened / self.emails_sent if self.emails_sent > 0 else 0.0
    
    @property
    def response_rate(self) -> float:
        return self.responses_received / self.emails_sent if self.emails_sent > 0 else 0.0

class Pitch(Document):
    # User reference
    user_id: str  # Reference to User ID
    
    # Input Data
    headline: str = Field(..., min_length=5, max_length=200)
    company_name: str = Field(..., min_length=1, max_length=100)
    key_points: List[str] = Field(..., min_items=1, max_items=10)
    industry: str = Field(..., min_length=1, max_length=50)
    announcement_type: AnnouncementType
    
    # Generated Content
    content: GeneratedContent
    
    # Metadata
    generation_info: GenerationMetadata
    
    # Performance Tracking
    performance: PitchPerformance = PitchPerformance()
    
    # Management
    status: PitchStatus = PitchStatus.DRAFT
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        collection = "pitches"
        indexes = [
            IndexModel([("user_id", 1)]),  # Find by user
            IndexModel([("user_id", 1), ("status", 1)]),  # User + status
            IndexModel([("created_at", -1)]),  # Recent first
            IndexModel([("announcement_type", 1)]),  # Filter by type
        ]
    
    def mark_as_sent(self):
        """Mark pitch as sent and update status"""
        self.status = PitchStatus.SENT
        self.updated_at = datetime.utcnow()
    
    def record_email_sent(self, count: int = 1):
        """Record that emails were sent"""
        self.performance.emails_sent += count
        self.updated_at = datetime.utcnow()
    
    def record_email_opened(self, count: int = 1):
        """Record email opens"""
        self.performance.emails_opened += count
        self.updated_at = datetime.utcnow()
    
    def record_response(self, count: int = 1):
        """Record responses received"""
        self.performance.responses_received += count
        self.updated_at = datetime.utcnow()
    
    def record_article_published(self, count: int = 1):
        """Record articles published"""
        self.performance.articles_published += count
        self.updated_at = datetime.utcnow()

# Pydantic models for API
class PitchCreate(BaseModel):
    headline: str = Field(..., min_length=5, max_length=200)
    company_name: str = Field(..., min_length=1, max_length=100)
    key_points: List[str] = Field(..., min_items=1, max_items=10)
    industry: str = Field(..., min_length=1, max_length=50)
    announcement_type: AnnouncementType

class PitchResponse(BaseModel):
    id: str
    headline: str
    company_name: str
    key_points: List[str]
    industry: str
    announcement_type: AnnouncementType
    content: GeneratedContent
    generation_info: GenerationMetadata
    performance: PitchPerformance
    status: PitchStatus
    created_at: datetime
    updated_at: datetime

class PitchUpdate(BaseModel):
    headline: Optional[str] = Field(None, min_length=5, max_length=200)
    company_name: Optional[str] = Field(None, min_length=1, max_length=100)
    key_points: Optional[List[str]] = Field(None, min_items=1, max_items=10)
    industry: Optional[str] = Field(None, min_length=1, max_length=50)
    announcement_type: Optional[AnnouncementType] = None
    status: Optional[PitchStatus] = None

class PitchSearch(BaseModel):
    query: Optional[str] = None  # Search headline/company
    industry: Optional[str] = None
    announcement_type: Optional[AnnouncementType] = None
    status: Optional[PitchStatus] = None
    limit: int = Field(default=20, ge=1, le=100)
    skip: int = Field(default=0, ge=0)
