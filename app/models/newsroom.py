
from beanie import Document, Indexed
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import uuid4
import uuid

class MediaAsset(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: str = Field(..., description="Type of media (image, video, document)")
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=500)
    file_url: str = Field(..., description="URL to the media file")
    file_size: int = Field(..., description="File size in bytes")
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)

class CompanyInfo(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    website: Optional[str] = Field(None, max_length=200)
    email: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=50)
    address: Optional[str] = Field(None, max_length=300)
    logo_url: Optional[str] = Field(None, description="URL to company logo")
    founded_year: Optional[int] = Field(None, ge=1800, le=2030)
    industry: Optional[str] = Field(None, max_length=100)
    employee_count: Optional[str] = Field(None, max_length=50)

class NewsroomCreate(BaseModel):
    company_info: CompanyInfo
    brand_colors: Optional[Dict[str, str]] = Field(None, description="Brand color scheme")
    is_public: Optional[bool] = Field(False, description="Whether newsroom is publicly accessible")

class NewsroomUpdate(BaseModel):
    company_info: Optional[CompanyInfo] = None
    brand_colors: Optional[Dict[str, str]] = None
    is_public: Optional[bool] = None

class Newsroom(Document):
    owner_id: str = Field(..., description="User ID who owns this newsroom")
    company_info: CompanyInfo
    press_releases: List[Dict[str, Any]] = Field(default_factory=list)
    media_assets: List[MediaAsset] = Field(default_factory=list)
    brand_colors: Dict[str, str] = Field(default={
        "primary": "#1f2937",
        "secondary": "#6b7280", 
        "accent": "#3b82f6"
    })
    is_public: bool = Field(default=False)
    views: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        name = "newsrooms"
