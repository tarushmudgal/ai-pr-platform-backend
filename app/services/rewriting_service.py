from typing import Literal
from openai import OpenAI
from app.config import settings

class RewritingService:
    
    def __init__(self):
        self.client = OpenAI(api_key=settings.openai_api_key)
    
    async def rewrite_content(
        self, 
        content: str, 
        content_type: Literal["email", "press_release"],
        mood: Literal["professional", "empathetic", "enthusiastic", "formal", "casual"] = "professional",
        length: Literal["concise", "detailed", "shorter", "longer"] = "detailed",
        style: Literal["grammatical", "creative", "technical", "conversational"] = "grammatical"
    ) -> str:
        """Rewrite content with specified mood, length, and style"""
        
        print(f"🔍 DEBUG: Starting rewrite - Type: {content_type}, Mood: {mood}, Length: {length}, Style: {style}")
        print(f"🔍 DEBUG: Input content length: {len(content)} characters")
        print(f"🔍 DEBUG: Input preview: {content[:150]}...")
        
        # Build detailed prompt
        mood_instructions = {
            "professional": "Use formal language, industry terminology, and maintain a business-appropriate tone",
            "empathetic": "Use understanding, compassionate language that connects with the reader emotionally",
            "enthusiastic": "Use exciting, energetic language with positive emotions and compelling calls to action",
            "formal": "Use very formal, academic-style language with sophisticated vocabulary",
            "casual": "Use conversational, friendly language as if talking to a colleague"
        }
        
        length_instructions = {
            "concise": "Make it significantly shorter while keeping all key information",
            "detailed": "Expand with more details, examples, and comprehensive explanations",
            "shorter": "Reduce length by about 30% while maintaining core message",
            "longer": "Increase length by about 50% with additional context and details"
        }
        
        style_instructions = {
            "grammatical": "Focus on perfect grammar, clear structure, and professional writing standards",
            "creative": "Use creative language, metaphors, and engaging storytelling elements",
            "technical": "Use industry-specific terminology and technical precision",
            "conversational": "Write as if having a friendly conversation with the reader"
        }
        
        placeholder_instruction = ""
        if content_type == "press_release":
            placeholder_instruction = "\n- Keep any existing placeholders like [CITY], [DATE] unchanged"
        else:
            placeholder_instruction = "\n- Keep any existing placeholders like {journalist_name}, {publication} unchanged\n- Do not add specific dates - use general terms like 'recently' instead"
        

        prompt = f"""Rewrite the following {content_type} with these specific requirements:

    MOOD: {mood} - {mood_instructions[mood]}
    LENGTH: {length} - {length_instructions[length]}  
    STYLE: {style} - {style_instructions[style]}

    ORIGINAL CONTENT:
    {content}

    INSTRUCTIONS:
    - Do NOT include subject lines in your response
    - Do NOT add "Subject:" prefixes
    - Start directly with the content (for emails, start with "Hi" or the greeting)
    - Maintain all factual information and key messages
    - Ensure the rewritten version matches the specified mood, length, and style
    - Keep the same structure and format as the original
    - Make it compelling and engaging for journalists/media professionals
    - Ensure it's ready to use without further editing

    REWRITTEN CONTENT:"""
        
        try:
            print(f"🔍 DEBUG: Sending request to OpenAI...")
            response = self.client.chat.completions.create(
                model="gpt-4.1-nano-2025-04-14",
                messages=[{
                    "role": "user", 
                    "content": prompt
                }],
                temperature=0.7,
                max_tokens=2000
            )
            
            result = response.choices[0].message.content.strip()
            print(f"🔍 DEBUG: OpenAI response received: {len(result)} characters")
            print(f"🔍 DEBUG: Response preview: {result[:150]}...")
            return result
            
        except Exception as e:
            print(f"❌ Error rewriting content: {e}")
            return content  # Return original on error


# Global instance
rewriting_service = RewritingService()
