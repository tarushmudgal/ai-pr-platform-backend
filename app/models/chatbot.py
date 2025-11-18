"""
# app/models/chatbot.py
from beanie import Document, Indexed
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime
from enum import Enum

class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

class ActionType(str, Enum):
    GENERATE_PITCH = "generate_pitch"
    SEND_EMAIL = "send_email"
    CREATE_NEWSROOM = "create_newsroom"
    UPLOAD_MEDIA = "upload_media"
    ADD_JOURNALIST = "add_journalist"
    GET_ANALYTICS = "get_analytics"
    SEARCH_PITCHES = "search_pitches"
    UPDATE_SETTINGS = "update_settings"
    SEARCH_JOURNALISTS = "search_journalists"

class ChatAction(BaseModel):
    type: ActionType
    parameters: Dict[str, Any] = Field(default_factory=dict)
    status: Literal["pending", "completed", "failed"] = "pending"
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    executed_at: Optional[datetime] = None

class ChatMessage(BaseModel):
    role: MessageRole
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    actions: List[ChatAction] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ChatSession(Document):
    user_id: str = Field(..., description="User ID who owns this chat session")
    session_name: str = Field(default="New Chat")
    messages: List[ChatMessage] = Field(default_factory=list)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_activity: datetime = Field(default_factory=datetime.utcnow)
    total_messages: int = Field(default=0)
    
    class Settings:
        name = "chat_sessions"
        indexes = [
            "user_id",
            [("user_id", 1), ("last_activity", -1)]
        ]

# Request/Response models
class ChatMessageRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    conversation_history: Optional[List[Dict[str, Any]]] = None 

    class Config:
        schema_extra = {
            "example": {
                "message": "Generate a pitch for our new product",
                "session_id": "optional_session_id",
                "conversation_history": [
                    {
                        "role": "user",
                        "content": "Hi",
                        "timestamp": "2025-09-22T13:00:00Z"
                    },
                    {
                        "role": "assistant", 
                        "content": "Hello! How can I help you today?",
                        "timestamp": "2025-09-22T13:00:01Z"
                    }
                ]
            }
        }

class ChatMessageResponse(BaseModel):
    session_id: str
    message: ChatMessage
    actions_executed: List[Dict[str, Any]] = Field(default_factory=list)

class ChatSessionResponse(BaseModel):
    id: str
    session_name: str
    messages: List[ChatMessage]
    is_active: bool
    created_at: datetime
    last_activity: datetime
    total_messages: int


class ChatMessageResponseEnhanced(BaseModel):
    session_id: str
    message: ChatMessage
    actions_executed: List[Dict[str, Any]] = Field(default_factory=list)
    suggestions: List[Dict[str, Any]] = Field(default_factory=list)
    next_steps: List[str] = Field(default_factory=list)
    tips: List[str] = Field(default_factory=list)
    performance_info: Dict[str, Any] = Field(default_factory=dict)

"""


# app/models/chatbot.py
from beanie import Document
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class ChatMessageResponse(BaseModel):
    """Individual chat message model"""
    role: str = Field(..., description="Role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")


class ChatMessageRequest(BaseModel):
    """Request model for sending a message"""
    message: str = Field(..., description="User's message")
    session_id: Optional[str] = Field(None, description="Optional session ID to continue conversation")
    conversation_history: Optional[List[Dict[str, str]]] = Field(
        default=None,
        description="Previous conversation messages"
    )


class ChatSession(Document):
    """Chat session document stored in MongoDB"""
    user_id: str = Field(..., description="User ID")
    session_name: str = Field(default="New Chat", description="Session name")
    messages: List[ChatMessageResponse] = Field(default=[], description="Chat messages")
    is_active: bool = Field(default=True, description="Is session active")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_activity: datetime = Field(default_factory=datetime.utcnow)
    total_messages: int = Field(default=0, description="Total message count")

    class Settings:
        name = "chat_sessions"
        indexes = [
            "user_id",
            "is_active",
            "last_activity"
        ]


class ChatSessionResponse(BaseModel):
    """Response model for chat session"""
    id: str
    session_name: str
    messages: List[ChatMessageResponse]
    is_active: bool
    created_at: datetime
    last_activity: datetime
    total_messages: int


class ChatMessageResponseEnhanced(BaseModel):
    """Enhanced response with additional context"""
    session_id: str
    message: ChatMessageResponse
    actions_executed: List[Dict[str, Any]] = []
    suggestions: List[Dict[str, Any]] = []
    next_steps: List[Dict[str, Any]] = []
    performance_info: Optional[Dict[str, Any]] = None
