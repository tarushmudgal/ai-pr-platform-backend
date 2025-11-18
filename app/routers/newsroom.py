# In app/routers/newsroom.py
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from typing import Optional, List
from beanie import PydanticObjectId
from app.models.newsroom import Newsroom, NewsroomCreate, NewsroomUpdate, CompanyInfo, MediaAsset
from app.models.user import User
from app.utils.dependencies import get_current_active_user
import os
import uuid
import aiofiles
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
import boto3

load_dotenv()

router = APIRouter()

S3_BUCKET = os.getenv("S3_BUCKET")
S3_REGION = os.getenv("AWS_REGION")

s3_client = boto3.client(
    "s3",
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name=S3_REGION
)

# Create uploads directory if it doesn't exist
UPLOAD_DIR = Path("uploads/media")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

async def save_uploaded_file(file: UploadFile) -> str:
    """Save uploaded file and return the file URL"""
    
    # Generate unique filename
    file_extension = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    file_path = UPLOAD_DIR / unique_filename
    
    # Save file
    async with aiofiles.open(file_path, 'wb') as f:
        content = await file.read()
        await f.write(content)
    
    # Return URL (adjust based on your static file serving)
    return f"/uploads/media/{unique_filename}"

@router.post("/", response_model=dict)
async def create_newsroom(
    newsroom_data: NewsroomCreate,
    current_user: User = Depends(get_current_active_user)
):
    """Create a new newsroom"""
    
    try:
        # Check if newsroom already exists
        existing = await Newsroom.find_one(Newsroom.owner_id == str(current_user.id))
        if existing:
            raise HTTPException(status_code=400, detail="Newsroom already exists")
        
        newsroom = Newsroom(
            owner_id=str(current_user.id),
            company_info=newsroom_data.company_info,
            brand_colors=newsroom_data.brand_colors or {
                "primary": "#1f2937",
                "secondary": "#6b7280", 
                "accent": "#3b82f6"
            },
            is_public=newsroom_data.is_public or False
        )
        
        await newsroom.create()
        
        return {
            "message": "Newsroom created successfully",
            "newsroom_id": str(newsroom.id),
            "newsroom_url": f"/newsroom/{newsroom.id}",
            "public_url": f"/newsroom/{newsroom.id}/public" if newsroom.is_public else None
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error creating newsroom: {e}")
        raise HTTPException(status_code=500, detail="Failed to create newsroom")

@router.get("/my")
async def get_my_newsroom(current_user: User = Depends(get_current_active_user)):
    """Get current user's newsroom"""
    
    try:
        newsroom = await Newsroom.find_one(Newsroom.owner_id == str(current_user.id))
        
        if not newsroom:
            return {
                "exists": False,
                "message": "No newsroom found. Create one to get started."
            }
        
        return {
            "exists": True,
            "newsroom": newsroom,
            "public_url": f"/newsroom/{newsroom.id}/public" if newsroom.is_public else None
        }
    except Exception as e:
        print(f"Error getting newsroom: {e}")
        raise HTTPException(status_code=500, detail="Failed to get newsroom")

@router.put("/", response_model=dict)
async def update_newsroom(
    updates: NewsroomUpdate,
    current_user: User = Depends(get_current_active_user)
):
    """Update newsroom"""
    
    try:
        newsroom = await Newsroom.find_one(Newsroom.owner_id == str(current_user.id))
        
        if not newsroom:
            raise HTTPException(status_code=404, detail="Newsroom not found")
        
        # Update fields
        update_data = updates.model_dump(exclude_unset=True)
        
        for key, value in update_data.items():
            if hasattr(newsroom, key):
                setattr(newsroom, key, value)
        
        newsroom.last_updated = datetime.utcnow()
        await newsroom.save()
        
        return {
            "message": "Newsroom updated successfully",
            "public_url": f"/newsroom/{newsroom.id}/public" if newsroom.is_public else None
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error updating newsroom: {e}")
        raise HTTPException(status_code=500, detail="Failed to update newsroom")

@router.post("/media", response_model=dict)
async def upload_media_asset(
    file: UploadFile = File(...),
    title: str = Form(...),
    description: str = Form(""),
    current_user: User = Depends(get_current_active_user)
):
    try:
        newsroom = await Newsroom.find_one(Newsroom.owner_id == str(current_user.id))
        if not newsroom:
            raise HTTPException(status_code=404, detail="Newsroom not found")

        allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp', 'video/mp4', 'application/pdf']
        if file.content_type not in allowed_types:
            raise HTTPException(status_code=400, detail=f"File type {file.content_type} not allowed")

        content = await file.read()
        file_size = len(content)
        if file_size > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File too large (max 10MB)")

        await file.seek(0)  # Reset pointer before upload

        file_extension = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_extension}"

        s3_client.upload_fileobj(
            file.file,
            S3_BUCKET,
            unique_filename,
            ExtraArgs={'ContentType': file.content_type}
        )

        file_url = f"https://{S3_BUCKET}.s3.{S3_REGION}.amazonaws.com/{unique_filename}"

        media_asset = MediaAsset(
            type=file.content_type.split('/')[0],
            title=title,
            description=description,
            file_url=file_url,
            file_size=file_size,
            uploaded_at=datetime.utcnow()
        )

        newsroom.media_assets.append(media_asset)
        newsroom.last_updated = datetime.utcnow()
        await newsroom.save()

        return {
            "message": "Media asset uploaded successfully",
            "asset": media_asset,
            "total_assets": len(newsroom.media_assets)
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error uploading media asset: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload media asset")


@router.delete("/media/{asset_index}", response_model=dict)
async def delete_media_asset(
    asset_index: int,
    current_user: User = Depends(get_current_active_user)
):
    """Delete media asset from newsroom"""
    
    try:
        newsroom = await Newsroom.find_one(Newsroom.owner_id == str(current_user.id))
        
        if not newsroom:
            raise HTTPException(status_code=404, detail="Newsroom not found")
        
        if asset_index < 0 or asset_index >= len(newsroom.media_assets):
            raise HTTPException(status_code=404, detail="Media asset not found")
        
        # Remove the asset
        deleted_asset = newsroom.media_assets.pop(asset_index)
        
        # Delete file from S3
        try:
            filename = deleted_asset.file_url.split('/')[-1]
            s3_client.delete_object(Bucket=S3_BUCKET, Key=filename)
        except Exception as e:
            print(f"Warning: Could not delete S3 file {filename}: {e}")
        
        newsroom.last_updated = datetime.utcnow()
        await newsroom.save()
        
        return {
            "message": "Media asset deleted successfully",
            "deleted_asset_title": deleted_asset.title,
            "remaining_assets": len(newsroom.media_assets)
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error deleting media asset: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete media asset")


@router.post("/press-release", response_model=dict)
async def add_press_release(
    pitch_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Add a press release from a pitch to the newsroom"""
    
    try:
        newsroom = await Newsroom.find_one(Newsroom.owner_id == str(current_user.id))
        
        if not newsroom:
            raise HTTPException(status_code=404, detail="Newsroom not found")
        
        # Get the pitch
        from app.models.pitch import Pitch
        try:
            pitch_obj_id = PydanticObjectId(pitch_id)
            pitch = await Pitch.find_one(
                Pitch.id == pitch_obj_id,
                Pitch.user_id == str(current_user.id)
            )
        except:
            raise HTTPException(status_code=400, detail="Invalid pitch ID")
        
        if not pitch:
            raise HTTPException(status_code=404, detail="Pitch not found")
        
        # Check if this press release already exists
        existing_release = next(
            (release for release in newsroom.press_releases 
             if release.get("pitch_id") == str(pitch.id)), 
            None
        )
        
        if existing_release:
            raise HTTPException(status_code=400, detail="Press release already added to newsroom")
        
        # Create press release from pitch
        press_release = {
            "title": pitch.content.press_release.headline,
            "content": pitch.content.press_release.body,
            "published_date": datetime.utcnow(),
            "pitch_id": str(pitch.id),
            "company_name": pitch.company_name,
            "industry": pitch.industry
        }
        
        newsroom.press_releases.append(press_release)
        newsroom.last_updated = datetime.utcnow()
        await newsroom.save()
        
        return {
            "message": "Press release added to newsroom successfully",
            "press_release_title": press_release["title"],
            "total_releases": len(newsroom.press_releases)
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error adding press release: {e}")
        raise HTTPException(status_code=500, detail="Failed to add press release")

@router.delete("/press-release/{release_index}", response_model=dict)
async def delete_press_release(
    release_index: int,
    current_user: User = Depends(get_current_active_user)
):
    """Delete press release from newsroom"""
    
    try:
        newsroom = await Newsroom.find_one(Newsroom.owner_id == str(current_user.id))
        
        if not newsroom:
            raise HTTPException(status_code=404, detail="Newsroom not found")
        
        if release_index < 0 or release_index >= len(newsroom.press_releases):
            raise HTTPException(status_code=404, detail="Press release not found")
        
        # Remove the press release
        deleted_release = newsroom.press_releases.pop(release_index)
        newsroom.last_updated = datetime.utcnow()
        await newsroom.save()
        
        return {
            "message": "Press release deleted successfully",
            "deleted_release_title": deleted_release.get("title", "Unknown"),
            "remaining_releases": len(newsroom.press_releases)
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error deleting press release: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete press release")

@router.get("/{newsroom_id}/public")
async def get_public_newsroom(newsroom_id: str):
    """Get public newsroom (for journalists/public)"""
    
    try:
        newsroom_obj_id = PydanticObjectId(newsroom_id)
        newsroom = await Newsroom.get(newsroom_obj_id)
        
        if not newsroom:
            raise HTTPException(status_code=404, detail="Newsroom not found")
        
        if not newsroom.is_public:
            raise HTTPException(status_code=403, detail="Newsroom is private")
        
        # Increment views
        newsroom.views += 1
        await newsroom.save()
        
        # Sort press releases by date (newest first)
        sorted_releases = sorted(
            newsroom.press_releases, 
            key=lambda x: x.get("published_date", datetime.min), 
            reverse=True
        )
        
        return {
            "id": str(newsroom.id),
            "company_info": newsroom.company_info,
            "press_releases": sorted_releases,
            "media_assets": newsroom.media_assets,
            "brand_colors": newsroom.brand_colors,
            "views": newsroom.views,
            "last_updated": newsroom.last_updated
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting public newsroom: {e}")
        raise HTTPException(status_code=404, detail="Newsroom not found")

@router.get("/stats")
async def get_newsroom_stats(current_user: User = Depends(get_current_active_user)):
    """Get newsroom statistics"""
    
    try:
        newsroom = await Newsroom.find_one(Newsroom.owner_id == str(current_user.id))
        
        if not newsroom:
            return {
                "exists": False,
                "stats": {
                    "views": 0,
                    "press_releases": 0,
                    "media_assets": 0,
                    "is_public": False,
                    "last_updated": None
                }
            }
        
        return {
            "exists": True,
            "stats": {
                "views": newsroom.views,
                "press_releases": len(newsroom.press_releases),
                "media_assets": len(newsroom.media_assets),
                "is_public": newsroom.is_public,
                "last_updated": newsroom.last_updated,
                "created_at": newsroom.created_at
            }
        }
    except Exception as e:
        print(f"Error getting newsroom stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get newsroom stats")

@router.get("/media")
async def list_media_assets(current_user: User = Depends(get_current_active_user)):
    """Get all media assets for current user's newsroom"""
    
    try:
        newsroom = await Newsroom.find_one(Newsroom.owner_id == str(current_user.id))
        
        if not newsroom:
            raise HTTPException(status_code=404, detail="Newsroom not found")
        
        # Sort media assets by upload date (newest first)
        sorted_assets = sorted(
            newsroom.media_assets, 
            key=lambda x: x.uploaded_at, 
            reverse=True
        )
        
        return {
            "media_assets": sorted_assets,
            "total_count": len(sorted_assets),
            "total_size": sum(asset.file_size for asset in sorted_assets)
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error listing media assets: {e}")
        raise HTTPException(status_code=500, detail="Failed to list media assets")

@router.get("/press-releases")
async def list_press_releases(current_user: User = Depends(get_current_active_user)):
    """Get all press releases for current user's newsroom"""
    
    try:
        newsroom = await Newsroom.find_one(Newsroom.owner_id == str(current_user.id))
        
        if not newsroom:
            raise HTTPException(status_code=404, detail="Newsroom not found")
        
        # Sort press releases by published date (newest first)
        sorted_releases = sorted(
            newsroom.press_releases, 
            key=lambda x: x.get("published_date", datetime.min), 
            reverse=True
        )
        
        return {
            "press_releases": sorted_releases,
            "total_count": len(sorted_releases)
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error listing press releases: {e}")
        raise HTTPException(status_code=500, detail="Failed to list press releases")

@router.post("/toggle-public", response_model=dict)
async def toggle_newsroom_public(current_user: User = Depends(get_current_active_user)):
    """Toggle newsroom public/private status"""
    
    try:
        newsroom = await Newsroom.find_one(Newsroom.owner_id == str(current_user.id))
        
        if not newsroom:
            raise HTTPException(status_code=404, detail="Newsroom not found")
        
        # Toggle the public status
        newsroom.is_public = not newsroom.is_public
        newsroom.last_updated = datetime.utcnow()
        await newsroom.save()
        
        return {
            "message": f"Newsroom is now {'public' if newsroom.is_public else 'private'}",
            "is_public": newsroom.is_public,
            "public_url": f"/newsroom/{newsroom.id}/public" if newsroom.is_public else None
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error toggling newsroom status: {e}")
        raise HTTPException(status_code=500, detail="Failed to toggle newsroom status")
