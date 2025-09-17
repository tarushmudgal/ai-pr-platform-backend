from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Optional
from app.models.pitch import (
    PitchCreate, 
    PitchUpdate, 
    PitchResponse,
    PitchSearch,
    AnnouncementType,
    PitchStatus
)
from app.models.user import User
from app.services.pitch_service import PitchService
from app.utils.dependencies import get_current_active_user

router = APIRouter()

@router.post("/", response_model=PitchResponse, status_code=status.HTTP_201_CREATED)
async def create_pitch(
    pitch_data: PitchCreate,
    current_user: User = Depends(get_current_active_user)
):
    """Generate a new AI-powered pitch (costs 1 credit)"""
    return await PitchService.create_pitch(pitch_data, current_user)

@router.get("/", response_model=dict)
async def search_pitches(
    query: Optional[str] = Query(None, description="Search headline or company name"),
    industry: Optional[str] = Query(None, description="Filter by industry"),
    announcement_type: Optional[AnnouncementType] = Query(None, description="Filter by announcement type"),
    status: Optional[PitchStatus] = Query(None, description="Filter by status"),
    limit: int = Query(20, ge=1, le=100, description="Number of results"),
    skip: int = Query(0, ge=0, description="Number of results to skip"),
    current_user: User = Depends(get_current_active_user)
):
    """Search and filter pitches"""
    
    search_params = PitchSearch(
        query=query,
        industry=industry,
        announcement_type=announcement_type,
        status=status,
        limit=limit,
        skip=skip
    )
    
    return await PitchService.search_pitches(search_params, current_user)

@router.get("/{pitch_id}", response_model=PitchResponse)
async def get_pitch(
    pitch_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Get pitch by ID"""
    return await PitchService.get_pitch(pitch_id, current_user)

@router.put("/{pitch_id}", response_model=PitchResponse)
async def update_pitch(
    pitch_id: str,
    update_data: PitchUpdate,
    current_user: User = Depends(get_current_active_user)
):
    """Update pitch details"""
    return await PitchService.update_pitch(pitch_id, update_data, current_user)

@router.delete("/{pitch_id}")
async def delete_pitch(
    pitch_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Delete pitch"""
    return await PitchService.delete_pitch(pitch_id, current_user)

@router.post("/{pitch_id}/regenerate", response_model=PitchResponse)
async def regenerate_pitch(
    pitch_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Regenerate AI content for existing pitch (costs 1 credit)"""
    return await PitchService.regenerate_pitch_content(pitch_id, current_user)

@router.get("/stats/overview")
async def get_pitch_stats(
    current_user: User = Depends(get_current_active_user)
):
    """Get pitch generation statistics for current user"""
    from app.models.pitch import Pitch
    
    total_pitches = await Pitch.find(
        Pitch.user_id == str(current_user.id)
    ).count()
    
    draft_pitches = await Pitch.find(
        Pitch.user_id == str(current_user.id),
        Pitch.status == "draft"
    ).count()
    
    sent_pitches = await Pitch.find(
        Pitch.user_id == str(current_user.id),
        Pitch.status == "sent"
    ).count()
    
    # Get all pitches for performance calculations
    all_pitches = await Pitch.find(
        Pitch.user_id == str(current_user.id)
    ).to_list()
    
    total_emails_sent = sum([p.performance.emails_sent for p in all_pitches])
    total_responses = sum([p.performance.responses_received for p in all_pitches])
    total_articles = sum([p.performance.articles_published for p in all_pitches])
    
    return {
        "total_pitches": total_pitches,
        "draft_pitches": draft_pitches,
        "sent_pitches": sent_pitches,
        "performance": {
            "total_emails_sent": total_emails_sent,
            "total_responses": total_responses,
            "total_articles": total_articles,
            "response_rate": round(total_responses / total_emails_sent, 3) if total_emails_sent > 0 else 0
        },
        "credits_remaining": current_user.credits_remaining
    }
