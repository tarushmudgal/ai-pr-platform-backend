# app/routers/chatbot.py
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import StreamingResponse
from typing import List, Optional
from beanie import PydanticObjectId
import requests
from app.models.chatbot import (
    ChatSession, 
    ChatMessageRequest, 
    ChatMessageResponse,
    ChatSessionResponse,
    ChatMessageResponseEnhanced
)
from app.models.user import User
from app.utils.dependencies import get_current_active_user
from app.services.langgraph_ai_agent_service import EnhancedChatbotAgent
from datetime import datetime
import json
import logging
from app.services.subscription_service import subscription_service

logger = logging.getLogger(__name__)
router = APIRouter()



@router.post("/message")
async def send_message(
    request: ChatMessageRequest,
    http_request: Request,
    current_user: User = Depends(get_current_active_user)
):
    """Send a message to the AI agent with streaming response (0.5 credits per message)"""
    
    # Check and deduct credits BEFORE processing
    credit_check = await subscription_service.check_and_deduct_credits(
        user_id=str(current_user.id),
        feature="ai_chat_message"
    )
    
    if not credit_check["success"]:
        raise HTTPException(
            status_code=402,
            detail={
                "error": "insufficient_credits",
                "message": credit_check["message"],
                "remaining_credits": credit_check["remaining_credits"],
                "credits_needed": credit_check.get("credits_needed", 0.5)
            }
        )
    try:
        # Extract Authorization header ("Bearer <token>")
        auth_header = http_request.headers.get("authorization")
        
        # Get or create session
        session = None
        if request.session_id:
            try:
                session_obj_id = PydanticObjectId(request.session_id)
                session = await ChatSession.get(session_obj_id)
                if not session or session.user_id != str(current_user.id):
                    session = None
            except Exception:
                session = None
        
        if not session:
            session = ChatSession(
                user_id=str(current_user.id),
                session_name="New Chat"
            )
            await session.create()
        
        # Save user message to session
        user_message = ChatMessageResponse(
            role="user",
            content=request.message,
            timestamp=datetime.utcnow()
        )
        session.messages.append(user_message)
        session.total_messages += 1
        session.last_activity = datetime.utcnow()
        
        # Initialize agent with auth header
        agent = EnhancedChatbotAgent(current_user, auth_header)
        
        # Build conversation history (exclude current message)
        conversation_history = [
            {"role": msg.role, "content": msg.content}
            for msg in session.messages[:-1]
        ]
        
        async def event_generator():
            full_response = ""
            actions_executed = []
            suggestions = []
            
            try:
                yield f"data: {json.dumps({'type': 'session_id', 'session_id': str(session.id)})}\n\n"
                
                async for event in agent.process_message(request.message, conversation_history):
                    etype = event["type"]
                    
                    if etype == "content":
                        full_response += event["content"]
                        yield f"data: {json.dumps(event)}\n\n"
                    
                    elif etype == "tool_call":
                        tool_event = {
                            "type": "tool_call",
                            "tool": event["tool"],
                            "status": "executing"
                        }
                        yield f"data: {json.dumps(tool_event)}\n\n"
                        actions_executed.append({
                            "tool": event["tool"],
                            "args": event.get("args", {})
                        })
                    
                    elif etype == "tool_result":
                        result_event = {
                            "type": "tool_result",
                            "tool": event["tool"],
                            "status": "completed",
                            "success": event["result"].get("success", False)
                        }
                        yield f"data: {json.dumps(result_event)}\n\n"
                    
                    elif etype == "error":
                        error_event = {
                            "type": "error",
                            "error": event["error"]
                        }
                        yield f"data: {json.dumps(error_event)}\n\n"
                        full_response = f"I encountered an error: {event['error']}"
                        break
                    
                    elif etype == "done":
                        full_response = event["content"]
                        break
                
                # Suggestions
                lower = full_response.lower()
                if "journalist" in lower:
                    suggestions.append({
                        "title": "📧 Send a Pitch",
                        "description": "Send your pitch to selected journalists",
                        "action": "Show me how to send this pitch",
                        "priority": "high"
                    })
                if "pitch" in lower and "create" in lower:
                    suggestions.append({
                        "title": "✏️ Edit Pitch",
                        "description": "Modify the generated pitch",
                        "action": "Rewrite this pitch to be more casual",
                        "priority": "medium"
                    })
                if not actions_executed:
                    suggestions.append({
                        "title": "📊 View Analytics",
                        "description": "Check your performance metrics",
                        "action": "Show me my email statistics",
                        "priority": "low"
                    })
                
                assistant_message = ChatMessageResponse(
                    role="assistant",
                    content=full_response,
                    timestamp=datetime.utcnow(),
                    metadata={
                        "actions_executed": actions_executed,
                        "suggestions": suggestions
                    }
                )
                session.messages.append(assistant_message)
                session.total_messages += 1
                session.last_activity = datetime.utcnow()
                
                if session.session_name == "New Chat" and session.total_messages <= 2:
                    session.session_name = request.message[:50] + ("..." if len(request.message) > 50 else "")
                
                await session.save()
                
                final_event = {
                    "type": "complete",
                    "session_id": str(session.id),
                    "message": {
                        "role": "assistant",
                        "content": full_response,
                        "timestamp": assistant_message.timestamp.isoformat(),
                        "metadata": assistant_message.metadata
                    },
                    "actions_executed": actions_executed,
                    "suggestions": suggestions,
                    "next_steps": generate_next_steps(actions_executed)
                }
                yield f"data: {json.dumps(final_event)}\n\n"
            
            except Exception as e:
                logger.error(f"Streaming error: {e}", exc_info=True)
                error_event = {
                    "type": "error",
                    "error": str(e),
                    "suggestions": [
                        {
                            "title": "🔄 Try Again",
                            "description": "Rephrase your request",
                            "action": "Help me with my PR tasks",
                            "priority": "high"
                        }
                    ]
                }
                yield f"data: {json.dumps(error_event)}\n\n"
        
        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
                "Access-Control-Allow-Origin": "*"
            }
        )
    
    except Exception as e:
        logger.error(f"Failed to process message: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Failed to process your request",
                "error": str(e)
            }
        )


def generate_next_steps(actions_executed: List[dict]) -> List[dict]:
    """Generate contextual next steps based on actions"""
    
    next_steps = []
    
    # Check what actions were executed
    tool_names = [action["tool"] for action in actions_executed]
    
    if "search_journalists_tool" in tool_names:
        next_steps.append({
            "title": "Send Pitch",
            "description": "Send your pitch to the journalists you found",
            "icon": "📧"
        })
    
    if "create_pitch_tool" in tool_names:
        next_steps.append({
            "title": "Review & Edit",
            "description": "Fine-tune your pitch before sending",
            "icon": "✏️"
        })
        next_steps.append({
            "title": "Find Journalists",
            "description": "Search for journalists to send this pitch to",
            "icon": "🔍"
        })
    
    if "send_pitch_tool" in tool_names:
        next_steps.append({
            "title": "Track Engagement",
            "description": "Monitor email opens and responses",
            "icon": "📊"
        })
    
    if not next_steps:
        next_steps = [
            {
                "title": "Create a Pitch",
                "description": "Generate a new press pitch",
                "icon": "✨"
            },
            {
                "title": "Manage Journalists",
                "description": "View and organize your contacts",
                "icon": "👥"
            },
            {
                "title": "View Analytics",
                "description": "Check your campaign performance",
                "icon": "📈"
            }
        ]
    
    return next_steps


@router.post("/validate-context")
async def validate_conversation_context(
    request: ChatMessageRequest,
    current_user: User = Depends(get_current_active_user)
):
    """Debug endpoint to validate conversation context format"""
    
    try:
        if not request.conversation_history:
            return {"valid": True, "message": "No conversation history provided"}
        
        # Validate conversation history format
        valid_messages = []
        errors = []
        
        for i, msg in enumerate(request.conversation_history):
            if not isinstance(msg, dict):
                errors.append(f"Message {i}: Must be a dictionary")
                continue
                
            if "role" not in msg or msg["role"] not in ["user", "assistant"]:
                errors.append(f"Message {i}: Missing or invalid 'role' field")
                
            if "content" not in msg or not msg["content"]:
                errors.append(f"Message {i}: Missing or empty 'content' field")
                
            valid_messages.append(msg)
        
        return {
            "valid": len(errors) == 0,
            "total_messages": len(request.conversation_history),
            "valid_messages": len(valid_messages),
            "errors": errors,
            "context_summary": f"Last {min(6, len(valid_messages))} messages will be used for context"
        }
        
    except Exception as e:
        return {
            "valid": False,
            "error": str(e)
        }


@router.get("/sessions", response_model=List[dict])
async def get_chat_sessions(
    current_user: User = Depends(get_current_active_user)
):
    """Get all chat sessions for the current user"""
    
    try:
        sessions = await ChatSession.find(
            ChatSession.user_id == str(current_user.id),
            ChatSession.is_active == True
        ).sort(-ChatSession.last_activity).limit(20).to_list()
        
        return [
            {
                "id": str(session.id),
                "session_name": session.session_name,
                "last_activity": session.last_activity,
                "total_messages": session.total_messages,
                "preview": session.messages[-1].content[:100] if session.messages else "New chat"
            }
            for session in sessions
        ]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get chat sessions: {str(e)}")


@router.get("/sessions/{session_id}", response_model=ChatSessionResponse)
async def get_chat_session(
    session_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Get a specific chat session"""
    
    try:
        session_obj_id = PydanticObjectId(session_id)
        session = await ChatSession.get(session_obj_id)
        
        if not session or session.user_id != str(current_user.id):
            raise HTTPException(status_code=404, detail="Chat session not found")
        
        return ChatSessionResponse(
            id=str(session.id),
            session_name=session.session_name,
            messages=session.messages,
            is_active=session.is_active,
            created_at=session.created_at,
            last_activity=session.last_activity,
            total_messages=session.total_messages
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get chat session: {str(e)}")


@router.post("/sessions", response_model=dict)
async def create_chat_session(
    current_user: User = Depends(get_current_active_user)
):
    """Create a new chat session"""
    
    try:
        session = ChatSession(
            user_id=str(current_user.id),
            session_name="New Chat"
        )
        await session.create()
        
        return {
            "session_id": str(session.id),
            "message": "New chat session created"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create chat session: {str(e)}")


@router.delete("/sessions/{session_id}")
async def delete_chat_session(
    session_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Delete a chat session"""
    
    try:
        session_obj_id = PydanticObjectId(session_id)
        session = await ChatSession.get(session_obj_id)
        
        if not session or session.user_id != str(current_user.id):
            raise HTTPException(status_code=404, detail="Chat session not found")
        
        session.is_active = False
        await session.save()
        
        return {"message": "Chat session deleted"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete chat session: {str(e)}")


@router.put("/sessions/{session_id}/name")
async def rename_chat_session(
    session_id: str,
    new_name: dict,
    current_user: User = Depends(get_current_active_user)
):
    """Rename a chat session"""
    
    try:
        session_obj_id = PydanticObjectId(session_id)
        session = await ChatSession.get(session_obj_id)
        
        if not session or session.user_id != str(current_user.id):
            raise HTTPException(status_code=404, detail="Chat session not found")
        
        session.session_name = new_name.get("name", "Unnamed Chat")
        await session.save()
        
        return {"message": "Chat session renamed successfully"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to rename chat session: {str(e)}")
