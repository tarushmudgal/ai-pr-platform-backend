from typing import Dict
from app.models.user import User
from app.models.import_models import ImportPreview, ImportResult, FieldMappingRequest
from app.services.import_service import import_service
from app.utils.dependencies import get_current_active_user
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from typing import Dict
import json

router = APIRouter()

@router.post("/preview", response_model=ImportPreview)
async def preview_journalist_import(
    file: UploadFile = File(..., description="CSV, Excel, or JSON file with journalist data"),
    current_user: User = Depends(get_current_active_user)
):
    """
    Preview import file and get suggested field mappings
    
    Supported formats:
    - CSV (.csv)
    - Excel (.xlsx, .xls)  
    - JSON (.json) - must be array of objects
    
    The system will automatically detect columns and suggest mappings to our journalist fields.
    """
    
    # Validate file size (max 10MB)
    max_size = 10 * 1024 * 1024  # 10MB
    file_content = await file.read()
    
    if len(file_content) > max_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File too large. Maximum size is 10MB."
        )
    
    # Reset file position
    await file.seek(0)
    
    return await import_service.preview_import_file(file, current_user)



@router.post("/execute", response_model=ImportResult)
async def execute_journalist_import(
    file: UploadFile = File(..., description="File to import (CSV, Excel, JSON)"),
    skip_duplicates: bool = Form(True, description="Skip duplicate journalists"),
    update_existing: bool = Form(False, description="Update existing journalists"),
    current_user: User = Depends(get_current_active_user)
):
    """
    Execute journalist import with automatic field mapping
    
    The system will automatically detect the best field mappings based on column names.
    Use the preview endpoint first to see what mappings will be applied.
    """
    
    # Get auto-detected mappings
    preview = await import_service.preview_import_file(file, current_user)
    
    # Reset file position after preview
    await file.seek(0)
    
    # Execute import with auto-detected mapping
    return await import_service.import_journalists(
        file=file,
        field_mapping=preview.suggested_mapping,
        current_user=current_user,
        skip_duplicates=skip_duplicates,
        update_existing=update_existing
    )



@router.get("/supported-fields")
async def get_supported_fields():
    """Get list of supported journalist fields for mapping"""
    
    return {
        "required_fields": {
            "name": "Journalist's full name (required)",
            "email": "Email address (required)"
        },
        "optional_fields": {
            "publication": "Media outlet or publication name",
            "category": "Journalism category/beat (technology, business, healthcare, etc.)",
            "topics": "Comma-separated list of topics covered",
            "country": "Country/location",
            "timezone": "Time zone (e.g., PST, UTC)",
            "phone": "Phone number",
            "website": "Personal or professional website",
            "twitter": "Twitter handle",
            "linkedin": "LinkedIn profile URL"
        },
        "supported_categories": [
            "technology", "business", "healthcare", "finance", 
            "lifestyle", "entertainment", "sports", "other"
        ],
        "notes": [
            "Any unmapped columns will be stored as additional data",
            "Duplicate detection is based on email addresses",
            "Categories are automatically mapped to supported values",
            "Topics can be comma, semicolon, or pipe separated"
        ]
    }

@router.get("/template")
async def download_import_template():
    """Get a sample CSV template for journalist imports"""
    
    template_data = """name,email,publication,category,topics,country,phone,website,twitter,linkedin,notes
John Smith,john.smith@techcrunch.com,TechCrunch,technology,"AI,startups,automation",United States,+1-555-0123,https://johnsmith.com,@johnsmith,https://linkedin.com/in/johnsmith,Covers enterprise AI
Sarah Johnson,sarah@forbes.com,Forbes,business,"finance,leadership,strategy",United States,+1-555-0124,,@sarahforbes,,Expert in business strategy
Mike Chen,mike.chen@reuters.com,Reuters,finance,"cryptocurrency,fintech,banking",United Kingdom,+44-123-456789,,,https://linkedin.com/in/mikechen,Specializes in crypto coverage"""
    
    from fastapi.responses import Response
    
    return Response(
        content=template_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=journalist_import_template.csv"}
    )
