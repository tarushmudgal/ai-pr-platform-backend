from typing import List, Optional, Dict, Any
from beanie import PydanticObjectId
from app.models.pitch import (
    Pitch, 
    PitchCreate, 
    PitchUpdate, 
    PitchSearch,
    PitchResponse
)
from app.models.user import User
from app.services.ai_service import ai_service
from fastapi import HTTPException, status
from datetime import datetime
import re

class PitchService:
    
    @staticmethod
    async def create_pitch(
        pitch_data: PitchCreate, 
        current_user: User
    ) -> PitchResponse:
        """Create a new AI-generated pitch"""
        
        # Check if user has enough credits
        if not current_user.can_use_credits(1):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient credits. Please upgrade your plan."
            )
        
        try:
            # Generate AI content
            generated_content, generation_metadata = await ai_service.generate_pitch_content(pitch_data)
            
            # Create pitch document
            pitch = Pitch(
                user_id=str(current_user.id),
                headline=pitch_data.headline,
                company_name=pitch_data.company_name,
                key_points=pitch_data.key_points,
                industry=pitch_data.industry,
                announcement_type=pitch_data.announcement_type,
                content=generated_content,
                generation_info=generation_metadata
            )
            
            await pitch.create()
            
            # Deduct credit from user
            current_user.use_credits(1)
            await current_user.save()
            
            return PitchResponse(
                id=str(pitch.id),
                headline=pitch.headline,
                company_name=pitch.company_name,
                key_points=pitch.key_points,
                industry=pitch.industry,
                announcement_type=pitch.announcement_type,
                content=pitch.content,
                generation_info=pitch.generation_info,
                performance=pitch.performance,
                status=pitch.status,
                created_at=pitch.created_at,
                updated_at=pitch.updated_at
            )
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate pitch: {str(e)}"
            )
    
    @staticmethod
    async def get_pitch(
        pitch_id: str, 
        current_user: User
    ) -> PitchResponse:
        """Get pitch by ID"""
        
        try:
            pitch_obj_id = PydanticObjectId(pitch_id)
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
        
        return PitchResponse(
            id=str(pitch.id),
            headline=pitch.headline,
            company_name=pitch.company_name,
            key_points=pitch.key_points,
            industry=pitch.industry,
            announcement_type=pitch.announcement_type,
            content=pitch.content,
            generation_info=pitch.generation_info,
            performance=pitch.performance,
            status=pitch.status,
            created_at=pitch.created_at,
            updated_at=pitch.updated_at
        )
    
    @staticmethod
    async def search_pitches(
        search_params: PitchSearch,
        current_user: User
    ) -> Dict[str, Any]:
        """Search pitches with filters"""
        
        # Build query
        query_conditions = [Pitch.user_id == str(current_user.id)]
        
        # Add search filters
        if search_params.industry:
            query_conditions.append(Pitch.industry == search_params.industry)
        
        if search_params.announcement_type:
            query_conditions.append(Pitch.announcement_type == search_params.announcement_type)
        
        if search_params.status:
            query_conditions.append(Pitch.status == search_params.status)
        
        # Text search on headline and company name
        if search_params.query:
            query_conditions.append(
                {"$or": [
                    {"headline": {"$regex": re.escape(search_params.query), "$options": "i"}},
                    {"company_name": {"$regex": re.escape(search_params.query), "$options": "i"}}
                ]}
            )
        
        # Execute search with sorting (newest first)
        pitches = await Pitch.find(
            *query_conditions
        ).sort(-Pitch.created_at).skip(search_params.skip).limit(search_params.limit).to_list()
        
        # Get total count
        total_count = await Pitch.find(*query_conditions).count()
        
        # Convert to response format
        pitch_responses = [
            PitchResponse(
                id=str(p.id),
                headline=p.headline,
                company_name=p.company_name,
                key_points=p.key_points,
                industry=p.industry,
                announcement_type=p.announcement_type,
                content=p.content,
                generation_info=p.generation_info,
                performance=p.performance,
                status=p.status,
                created_at=p.created_at,
                updated_at=p.updated_at
            ) for p in pitches
        ]
        
        return {
            "pitches": pitch_responses,
            "total": total_count,
            "page": search_params.skip // search_params.limit + 1,
            "pages": (total_count + search_params.limit - 1) // search_params.limit,
            "has_next": search_params.skip + search_params.limit < total_count
        }
    
    @staticmethod
    async def update_pitch(
        pitch_id: str,
        update_data: PitchUpdate,
        current_user: User
    ) -> PitchResponse:
        """Update pitch"""
        
        try:
            pitch_obj_id = PydanticObjectId(pitch_id)
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
        
        # Update fields
        update_dict = update_data.model_dump(exclude_unset=True)
        
        for field, value in update_dict.items():
            setattr(pitch, field, value)
        
        pitch.updated_at = datetime.utcnow()
        await pitch.save()
        
        return PitchResponse(
            id=str(pitch.id),
            headline=pitch.headline,
            company_name=pitch.company_name,
            key_points=pitch.key_points,
            industry=pitch.industry,
            announcement_type=pitch.announcement_type,
            content=pitch.content,
            generation_info=pitch.generation_info,
            performance=pitch.performance,
            status=pitch.status,
            created_at=pitch.created_at,
            updated_at=pitch.updated_at
        )
    
    @staticmethod
    async def delete_pitch(
        pitch_id: str,
        current_user: User
    ) -> Dict[str, str]:
        """Delete pitch"""
        
        try:
            pitch_obj_id = PydanticObjectId(pitch_id)
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
        
        await pitch.delete()
        
        return {"message": "Pitch deleted successfully"}
    
    @staticmethod
    async def regenerate_pitch_content(
        pitch_id: str,
        current_user: User
    ) -> PitchResponse:
        """Regenerate AI content for existing pitch"""
        
        # Check credits
        if not current_user.can_use_credits(1):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient credits. Please upgrade your plan."
            )
        
        try:
            pitch_obj_id = PydanticObjectId(pitch_id)
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
        
        try:
            # Create PitchCreate object from existing pitch
            pitch_data = PitchCreate(
                headline=pitch.headline,
                company_name=pitch.company_name,
                key_points=pitch.key_points,
                industry=pitch.industry,
                announcement_type=pitch.announcement_type
            )
            
            # Generate new content
            generated_content, generation_metadata = await ai_service.generate_pitch_content(pitch_data)
            
            # Update pitch with new content
            pitch.content = generated_content
            pitch.generation_info = generation_metadata
            pitch.updated_at = datetime.utcnow()
            
            await pitch.save()
            
            # Deduct credit
            current_user.use_credits(1)
            await current_user.save()
            
            return PitchResponse(
                id=str(pitch.id),
                headline=pitch.headline,
                company_name=pitch.company_name,
                key_points=pitch.key_points,
                industry=pitch.industry,
                announcement_type=pitch.announcement_type,
                content=pitch.content,
                generation_info=pitch.generation_info,
                performance=pitch.performance,
                status=pitch.status,
                created_at=pitch.created_at,
                updated_at=pitch.updated_at
            )
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to regenerate pitch: {str(e)}"
            )
