from beanie import Document
from pymongo import IndexModel
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Literal
from datetime import datetime
from enum import Enum

class InteractionType(str, Enum):
    EMAIL_SENT = "email_sent"
    EMAIL_OPENED = "email_opened"
    EMAIL_CLICKED = "email_clicked"
    RESPONSE_RECEIVED = "response_received"
    MEETING_SCHEDULED = "meeting_scheduled"
    ARTICLE_PUBLISHED = "article_published"

class EmailStatus(str, Enum):
    SENT = "sent"
    DELIVERED = "delivered"
    OPENED = "opened"
    CLICKED = "clicked"
    REPLIED = "replied"
    BOUNCED = "bounced"
    FAILED = "failed"

class EmailData(BaseModel):
    subject: str
    content: str
    sent_via: Literal["smtp", "manual"] = "smtp"
    message_id: Optional[str] = None
    opened_at: Optional[datetime] = None
    clicked_at: Optional[datetime] = None
    reply_content: Optional[str] = None

class Interaction(Document):
    # References
    user_id: str  # Reference to User
    journalist_id: str  # Reference to Journalist
    pitch_id: Optional[str] = None  # Reference to Pitch (optional)
    
    # Interaction Details
    type: InteractionType
    status: EmailStatus = EmailStatus.SENT
    
    # Email Specific Data
    email_data: Optional[EmailData] = None
    
    # Outcome Data
    response_received: bool = False
    response_content: Optional[str] = None
    sentiment: Optional[Literal["positive", "neutral", "negative"]] = None
    interest_level: Optional[Literal["high", "medium", "low"]] = None
    next_steps: Optional[str] = None
    
    # Timestamps
    interaction_date: datetime = Field(default_factory=datetime.utcnow)
    response_date: Optional[datetime] = None
    
    # Notes
    notes: Optional[str] = Field(None, max_length=500)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        collection = "interactions"
        indexes = [
            IndexModel([("user_id", 1)]),
            IndexModel([("journalist_id", 1)]),
            IndexModel([("pitch_id", 1)]),
            IndexModel([("user_id", 1), ("type", 1)]),
            IndexModel([("interaction_date", -1)]),
        ]
    
    def mark_as_opened(self):
        """Mark email as opened"""
        if self.email_data:
            self.email_data.opened_at = datetime.utcnow()
            self.status = EmailStatus.OPENED
            self.updated_at = datetime.utcnow()
    
    def mark_as_clicked(self):
        """Mark email as clicked"""
        if self.email_data:
            self.email_data.clicked_at = datetime.utcnow()
            self.status = EmailStatus.CLICKED
            self.updated_at = datetime.utcnow()
    
    def record_response(self, content: str, sentiment: Optional[str] = None):
        """Record journalist response"""
        self.response_received = True
        self.response_content = content
        self.response_date = datetime.utcnow()
        self.sentiment = sentiment
        self.status = EmailStatus.REPLIED
        self.updated_at = datetime.utcnow()

# Pydantic models for API
class InteractionCreate(BaseModel):
    journalist_id: str
    pitch_id: Optional[str] = None
    type: InteractionType
    email_subject: Optional[str] = None
    email_content: Optional[str] = None
    notes: Optional[str] = Field(None, max_length=500)

class InteractionResponse(BaseModel):
    id: str
    journalist_id: str
    pitch_id: Optional[str]
    type: InteractionType
    status: EmailStatus
    email_data: Optional[EmailData]
    response_received: bool
    response_content: Optional[str]
    sentiment: Optional[str]
    interaction_date: datetime
    response_date: Optional[datetime]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime
