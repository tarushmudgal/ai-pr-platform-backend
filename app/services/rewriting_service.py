from typing import Literal
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.schema.output_parser import StrOutputParser
from app.config import settings


class RewritingService:
    
    def __init__(self):
        if not settings.openai_api_key:
            raise ValueError("OpenAI API key not found")
        
        self.llm = ChatOpenAI(
            api_key=settings.openai_api_key,
            model="gpt-4o-mini",  #  Change model for better output
            temperature=0.7,
            max_tokens=2000
        )
        self.output_parser = StrOutputParser()
    
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
        
        mood_instructions = {
            "professional": "Use formal language, industry terminology, and maintain a business-appropriate tone",
            "empathetic": "Use understanding, compassionate language that connects with the reader emotionally",
            "enthusiastic": "Use exciting, energetic language with positive emotions and compelling calls to action",
            "formal": "Use very formal, academic-style language with sophisticated vocabulary",
            "casual": "Use conversational, friendly language as if talking to a colleague"
        }
        
        length_instructions = {
            "concise": "Make it significantly shorter (50-70% of original length) while keeping all key information",
            "detailed": "Expand with more details, examples, and comprehensive explanations (150-200% of original)",
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
        if content_type == "email":
            placeholder_instruction = "Keep {{journalist_name}} and {{publication}} placeholders EXACTLY as they are with double curly braces. Do NOT replace them with actual names."
        else:
            placeholder_instruction = "Keep [CITY] and [DATE] placeholders EXACTLY as they are. Do NOT add specific dates."
        
        rewrite_prompt = ChatPromptTemplate.from_template("""
You are a professional content editor. Rewrite the following {content_type} with these specifications:

MOOD: {mood}
{mood_description}

LENGTH: {length}
{length_description}

STYLE: {style}
{style_description}

IMPORTANT: {placeholder_rules}

CRITICAL INSTRUCTIONS:
- DO NOT add "Subject:" or any prefixes
- For emails: Start directly with "Hi {{{{journalist_name}}}}" or the greeting
- Maintain all factual information and key points
- Make it compelling and ready to use immediately

ORIGINAL CONTENT:
{content}

REWRITTEN VERSION (output ONLY the rewritten content):""")
        
        try:
            chain = rewrite_prompt | self.llm | self.output_parser
            
            result = await chain.ainvoke({
                "content_type": content_type,
                "mood": mood,
                "mood_description": mood_instructions[mood],
                "length": length,
                "length_description": length_instructions[length],
                "style": style,
                "style_description": style_instructions[style],
                "placeholder_rules": placeholder_instruction,
                "content": content
            })
            
            result = result.strip()
            
            # Clean up for emails
            if content_type == "email":
                lines = result.split('\n')
                cleaned_lines = [line for line in lines if not line.strip().startswith(("Subject:", "SUBJECT:"))]
                result = '\n'.join(cleaned_lines).strip()
            
            print(f"✅ DEBUG: Rewrite successful - {len(result)} characters")
            return result
            
        except Exception as e:
            print(f"❌ Error rewriting content: {e}")
            return content


# Global instance
rewriting_service = RewritingService()
