from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime
from enum import Enum

class ImportStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class ImportFileType(str, Enum):
    CSV = "csv"
    EXCEL = "excel"
    JSON = "json"

class JournalistImportRow(BaseModel):
    """Flexible journalist data that can handle any combination of fields"""
    
    # Required fields (we'll try to extract these)
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    
    # Optional standard fields
    publication: Optional[str] = None
    category: Optional[str] = None
    topics: Optional[List[str]] = None
    country: Optional[str] = None
    timezone: Optional[str] = None
    
    # Contact info
    phone: Optional[str] = None
    website: Optional[str] = None
    twitter: Optional[str] = None
    linkedin: Optional[str] = None
    
    # Additional flexible fields
    extra_data: Dict[str, Any] = {}  # Store any unmapped fields
    
    # Import metadata
    row_number: int
    validation_errors: List[str] = []
    import_status: Literal["valid", "invalid", "duplicate"] = "valid"
    
    @validator('email', pre=True)
    def validate_email(cls, v):
        if v and isinstance(v, str):
            v = v.strip().lower()
        return v
    
    @validator('name', pre=True)
    def validate_name(cls, v):
        if v and isinstance(v, str):
            v = v.strip().title()
        return v
    
    def is_valid_for_import(self) -> bool:
        """Check if row has minimum required data"""
        return bool(self.name and self.email)

class ImportPreview(BaseModel):
    """Preview of import data before actual import"""
    total_rows: int
    valid_rows: int
    invalid_rows: int
    duplicate_rows: int
    field_mapping: Dict[str, str]  # original_column -> our_field
    sample_data: List[JournalistImportRow]
    detected_columns: List[str]
    suggested_mapping: Dict[str, str]

class ImportResult(BaseModel):
    """Results after importing data"""
    total_processed: int
    successfully_imported: int
    failed_imports: int
    duplicates_skipped: int
    errors: List[Dict[str, Any]]
    imported_journalist_ids: List[str]

class ImportJob(BaseModel):
    """Import job tracking"""
    id: str
    user_id: str
    filename: str
    file_type: ImportFileType
    status: ImportStatus
    total_rows: int
    processed_rows: int
    success_count: int
    error_count: int
    duplicate_count: int
    field_mapping: Dict[str, str]
    errors: List[Dict[str, Any]] = []
    created_at: datetime
    completed_at: Optional[datetime] = None
    
class FieldMappingRequest(BaseModel):
    """User's field mapping choices"""
    mapping: Dict[str, str] = Field(
        ..., 
        description="Map CSV columns to journalist fields",
        example={
            "Full Name": "name",
            "Email Address": "email", 
            "Media Outlet": "publication",
            "Beat": "category",
            "Location": "country"
        }
    )
    skip_duplicates: bool = True
    update_existing: bool = False
