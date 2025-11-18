from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.schema.output_parser import StrOutputParser
from app.config import settings
from app.models.pitch import PitchCreate, GeneratedContent, PressRelease, EmailPitch, GenerationMetadata
from typing import Dict, Any
import time
import re

class AIService:
    def __init__(self):
        if not settings.openai_api_key:
            raise ValueError("OpenAI API key not found. Please set OPENAI_API_KEY in your environment.")
        
        self.llm = ChatOpenAI(
            api_key=settings.openai_api_key,
            model="gpt-4.1-nano-2025-04-14",
            temperature=0.7,
            max_tokens=1500
        )
        self.output_parser = StrOutputParser()
    
    async def generate_pitch_content(self, pitch_data: PitchCreate) -> GeneratedContent:
        """Generate press release and email pitch"""
        
        start_time = time.time()
        
        try:
            # Generate press release
            press_release = await self._generate_press_release(pitch_data)
            
            # Generate email pitch
            email_pitch = await self._generate_email_pitch(pitch_data)
            
            generation_time = int((time.time() - start_time) * 1000)
            
            return GeneratedContent(
                press_release=press_release,
                email_pitch=email_pitch
            ), GenerationMetadata(
                generation_time_ms=generation_time,
                quality_score=self._calculate_quality_score(press_release, email_pitch)
            )
            
        except Exception as e:
            raise Exception(f"AI generation failed: {str(e)}")
    
    async def _generate_press_release(self, pitch_data: PitchCreate) -> PressRelease:
        """Generate professional press release"""
        
        press_release_prompt = ChatPromptTemplate.from_template("""
        You are a professional PR writer. Create a compelling press release for the following information:

        Company: {company_name}
        Headline: {headline}
        Industry: {industry}
        Announcement Type: {announcement_type}
        Key Points: {key_points}

        Requirements:
        - Professional press release format
        - Use placeholder "[CITY], [DATE]" for dateline instead of specific dates
        - Compelling headline and subheadline
        - 3-4 body paragraphs
        - Include a company boilerplate at the end
        - 400-500 words total
        - DO NOT use any specific dates like "October 27, 2023" or "NEW YORK, October 27, 2023"                                                                
        - Professional, newsworthy tone
        - Use "[CITY], [DATE]" at the beginning of the press release body
        Format:
        HEADLINE: [Compelling headline]

        SUBHEADLINE: [Supporting subheadline]

        [CITY], [DATE] — {company_name}, [Press release body with multiple paragraphs]

        About [Company Name]:
        [Brief company description and boilerplate]
        """)
        
        chain = press_release_prompt | self.llm | self.output_parser
        
        result = await chain.ainvoke({
            "company_name": pitch_data.company_name,
            "headline": pitch_data.headline,
            "industry": pitch_data.industry,
            "announcement_type": pitch_data.announcement_type.replace("_", " ").title(),
            "key_points": ", ".join(pitch_data.key_points)
        })
        
        # Parse the result to extract headline and body
        lines = result.strip().split('\n')
        headline = ""
        body = ""
        
        for i, line in enumerate(lines):
            if line.startswith("HEADLINE:"):
                headline = line.replace("HEADLINE:", "").strip()
            elif line.strip() and not line.startswith(("HEADLINE:", "SUBHEADLINE:")):
                body = '\n'.join(lines[i:]).strip()
                break
        
        if not headline:
            headline = pitch_data.headline
        
        if not body:
            body = result
        
        return PressRelease(
            headline=headline,
            body=body,
            word_count=len(body.split())
        )
    
    async def _generate_email_pitch(self, pitch_data: PitchCreate) -> EmailPitch:
        """Generate personalized email pitch"""
        
        email_pitch_prompt = ChatPromptTemplate.from_template("""
        You are a PR professional writing a personalized media pitch email. Create an email pitch for:

        Company: {company_name}
        Story: {headline}
        Industry: {industry}
        Key Points: {key_points}
        Announcement Type: {announcement_type}

        Requirements:
        - Personalized, conversational tone
        - Compelling subject line
        - Brief and to-the-point (150-200 words)
        - Clear value proposition for the journalist
        - DO NOT include any specific dates                                                              
        - Include placeholders: {{journalist_name}} and {{publication}}
        - Strong call-to-action
        - If you need to reference timing, use phrases like "recently announced" or "just launched"
                                                              
        Format:
        SUBJECT: [Compelling email subject line]

        Hi {{journalist_name}},

        [Email body with personalized pitch]

        Best regards,
        [Your name]
        """)
        
        chain = email_pitch_prompt | self.llm | self.output_parser
        
        result = await chain.ainvoke({
            "company_name": pitch_data.company_name,
            "headline": pitch_data.headline,
            "industry": pitch_data.industry,
            "announcement_type": pitch_data.announcement_type.replace("_", " ").title(),
            "key_points": ", ".join(pitch_data.key_points)
        })
        
        # Parse subject and body
        lines = result.strip().split('\n')
        subject = ""
        body = ""
        
        for i, line in enumerate(lines):
            if line.startswith("SUBJECT:"):
                subject = line.replace("SUBJECT:", "").strip()
            elif line.strip() and not line.startswith("SUBJECT:"):
                body = '\n'.join(lines[i:]).strip()
                break
        
        if not subject:
            subject = f"Exclusive: {pitch_data.headline}"
        
        if not body:
            body = result
        
        return EmailPitch(
            subject=subject,
            body=body,
            word_count=len(body.split())
        )
    
    def _calculate_quality_score(self, press_release: PressRelease, email_pitch: EmailPitch) -> float:
        """Calculate content quality score (1-10)"""
        score = 5.0  # Base score
        
        # Check word count ranges
        if 400 <= press_release.word_count <= 500:
            score += 1.0
        elif 300 <= press_release.word_count <= 600:
            score += 0.5
        
        if 150 <= email_pitch.word_count <= 200:
            score += 1.0
        elif 100 <= email_pitch.word_count <= 250:
            score += 0.5
        
        # Check for key elements
        if "about" in press_release.body.lower():  # Has boilerplate
            score += 0.5
        
        if "{journalist_name}" in email_pitch.body:  # Has personalization
            score += 0.5
        
        if "{publication}" in email_pitch.body:
            score += 0.5
        
        # Check for professional language
        professional_words = ["announce", "today", "leading", "innovative", "solutions"]
        if any(word in press_release.body.lower() for word in professional_words):
            score += 0.5
        
        return min(10.0, max(1.0, score))  # Clamp between 1-10

# Global AI service instance
ai_service = AIService()
