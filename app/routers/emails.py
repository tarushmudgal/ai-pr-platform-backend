from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional
from pydantic import BaseModel, Field
from beanie import PydanticObjectId
from app.models.user import User
from app.models.pitch import Pitch
from app.models.journalist import Journalist
from app.services.email_service import email_service
from app.utils.dependencies import get_current_active_user

router = APIRouter()

# Pydantic models for email operations
class SendPitchRequest(BaseModel):
    pitch_id: str
    journalist_ids: List[str] = Field(..., min_items=1, max_items=50)  # Max 50 recipients
    custom_subject: Optional[str] = Field(None, max_length=200)
    custom_message: Optional[str] = Field(None, max_length=2000)

class SendPitchResponse(BaseModel):
    message: str
    sent: List[dict]
    failed: List[dict]
    total_sent: int
    total_failed: int

@router.post("/send-pitch", response_model=SendPitchResponse)
async def send_pitch_to_journalists(
    request: SendPitchRequest,
    current_user: User = Depends(get_current_active_user)
):
    """Send a pitch to selected journalists via email"""
    
    # Get and validate pitch
    try:
        pitch_obj_id = PydanticObjectId(request.pitch_id)
    except:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid pitch ID"
        )
    
    pitch = await Pitch.find_one(
        Pitch.id == pitch_obj_id,
        Pitch.user_id == str(current_user.id)
    )
    
    if not pitch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pitch not found"
        )
    
    # Validate journalist IDs belong to user
    valid_journalist_ids = []
    for journalist_id in request.journalist_ids:
        try:
            journalist_obj_id = PydanticObjectId(journalist_id)
            journalist = await Journalist.find_one(
                Journalist.id == journalist_obj_id,
                Journalist.added_by_user_id == str(current_user.id)
            )
            if journalist:
                valid_journalist_ids.append(str(journalist_id))
        except:
            continue
    
    if not valid_journalist_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid journalist IDs provided"
        )
    
    # Send emails
    results = await email_service.send_pitch_to_journalists(
        pitch=pitch,
        journalist_ids=valid_journalist_ids,
        current_user=current_user,
        custom_subject=request.custom_subject,
        custom_message=request.custom_message
    )
    
    return SendPitchResponse(
        message=f"Email sending completed. {results['total_sent']} sent, {results['total_failed']} failed.",
        sent=results["sent"],
        failed=results["failed"],
        total_sent=results["total_sent"],
        total_failed=results["total_failed"]
    )

@router.get("/interactions")
async def get_email_interactions(
    limit: int = Query(20, ge=1, le=100, description="Number of results"),
    skip: int = Query(0, ge=0, description="Number of results to skip"),
    current_user: User = Depends(get_current_active_user)
):
    """Get user's email interactions and tracking"""
    
    return await email_service.get_user_interactions(
        user_id=str(current_user.id),
        limit=limit,
        skip=skip
    )

@router.get("/stats")
async def get_email_stats(
    current_user: User = Depends(get_current_active_user)
):
    """Get email sending statistics"""
    
    from app.models.interaction import Interaction, InteractionType, EmailStatus
    
    # Get interaction counts using correct Beanie syntax
    total_emails = await Interaction.find(
        Interaction.user_id == str(current_user.id),
        Interaction.type == InteractionType.EMAIL_SENT
    ).count()
    
    # Fix: Use == for individual status checks instead of .in_()
    opened_emails_count = 0
    replied_emails_count = 0
    
    # Get all email interactions for this user
    all_interactions = await Interaction.find(
        Interaction.user_id == str(current_user.id),
        Interaction.type == InteractionType.EMAIL_SENT
    ).to_list()
    
    # Count opened and replied emails manually
    for interaction in all_interactions:
        if interaction.status in [EmailStatus.OPENED, EmailStatus.CLICKED, EmailStatus.REPLIED]:
            opened_emails_count += 1
        if interaction.response_received:
            replied_emails_count += 1
    
    # Calculate rates
    open_rate = round(opened_emails_count / total_emails, 3) if total_emails > 0 else 0
    response_rate = round(replied_emails_count / total_emails, 3) if total_emails > 0 else 0
    
    return {
        "total_emails_sent": total_emails,
        "emails_opened": opened_emails_count,
        "emails_replied": replied_emails_count,
        "open_rate": open_rate,
        "response_rate": response_rate,
        "credits_remaining": current_user.credits_remaining
    }

# Test email configuration
@router.post("/test-config")
async def test_email_configuration(
    current_user: User = Depends(get_current_active_user)
):
    """Test email configuration (admin only for security)"""
    
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    try:
        # Test SMTP connection
        import aiosmtplib
        from app.config import settings
        
        async with aiosmtplib.SMTP(
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            start_tls=True
        ) as server:
            await server.login(settings.smtp_user, settings.smtp_password)
        
        return {
            "status": "success",
            "message": "Email configuration is working",
            "smtp_host": settings.smtp_host,
            "smtp_port": settings.smtp_port,
            "smtp_user": settings.smtp_user
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Email configuration failed: {str(e)}",
            "smtp_host": settings.smtp_host,
            "smtp_port": settings.smtp_port
        }
