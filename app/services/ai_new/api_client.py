# app/services/api_client.py
import httpx
from typing import Optional, Dict, Any, List
from app.config import settings
import logging

logger = logging.getLogger(__name__)

class APIClient:
    """Singleton API client for making internal API calls"""
    
    _instance: Optional['APIClient'] = None
    _client: Optional[httpx.AsyncClient] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    async def start(self):
        """Initialize the HTTP client"""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url="http://localhost:8000",
                timeout=30.0,
                headers={"Content-Type": "application/json"}
            )
            logger.info("APIClient initialized")
    
    async def stop(self):
        """Close the HTTP client"""
        if self._client:
            await self._client.aclose()
            self._client = None
            logger.info("APIClient closed")
    
    def _get_headers(self, user_id: str, auth_header: Optional[str]) -> Dict[str, str]:
        """Get headers with user authentication"""
        headers: Dict[str, str] = {
            "X-User-ID": user_id,
            "Content-Type": "application/json",
        }
        if auth_header:
            # auth_header is already like "Bearer <token>"
            headers["Authorization"] = auth_header
        return headers
    
    async def _request(
        self, 
        method: str, 
        endpoint: str, 
        user_id: str,
        auth_header: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Make an API request with error handling"""
        if self._client is None:
            raise RuntimeError("APIClient HTTP client is not initialized. Call api_client.start() on startup.")
        
        try:
            headers = self._get_headers(user_id, auth_header)
            response = await self._client.request(
                method=method,
                url=endpoint,
                headers=headers,
                **kwargs
            )
            response.raise_for_status()
            return {
                "success": True,
                "data": response.json(),
                "status_code": response.status_code
            }
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error for {endpoint}: {e.response.status_code} {e.response.text}")
            return {
                "success": False,
                "error": str(e),
                "status_code": e.response.status_code,
                "detail": e.response.text
            }
        except Exception as e:
            logger.error(f"Request failed for {endpoint}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    # Journalist endpoints
    async def search_journalists(
        self, 
        user_id: str,
        auth_header: Optional[str],
        query: Optional[str] = None,
        category: Optional[str] = None,
        skip: int = 0,
        limit: int = 20
    ) -> Dict[str, Any]:
        """Search journalists"""
        params = {"skip": skip, "limit": limit}
        if query:
            params["query"] = query
        if category:
            params["category"] = category
        
        return await self._request(
            "GET",
            "/api/v1/journalists/",
            user_id,
            auth_header=auth_header,
            params=params
        )
    
    async def get_journalist(self, user_id: str, auth_header: Optional[str], journalist_id: str) -> Dict[str, Any]:
        """Get a specific journalist"""
        return await self._request(
            "GET",
            f"/api/v1/journalists/{journalist_id}",
            user_id,
            auth_header=auth_header
        )
    
    async def create_journalist(self, user_id: str, auth_header: Optional[str], data: Dict) -> Dict[str, Any]:
        """Create a new journalist"""
        return await self._request(
            "POST",
            "/api/v1/journalists/",
            user_id,
            auth_header=auth_header,
            json=data
        )
    
    async def update_journalist(
        self, 
        user_id: str, 
        auth_header: Optional[str],
        journalist_id: str, 
        data: Dict
    ) -> Dict[str, Any]:
        """Update a journalist"""
        return await self._request(
            "PUT",
            f"/api/v1/journalists/{journalist_id}",
            user_id,
            auth_header=auth_header,
            json=data
        )
    
    async def delete_journalist(self, user_id: str, auth_header: Optional[str], journalist_id: str) -> Dict[str, Any]:
        """Delete a journalist"""
        return await self._request(
            "DELETE",
            f"/api/v1/journalists/{journalist_id}",
            user_id,
            auth_header=auth_header
        )
    
    async def get_journalist_stats(self, user_id: str, auth_header: Optional[str]) -> Dict[str, Any]:
        """Get journalist statistics"""
        return await self._request(
            "GET",
            "/api/v1/journalists/stats/overview",
            user_id,
            auth_header=auth_header
        )
    
    # Pitch endpoints (same pattern: add auth_header and forward it)
    async def search_pitches(
        self,
        user_id: str,
        auth_header: Optional[str],
        query: Optional[str] = None,
        skip: int = 0,
        limit: int = 20
    ) -> Dict[str, Any]:
        params = {"skip": skip, "limit": limit}
        if query:
            params["query"] = query
        
        return await self._request(
            "GET",
            "/api/v1/pitches/",
            user_id,
            auth_header=auth_header,
            params=params
        )
    
    async def get_pitch(self, user_id: str, auth_header: Optional[str], pitch_id: str) -> Dict[str, Any]:
        return await self._request(
            "GET",
            f"/api/v1/pitches/{pitch_id}",
            user_id,
            auth_header=auth_header
        )
    
    async def create_pitch(self, user_id: str, auth_header: Optional[str], data: Dict) -> Dict[str, Any]:
        return await self._request(
            "POST",
            "/api/v1/pitches/",
            user_id,
            auth_header=auth_header,
            json=data
        )
    
    async def update_pitch(
        self,
        user_id: str,
        auth_header: Optional[str],
        pitch_id: str,
        data: Dict
    ) -> Dict[str, Any]:
        return await self._request(
            "PUT",
            f"/api/v1/pitches/{pitch_id}",
            user_id,
            auth_header=auth_header,
            json=data
        )
    
    async def delete_pitch(self, user_id: str, auth_header: Optional[str], pitch_id: str) -> Dict[str, Any]:
        return await self._request(
            "DELETE",
            f"/api/v1/pitches/{pitch_id}",
            user_id,
            auth_header=auth_header
        )
    
    async def regenerate_pitch(self, user_id: str, auth_header: Optional[str], pitch_id: str) -> Dict[str, Any]:
        return await self._request(
            "POST",
            f"/api/v1/pitches/{pitch_id}/regenerate",
            user_id,
            auth_header=auth_header
        )
    
    async def rewrite_pitch(
        self,
        user_id: str,
        auth_header: Optional[str],
        pitch_id: str,
        instructions: str
    ) -> Dict[str, Any]:
        return await self._request(
            "POST",
            f"/api/v1/pitches/{pitch_id}/rewrite",
            user_id,
            auth_header=auth_header,
            json={"instructions": instructions}
        )
    
    async def get_pitch_stats(self, user_id: str, auth_header: Optional[str]) -> Dict[str, Any]:
        return await self._request(
            "GET",
            "/api/v1/pitches/stats/overview",
            user_id,
            auth_header=auth_header
        )
    
    # Email endpoints (same pattern)
    async def send_pitch_to_journalists(
        self,
        user_id: str,
        auth_header: Optional[str],
        pitch_id: str,
        journalist_ids: List[str],
        custom_subject: Optional[str] = None,
        custom_message: Optional[str] = None
    ) -> Dict[str, Any]:
        data = {
            "pitch_id": pitch_id,
            "journalist_ids": journalist_ids
        }
        if custom_subject:
            data["custom_subject"] = custom_subject
        if custom_message:
            data["custom_message"] = custom_message
        
        return await self._request(
            "POST",
            "/api/v1/emails/send-pitch",
            user_id,
            auth_header=auth_header,
            json=data
        )
    
    async def get_email_interactions(
        self,
        user_id: str,
        auth_header: Optional[str],
        pitch_id: Optional[str] = None,
        journalist_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> Dict[str, Any]:
        params = {"skip": skip, "limit": limit}
        if pitch_id:
            params["pitch_id"] = pitch_id
        if journalist_id:
            params["journalist_id"] = journalist_id
        
        return await self._request(
            "GET",
            "/api/v1/emails/interactions",
            user_id,
            auth_header=auth_header,
            params=params
        )
    
    async def get_email_stats(self, user_id: str, auth_header: Optional[str]) -> Dict[str, Any]:
        return await self._request(
            "GET",
            "/api/v1/emails/stats",
            user_id,
            auth_header=auth_header
        )
    
    # Newsroom endpoints (same pattern)
    async def get_my_newsroom(self, user_id: str, auth_header: Optional[str]) -> Dict[str, Any]:
        return await self._request(
            "GET",
            "/api/v1/newsroom/my",
            user_id,
            auth_header=auth_header
        )
    
    async def create_newsroom(self, user_id: str, auth_header: Optional[str], data: Dict) -> Dict[str, Any]:
        return await self._request(
            "POST",
            "/api/v1/newsroom/",
            user_id,
            auth_header=auth_header,
            json=data
        )
    
    async def update_newsroom(self, user_id: str, auth_header: Optional[str], data: Dict) -> Dict[str, Any]:
        return await self._request(
            "PUT",
            "/api/v1/newsroom/",
            user_id,
            auth_header=auth_header,
            json=data
        )
    
    async def get_newsroom_stats(self, user_id: str, auth_header: Optional[str]) -> Dict[str, Any]:
        return await self._request(
            "GET",
            "/api/v1/newsroom/stats",
            user_id,
            auth_header=auth_header
        )
    
    async def toggle_newsroom_public(self, user_id: str, auth_header: Optional[str]) -> Dict[str, Any]:
        return await self._request(
            "POST",
            "/api/v1/newsroom/toggle-public",
            user_id,
            auth_header=auth_header
        )
    
    async def add_press_release(self, user_id: str, auth_header: Optional[str], data: Dict) -> Dict[str, Any]:
        return await self._request(
            "POST",
            "/api/v1/newsroom/press-release",
            user_id,
            auth_header=auth_header,
            json=data
        )


api_client = APIClient()
