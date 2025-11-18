from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Optional
from app.models.pitch import (
    PitchCreate, 
    PitchUpdate, 
    PitchResponse,
    PitchSearch,
    AnnouncementType,
    PitchStatus, 
    RewriteRequest
)
from app.models.user import User
from app.services.pitch_service import PitchService
from app.utils.dependencies import get_current_active_user
from app.services.rewriting_service import rewriting_service

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



from beanie import PydanticObjectId
from app.models.pitch import Pitch

def clean_press_release_content(content: str) -> str:
    """Remove subject lines and headers from press release content"""
    
    lines = content.split('\n')
    cleaned_lines = []
    skip_next_empty = False
    
    for i, line in enumerate(lines):
        line_stripped = line.strip()
        
        # Skip lines that look like subject lines or headers
        skip_patterns = [
            'Subject:',
            'HEADLINE:',
            'SUBHEADLINE:', 
            '**HEADLINE:**',
            '**SUBHEADLINE:**',
            'Subject: ',
        ]
        
        # Check if this line should be skipped
        should_skip = False
        for pattern in skip_patterns:
            if line_stripped.startswith(pattern):
                should_skip = True
                skip_next_empty = True  # Skip the next empty line too
                break
        
        if should_skip:
            continue
            
        # Skip empty lines right after headers
        if skip_next_empty and not line_stripped:
            skip_next_empty = False
            continue
        
        skip_next_empty = False
        
        # Skip empty lines at the very beginning
        if not cleaned_lines and not line_stripped:
            continue
            
        cleaned_lines.append(line)
    
    # Join back and clean up markdown
    cleaned_content = '\n'.join(cleaned_lines)
    
    # Remove markdown formatting but keep line breaks
    import re
    cleaned_content = re.sub(r'\*\*(.*?)\*\*', r'\1', cleaned_content)
    cleaned_content = re.sub(r'\*(.*?)\*', r'\1', cleaned_content)
    
    return cleaned_content.strip()


def clean_email_content(content: str) -> str:
    """Remove subject lines from email content"""
    
    lines = content.split('\n')
    cleaned_lines = []
    
    for i, line in enumerate(lines):
        line_stripped = line.strip()
        
        # Skip subject line patterns
        if (line_stripped.startswith('Subject:') or 
            line_stripped.startswith('Subject ') or
            (i == 0 and '🚀' in line and 'Subject' in line)):  # Handle emoji subjects
            continue
            
        # Skip empty lines right after subject removal
        if not cleaned_lines and not line_stripped:
            continue
            
        cleaned_lines.append(line)
    
    return '\n'.join(cleaned_lines).strip()


# In your pitch router, add this new endpoint
@router.post("/{pitch_id}/rewrite")
async def rewrite_pitch_content(
    pitch_id: str,
    request: RewriteRequest,
    current_user: User = Depends(get_current_active_user)
):
    try:
        # Get the pitch
        pitch_obj_id = PydanticObjectId(pitch_id)
        pitch = await Pitch.find_one(
            Pitch.id == pitch_obj_id,
            Pitch.user_id == str(current_user.id)
        )
        
        if not pitch:
            raise HTTPException(status_code=404, detail="Pitch not found")
        
        # Extract content based on type with proper cleaning
        if request.content_type == "email":
            raw_content = pitch.content.email_pitch.body
            # Clean email content to remove subject lines
            original_content = clean_email_content(raw_content)
            print(f"🔍 DEBUG: Cleaned email content: {len(original_content)} chars")
            
        elif request.content_type == "press_release":
            raw_content = str(pitch.content.press_release.body)
            # Clean press release content to remove headers
            original_content = clean_press_release_content(raw_content)
            print(f"🔍 DEBUG: Cleaned press release content: {len(original_content)} chars")
        else:
            raise HTTPException(status_code=400, detail="Invalid content_type")
        
        # Rewrite the cleaned content
        rewritten_content = await rewriting_service.rewrite_content(
            content=original_content,
            content_type=request.content_type,
            mood=request.mood,
            length=request.length,
            style=request.style
        )
        
        # Update pitch with cleaned rewritten content
        if request.content_type == "email":
            pitch.content.email_pitch.body = rewritten_content
        elif request.content_type == "press_release":
            pitch.content.press_release.body = rewritten_content
            
        await pitch.save()
        
        return {
            "pitch_id": str(pitch.id),
            "content_type": request.content_type,
            "original_content": original_content,
            "rewritten_content": rewritten_content,
            "settings": {
                "mood": request.mood,
                "length": request.length,
                "style": request.style
            }
        }
        
    except Exception as e:
        print(f"Error rewriting pitch content: {e}")
        raise HTTPException(status_code=400, detail=str(e))


    

@router.get("/{pitch_id}/debug-structure")
async def debug_pitch_structure(
    pitch_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Debug: See pitch structure"""
    
    try:
        pitch_obj_id = PydanticObjectId(pitch_id)
        pitch = await Pitch.find_one(
            Pitch.id == pitch_obj_id,
            Pitch.user_id == str(current_user.id)
        )
        
        if not pitch:
            raise HTTPException(status_code=404, detail="Pitch not found")
        
        # Convert to dict to see structure
        pitch_dict = pitch.dict()
        
        return {
            "pitch_structure": pitch_dict,
            "content_keys": list(pitch_dict.get('content', {}).keys()) if 'content' in pitch_dict else [],
            "press_release_type": str(type(pitch.content.press_release)) if hasattr(pitch.content, 'press_release') else "Not found"
        }
        
    except Exception as e:
        return {"error": str(e)}
