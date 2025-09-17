from typing import List, Optional, Dict, Any
from beanie import PydanticObjectId
from app.models.journalist import (
    Journalist, 
    JournalistCreate, 
    JournalistUpdate, 
    JournalistSearch,
    JournalistResponse
)
from app.models.user import User
from fastapi import HTTPException, status
from datetime import datetime
import re

class JournalistService:
    
    @staticmethod
    async def create_journalist(
        journalist_data: JournalistCreate, 
        current_user: User
    ) -> JournalistResponse:
        """Create a new journalist"""
        
        # Check if journalist already exists for this user
        existing = await Journalist.find_one(
            Journalist.email == journalist_data.email,
            Journalist.added_by_user_id == str(current_user.id)
        )
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Journalist with this email already exists in your database"
            )
        
        # Create new journalist
        journalist = Journalist(
            added_by_user_id=str(current_user.id),
            name=journalist_data.name,
            email=journalist_data.email,
            publication=journalist_data.publication,
            category=journalist_data.category,
            topics=journalist_data.topics,
            country=journalist_data.country,
            timezone=journalist_data.timezone,
            notes=journalist_data.notes,
            contact_info=journalist_data.contact_info
        )
        
        await journalist.create()
        
        return JournalistResponse(
            id=str(journalist.id),
            name=journalist.name,
            email=journalist.email,
            publication=journalist.publication,
            category=journalist.category,
            topics=journalist.topics,
            country=journalist.country,
            timezone=journalist.timezone,
            stats=journalist.stats,
            contact_info=journalist.contact_info,
            source=journalist.source,
            verified=journalist.verified,
            notes=journalist.notes,
            created_at=journalist.created_at,
            updated_at=journalist.updated_at,
            status=journalist.status
        )
    
    @staticmethod
    async def get_journalist(
        journalist_id: str, 
        current_user: User
    ) -> JournalistResponse:
        """Get journalist by ID"""
        
        try:
            journalist_obj_id = PydanticObjectId(journalist_id)
        except:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid journalist ID"
            )
        
        journalist = await Journalist.find_one(
            Journalist.id == journalist_obj_id,
            Journalist.added_by_user_id == str(current_user.id)
        )
        
        if not journalist:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Journalist not found"
            )
        
        return JournalistResponse(
            id=str(journalist.id),
            name=journalist.name,
            email=journalist.email,
            publication=journalist.publication,
            category=journalist.category,
            topics=journalist.topics,
            country=journalist.country,
            timezone=journalist.timezone,
            stats=journalist.stats,
            contact_info=journalist.contact_info,
            source=journalist.source,
            verified=journalist.verified,
            notes=journalist.notes,
            created_at=journalist.created_at,
            updated_at=journalist.updated_at,
            status=journalist.status
        )
    
    @staticmethod
    async def search_journalists(
        search_params: JournalistSearch,
        current_user: User
    ) -> Dict[str, Any]:
        """Search journalists with filters"""
        
        # Build query
        query_conditions = [Journalist.added_by_user_id == str(current_user.id)]
        
        # Add search filters
        if search_params.category:
            query_conditions.append(Journalist.category == search_params.category)
        
        if search_params.country:
            query_conditions.append(Journalist.country == search_params.country)
        
        if search_params.publication:
            # Case-insensitive partial match
            query_conditions.append(
                Journalist.publication.regex(re.escape(search_params.publication), "i")
            )
        
        if search_params.status:
            query_conditions.append(Journalist.status == search_params.status)
        
        if search_params.verified_only:
            query_conditions.append(Journalist.verified == True)
        
        # Text search on name and publication
        if search_params.query:
            query_conditions.append(
                {"$or": [
                    {"name": {"$regex": re.escape(search_params.query), "$options": "i"}},
                    {"publication": {"$regex": re.escape(search_params.query), "$options": "i"}}
                ]}
            )
        
        # Execute search
        journalists = await Journalist.find(
            *query_conditions
        ).skip(search_params.skip).limit(search_params.limit).to_list()
        
        # Get total count
        total_count = await Journalist.find(*query_conditions).count()
        
        # Convert to response format
        journalist_responses = [
            JournalistResponse(
                id=str(j.id),
                name=j.name,
                email=j.email,
                publication=j.publication,
                category=j.category,
                topics=j.topics,
                country=j.country,
                timezone=j.timezone,
                stats=j.stats,
                contact_info=j.contact_info,
                source=j.source,
                verified=j.verified,
                notes=j.notes,
                created_at=j.created_at,
                updated_at=j.updated_at,
                status=j.status
            ) for j in journalists
        ]
        
        return {
            "journalists": journalist_responses,
            "total": total_count,
            "page": search_params.skip // search_params.limit + 1,
            "pages": (total_count + search_params.limit - 1) // search_params.limit,
            "has_next": search_params.skip + search_params.limit < total_count
        }
    
    @staticmethod
    async def update_journalist(
        journalist_id: str,
        update_data: JournalistUpdate,
        current_user: User
    ) -> JournalistResponse:
        """Update journalist"""
        
        try:
            journalist_obj_id = PydanticObjectId(journalist_id)
        except:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid journalist ID"
            )
        
        journalist = await Journalist.find_one(
            Journalist.id == journalist_obj_id,
            Journalist.added_by_user_id == str(current_user.id)
        )
        
        if not journalist:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Journalist not found"
            )
        
        # Update fields
        update_dict = update_data.model_dump(exclude_unset=True)
        
        for field, value in update_dict.items():
            setattr(journalist, field, value)
        
        journalist.updated_at = datetime.utcnow()
        await journalist.save()
        
        return JournalistResponse(
            id=str(journalist.id),
            name=journalist.name,
            email=journalist.email,
            publication=journalist.publication,
            category=journalist.category,
            topics=journalist.topics,
            country=journalist.country,
            timezone=journalist.timezone,
            stats=journalist.stats,
            contact_info=journalist.contact_info,
            source=journalist.source,
            verified=journalist.verified,
            notes=journalist.notes,
            created_at=journalist.created_at,
            updated_at=journalist.updated_at,
            status=journalist.status
        )
    
    @staticmethod
    async def delete_journalist(
        journalist_id: str,
        current_user: User
    ) -> Dict[str, str]:
        """Delete journalist"""
        
        try:
            journalist_obj_id = PydanticObjectId(journalist_id)
        except:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid journalist ID"
            )
        
        journalist = await Journalist.find_one(
            Journalist.id == journalist_obj_id,
            Journalist.added_by_user_id == str(current_user.id)
        )
        
        if not journalist:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Journalist not found"
            )
        
        await journalist.delete()
        
        return {"message": "Journalist deleted successfully"}
