from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Optional
from app.models.journalist import (
    JournalistCreate, 
    JournalistUpdate, 
    JournalistResponse,
    JournalistSearch,
    JournalistCategory,
    JournalistStatus
)
from app.models.user import User
from app.services.journalist_service import JournalistService
from app.utils.dependencies import get_current_active_user

router = APIRouter()

@router.post("/", response_model=JournalistResponse, status_code=status.HTTP_201_CREATED)
async def create_journalist(
    journalist_data: JournalistCreate,
    current_user: User = Depends(get_current_active_user)
):
    """Create a new journalist"""
    return await JournalistService.create_journalist(journalist_data, current_user)

@router.get("/", response_model=dict)
async def search_journalists(
    query: Optional[str] = Query(None, description="Search name or publication"),
    category: Optional[JournalistCategory] = Query(None, description="Filter by category"),
    country: Optional[str] = Query(None, description="Filter by country"),
    publication: Optional[str] = Query(None, description="Filter by publication"),
    status: Optional[JournalistStatus] = Query(None, description="Filter by status"),
    verified_only: bool = Query(False, description="Show only verified journalists"),
    limit: int = Query(20, ge=1, le=100, description="Number of results"),
    skip: int = Query(0, ge=0, description="Number of results to skip"),
    current_user: User = Depends(get_current_active_user)
):
    """Search and filter journalists"""
    
    search_params = JournalistSearch(
        query=query,
        category=category,
        country=country,
        publication=publication,
        status=status,
        verified_only=verified_only,
        limit=limit,
        skip=skip
    )
    
    return await JournalistService.search_journalists(search_params, current_user)

@router.get("/{journalist_id}", response_model=JournalistResponse)
async def get_journalist(
    journalist_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Get journalist by ID"""
    return await JournalistService.get_journalist(journalist_id, current_user)

@router.put("/{journalist_id}", response_model=JournalistResponse)
async def update_journalist(
    journalist_id: str,
    update_data: JournalistUpdate,
    current_user: User = Depends(get_current_active_user)
):
    """Update journalist"""
    return await JournalistService.update_journalist(journalist_id, update_data, current_user)

@router.delete("/{journalist_id}")
async def delete_journalist(
    journalist_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Delete journalist"""
    return await JournalistService.delete_journalist(journalist_id, current_user)

# Quick stats endpoint
@router.get("/stats/overview")
async def get_journalist_stats(
    current_user: User = Depends(get_current_active_user)
):
    """Get journalist database statistics for current user"""
    from app.models.journalist import Journalist
    from collections import Counter
    
    # Get basic counts
    total_journalists = await Journalist.find(
        Journalist.added_by_user_id == str(current_user.id)
    ).count()
    
    active_journalists = await Journalist.find(
        Journalist.added_by_user_id == str(current_user.id),
        Journalist.status == "active"
    ).count()
    
    verified_journalists = await Journalist.find(
        Journalist.added_by_user_id == str(current_user.id),
        Journalist.verified == True
    ).count()
    
    # Get all journalists to calculate category stats
    all_journalists = await Journalist.find(
        Journalist.added_by_user_id == str(current_user.id)
    ).to_list()
    
    # Calculate category distribution
    category_counter = Counter([j.category for j in all_journalists])
    top_categories = [
        {"category": category, "count": count} 
        for category, count in category_counter.most_common(5)
    ]
    
    # Calculate country distribution
    country_counter = Counter([j.country for j in all_journalists])
    top_countries = [
        {"country": country, "count": count}
        for country, count in country_counter.most_common(5)
    ]
    
    return {
        "total_journalists": total_journalists,
        "active_journalists": active_journalists,
        "verified_journalists": verified_journalists,
        "verification_rate": round(verified_journalists / total_journalists, 3) if total_journalists > 0 else 0,
        "top_categories": top_categories,
        "top_countries": top_countries,
        "response_stats": {
            "total_emails_sent": sum([j.stats.emails_received for j in all_journalists]),
            "total_responses": sum([j.stats.responses_sent for j in all_journalists]),
            "total_articles": sum([j.stats.articles_published for j in all_journalists]),
            "average_response_rate": round(
                sum([j.stats.response_rate for j in all_journalists]) / len(all_journalists), 3
            ) if all_journalists else 0
        }
    }