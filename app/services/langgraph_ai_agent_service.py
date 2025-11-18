# app/services/chatbot_agent.py
from typing import Dict, Any, Optional, List, AsyncGenerator
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, MessagesState, END
from langgraph.prebuilt import ToolNode
from app.services.ai_new.api_client import api_client
from app.models.user import User
import json
from app.models.pitch import AnnouncementType
from typing import Dict, Any, Optional, List
from app.models.pitch import AnnouncementType  # import your enum
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class EnhancedChatbotAgent:
    """Production-ready chatbot agent with API integration"""
    
    def __init__(self, user: User, auth_header: Optional[str] = None):
        self.user = user
        self.user_id = str(user.id)
        self.auth_header = auth_header  # <-- store Authorization: Bearer <token>
        
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.7,
            streaming=True
        )
        self.tools = self._create_tools()
        self.agent = self._build_agent()
    
    def _create_tools(self) -> List:
        """Create tools with API integrations"""
        
        @tool
        async def search_journalists_tool(
            query: Optional[str] = None,
            category: Optional[str] = None,
            limit: int = 10,
        ) -> dict:
            """
            Search for journalists in your database.

            - query should be taken directly from the user's input (name, email, publication, etc.),
            but will be normalized (trimmed and lowercased) before searching.
            """

            raw_query = (query or "").strip()
            normalized_query = raw_query.lower() or None  # backend should do case-insensitive search

            # First attempt: normalized query
            result = await api_client.search_journalists(
                user_id=self.user_id,
                auth_header=self.auth_header,
                query=normalized_query,
                category=category,
                limit=limit,
            )

            # If success and we have journalists, return the normalized result
            if result.get("success") and result["data"].get("journalists"):
                data = result["data"]
                return {
                    "success": True,
                    "total": data.get("total", 0),
                    "journalists": [
                        {
                            "id": j["id"],
                            "name": j["name"],
                            "email": j["email"],
                            "publication": j.get("publication"),
                            "category": j.get("category"),
                            "beat": j.get("beat"),
                        }
                        for j in data.get("journalists", [])
                    ],
                }

            # Optional: simple fallback when query is a single "word" and no results
            # e.g., try stripping a trailing char in case of common one-letter hallucination
            if raw_query and " " not in raw_query and len(raw_query) > 3:
                fallback_query = raw_query[:-1].lower()
                if fallback_query != normalized_query:
                    fallback_result = await api_client.search_journalists(
                        user_id=self.user_id,
                        auth_header=self.auth_header,
                        query=fallback_query,
                        category=category,
                        limit=limit,
                    )
                    if fallback_result.get("success") and fallback_result["data"].get("journalists"):
                        data = fallback_result["data"]
                        return {
                            "success": True,
                            "total": data.get("total", 0),
                            "journalists": [
                                {
                                    "id": j["id"],
                                    "name": j["name"],
                                    "email": j["email"],
                                    "publication": j.get("publication"),
                                    "category": j.get("category"),
                                    "beat": j.get("beat"),
                                }
                                for j in data.get("journalists", [])
                            ],
                        }

            # Fall back to original result (empty list) if nothing matches
            return {
                "success": result.get("success", False),
                "total": result.get("data", {}).get("total", 0) if result.get("data") else 0,
                "journalists": result.get("data", {}).get("journalists", []),
                "error": result.get("error"),
                "status_code": result.get("status_code"),
                "detail": result.get("detail"),
            }

        
        @tool
        async def get_journalist_details_tool(journalist_id: str) -> dict:
            """
            Get detailed information about a specific journalist.
            """
            result = await api_client.get_journalist(
                user_id=self.user_id,
                auth_header=self.auth_header,
                journalist_id=journalist_id
            )
            return result
        
        @tool
        async def create_journalist_tool(
            name: str,
            email: str,
            publication: Optional[str] = None,
            category: Optional[str] = None,
            beat: Optional[str] = None,
            country: Optional[str] = None,
        ) -> dict:
            """
            Add a new journalist to your database.

            - category can be free text (e.g. "Fashion") and will be normalized to one of:
            technology, business, healthcare, finance, lifestyle, entertainment, sports, other.
            If it doesn't match, it will be set to "other".
            - country is required by the backend; if not provided, defaults to "US".
            """

            # Allowed enum values from your backend
            allowed = {
                "technology",
                "business",
                "healthcare",
                "finance",
                "lifestyle",
                "entertainment",
                "sports",
                "other",
            }

            # Normalize category: lowercase + fallback to "other"
            cat = (category or "").strip().lower()
            normalized_category = cat if cat in allowed else "other"

            # Ensure country is present (backend requires it)
            normalized_country = (country or "").strip()
            if not normalized_country:
                normalized_country = "US"  # or whatever default makes sense

            data = {
                "name": name,
                "email": email,
                "publication": publication,
                "category": normalized_category,
                "beat": beat,
                "country": normalized_country,
            }

            result = await api_client.create_journalist(
                user_id=self.user_id,
                auth_header=self.auth_header,
                data=data,
            )

            if not result.get("success"):
                return {
                    "success": False,
                    "error": result.get("error"),
                    "status_code": result.get("status_code"),
                    "detail": result.get("detail"),
                    "sent_payload": data,
                }

            return result

        
        @tool
        async def search_pitches_tool(
            query: Optional[str] = None,
            limit: int = 10
        ) -> dict:
            """
            Search for your press pitches.
            """
            result = await api_client.search_pitches(
                user_id=self.user_id,
                auth_header=self.auth_header,
                query=query,
                limit=limit
            )
            
            if result["success"]:
                data = result["data"]
                return {
                    "success": True,
                    "total": data.get("total", 0),
                    "pitches": [
                        {
                            "id": p["id"],
                            "company_name": p.get("company_name"),
                            "headline": p.get("content", {}).get("email_pitch", {}).get("subject"),
                            "created_at": p.get("created_at"),
                            "announcement_type": p.get("announcement_type")
                        }
                        for p in data.get("pitches", [])
                    ]
                }
            return result
        
        @tool
        async def get_pitch_details_tool(pitch_id: str) -> dict:
            """
            Get full details of a specific pitch.
            """
            result = await api_client.get_pitch(
                user_id=self.user_id,
                auth_header=self.auth_header,
                pitch_id=pitch_id
            )
            return result
        


        @tool
        async def create_pitch_tool(
            company_name: str,
            announcement_type: str,
            key_details: Optional[Dict[str, Any]] = None
        ) -> dict:
            """
            Create a new AI-powered press pitch.

            announcement_type can be free text (e.g., "product launch") and will be normalized
            to one of: product_launch, funding, partnership, executive_hire, award, research, other.

            key_details may contain:
            - product_name: str
            - description: str
            - industry: str
            - headline: str
            - key_points: List[str]
            """

            # 1) Normalize announcement_type to your enum values
            t = announcement_type.lower()
            if "product" in t or "launch" in t:
                normalized_type = AnnouncementType.PRODUCT_LAUNCH.value
            elif "fund" in t or "seed" in t or "series" in t:
                normalized_type = AnnouncementType.FUNDING.value
            elif "partner" in t:
                normalized_type = AnnouncementType.PARTNERSHIP.value
            elif "executive" in t or "hire" in t or "appointment" in t:
                normalized_type = AnnouncementType.EXECUTIVE_HIRE.value
            elif "award" in t or "recognition" in t:
                normalized_type = AnnouncementType.AWARD.value
            elif "research" in t or "study" in t or "report" in t:
                normalized_type = AnnouncementType.RESEARCH.value
            else:
                normalized_type = AnnouncementType.OTHER.value

            key_details = key_details or {}

            # 2) Derive industry
            industry = key_details.get("industry")
            if not industry:
                # default – adjust if you want something smarter
                industry = "technology"

            # 3) Derive headline
            product_name = key_details.get("product_name") or "a new product"
            description = key_details.get("description") or \
                "an AI-powered solution for startups."

            headline = key_details.get("headline")
            if not headline:
                # Keep within 200 chars – Pydantic enforces max_length=200
                base_headline = f"{company_name} launches {product_name} – {description}"
                headline = base_headline[:200]

            # 4) Derive key_points list
            raw_key_points = key_details.get("key_points")

            if isinstance(raw_key_points, list):
                # Filter to non-empty strings
                key_points: List[str] = [str(k).strip() for k in raw_key_points if str(k).strip()]
            else:
                key_points = []

            # Ensure 1–10 items as required by schema
            if not key_points:
                key_points = [
                    f"Introducing {product_name} from {company_name}",
                    f"Designed for {industry} companies and startups",
                    "AI-powered automation to speed up PR and pitch creation"
                ]
            # Cap at 10 items
            key_points = key_points[:10]

            # 5) Build a PitchCreate-compliant payload
            data = {
                "headline": headline,
                "company_name": company_name,
                "key_points": key_points,
                "industry": industry,
                "announcement_type": normalized_type
            }

            # 6) Call your backend
            result = await api_client.create_pitch(
                user_id=self.user_id,
                auth_header=self.auth_header,
                data=data
            )

            # 7) Bubble up error details for debugging if needed
            if not result.get("success"):
                return {
                    "success": False,
                    "error": result.get("error"),
                    "status_code": result.get("status_code"),
                    "detail": result.get("detail"),
                    "sent_payload": data
                }

            return result

        
        @tool
        async def rewrite_pitch_tool(pitch_id: str, instructions: str) -> dict:
            """
            Rewrite/modify an existing pitch with specific instructions.
            """
            result = await api_client.rewrite_pitch(
                user_id=self.user_id,
                auth_header=self.auth_header,
                pitch_id=pitch_id,
                instructions=instructions
            )
            return result
        
        @tool
        async def send_pitch_tool(
            pitch_id: str,
            journalist_ids: List[str],
            custom_subject: Optional[str] = None,
            custom_message: Optional[str] = None
        ) -> dict:
            """
            Send a pitch to one or more journalists via email.
            """
            result = await api_client.send_pitch_to_journalists(
                user_id=self.user_id,
                auth_header=self.auth_header,
                pitch_id=pitch_id,
                journalist_ids=journalist_ids,
                custom_subject=custom_subject,
                custom_message=custom_message
            )
            return result
        
        @tool
        async def get_journalist_stats_tool() -> dict:
            """
            Get statistics about your journalist database.
            """
            result = await api_client.get_journalist_stats(
                user_id=self.user_id,
                auth_header=self.auth_header
            )
            return result
        
        @tool
        async def get_pitch_stats_tool() -> dict:
            """
            Get statistics about your pitches.
            """
            result = await api_client.get_pitch_stats(
                user_id=self.user_id,
                auth_header=self.auth_header
            )
            return result
        
        @tool
        async def get_email_stats_tool() -> dict:
            """
            Get email campaign statistics.
            """
            result = await api_client.get_email_stats(
                user_id=self.user_id,
                auth_header=self.auth_header
            )
            return result
        
        @tool
        async def get_email_interactions_tool(
            pitch_id: Optional[str] = None,
            journalist_id: Optional[str] = None,
            limit: int = 20
        ) -> dict:
            """
            Get email interaction history.
            """
            result = await api_client.get_email_interactions(
                user_id=self.user_id,
                auth_header=self.auth_header,
                pitch_id=pitch_id,
                journalist_id=journalist_id,
                limit=limit
            )
            return result
        
        @tool
        async def get_newsroom_tool() -> dict:
            """
            Get your newsroom information.
            """
            result = await api_client.get_my_newsroom(
                user_id=self.user_id,
                auth_header=self.auth_header
            )
            return result
        
        @tool
        async def get_newsroom_stats_tool() -> dict:
            """
            Get newsroom statistics.
            """
            result = await api_client.get_newsroom_stats(
                user_id=self.user_id,
                auth_header=self.auth_header
            )
            return result
        
        return [
            search_journalists_tool,
            get_journalist_details_tool,
            create_journalist_tool,
            search_pitches_tool,
            get_pitch_details_tool,
            create_pitch_tool,
            rewrite_pitch_tool,
            send_pitch_tool,
            get_journalist_stats_tool,
            get_pitch_stats_tool,
            get_email_stats_tool,
            get_email_interactions_tool,
            get_newsroom_tool,
            get_newsroom_stats_tool
        ]
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt for the agent"""
        return f"""You are a professional PR assistant for {self.user.company_name}.

CRITICAL RULES:
1. ALWAYS use tools for data operations - never fabricate journalist names, pitches, or statistics
2. When users ask to "send" or "create", use the appropriate tool immediately
3. For questions about "my journalists", "my pitches", or "analytics", use search/stats tools first
4. If a tool returns success=False, explain the error clearly and suggest alternatives
5. Keep responses concise and actionable - under 3 sentences unless explaining complex data
6. When sending pitches, confirm journalist selection before calling send_pitch_tool

TOOL USAGE GUIDELINES:
- "show my journalists" / "list journalists" → search_journalists_tool()
- "find tech journalists" → search_journalists_tool(category="Technology")
- "show my pitches" / "list pitches" → search_pitches_tool()
- "create a pitch about X" → create_pitch_tool()
- "send pitch to John" → search_journalists_tool(query="John"), then send_pitch_tool()
- "how am I doing?" / "show stats" → get_pitch_stats_tool() + get_email_stats_tool()
- "rewrite pitch to be more casual" → rewrite_pitch_tool()
- "email performance" → get_email_stats_tool() + get_email_interactions_tool()

RESPONSE STYLE:
- Be professional but conversational
- Provide actionable insights from data
- Format lists clearly with bullet points
- Highlight important metrics
- Always confirm actions before execution

Your user is: {self.user.full_name} from {self.user.company_name}
"""
    
    def _build_agent(self):
        """Build the LangGraph agent with tool calling"""
        
        llm_with_tools = self.llm.bind_tools(self.tools)
        
        async def call_model(state: MessagesState) -> Dict[str, Any]:
            messages = state["messages"]
            response = await llm_with_tools.ainvoke(messages)
            return {"messages": [response]}
        
        tool_node = ToolNode(self.tools)
        
        def should_continue(state: MessagesState) -> str:
            messages = state["messages"]
            last_message = messages[-1]
            if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
                return "tools"
            return END
        
        workflow = StateGraph(MessagesState)
        workflow.add_node("agent", call_model)
        workflow.add_node("tools", tool_node)
        workflow.set_entry_point("agent")
        workflow.add_conditional_edges(
            "agent",
            should_continue,
            {"tools": "tools", END: END}
        )
        workflow.add_edge("tools", "agent")
        
        return workflow.compile()
    
    async def process_message(
        self,
        message: str,
        conversation_history: Optional[List[Dict]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        try:
            messages = [SystemMessage(content=self._get_system_prompt())]
            
            if conversation_history:
                for msg in conversation_history[-6:]:
                    if msg["role"] == "user":
                        messages.append(HumanMessage(content=msg["content"]))
                    elif msg["role"] == "assistant":
                        messages.append(AIMessage(content=msg["content"]))
            
            messages.append(HumanMessage(content=message))
            
            full_response = ""
            tool_calls_made = []
            
            async for event in self.agent.astream({"messages": messages}, stream_mode="values"):
                last_message = event["messages"][-1]
                
                if isinstance(last_message, AIMessage):
                    if last_message.content and last_message.content != full_response:
                        chunk = last_message.content[len(full_response):]
                        full_response = last_message.content
                        yield {"type": "content", "content": chunk}
                    
                    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
                        for tool_call in last_message.tool_calls:
                            if tool_call not in tool_calls_made:
                                tool_calls_made.append(tool_call)
                                yield {"type": "tool_call", "tool": tool_call["name"], "args": tool_call["args"]}
                
                elif isinstance(last_message, ToolMessage):
                    try:
                        result = json.loads(last_message.content)
                        yield {"type": "tool_result", "tool": last_message.name, "result": result}
                    except json.JSONDecodeError:
                        yield {"type": "tool_result", "tool": last_message.name, "result": {"raw": last_message.content}}
            
            yield {"type": "done", "content": full_response}
        
        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            yield {"type": "error", "error": str(e)}
