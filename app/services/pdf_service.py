# Create app/services/pdf_service.py
import os
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.lib import colors
from io import BytesIO
import tempfile
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.pitch import Pitch
    from app.models.user import User

class PDFService:
    
    def generate_press_release_pdf(self, pitch: 'Pitch', user: 'User') -> bytes:
        """Generate PDF from pitch content using reportlab"""
        
        try:
            # Extract the actual press release text from the body attribute
            press_release_text = self._extract_press_release_text(pitch)
            print(f"🔍 DEBUG: Successfully extracted {len(press_release_text)} characters")
            
            buffer = BytesIO()
            doc = SimpleDocTemplate(
                buffer, 
                pagesize=A4,
                rightMargin=72, 
                leftMargin=72,
                topMargin=72, 
                bottomMargin=72
            )
            
            styles = getSampleStyleSheet()
            
            # Custom styles
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=22,
                spaceAfter=30,
                alignment=TA_CENTER,
                textColor=colors.HexColor('#333333'),
                fontName='Helvetica-Bold'
            )
            
            header_style = ParagraphStyle(
                'CustomHeader',
                parent=styles['Heading2'],
                fontSize=16,
                spaceAfter=15,
                textColor=colors.HexColor('#667eea'),
                fontName='Helvetica-Bold'
            )
            
            body_style = ParagraphStyle(
                'CustomBody',
                parent=styles['Normal'],
                fontSize=12,
                spaceAfter=12,
                alignment=TA_JUSTIFY
            )
            
            # Build PDF content
            story = []
            
            # Header with branding
            story.append(Paragraph(pitch.company_name, 
                ParagraphStyle('Brand', fontSize=14, alignment=TA_CENTER, textColor=colors.HexColor('#667eea'))
            ))
            story.append(Spacer(1, 20))
            
            # Press Release Header
            story.append(Paragraph("PRESS RELEASE", header_style))
            story.append(Spacer(1, 10))
            
            # FOR IMMEDIATE RELEASE
            story.append(Paragraph("<b>FOR IMMEDIATE RELEASE</b>", 
                ParagraphStyle('Release', fontSize=12, alignment=TA_LEFT, textColor=colors.red)
            ))
            story.append(Spacer(1, 20))
            
            # Headline
            story.append(Paragraph(str(pitch.headline), title_style))
            story.append(Spacer(1, 20))
            
            # Company & Date
            story.append(Paragraph(
                f"<b>{pitch.company_name}</b> | {pitch.created_at.strftime('%B %d, %Y')}", 
                body_style
            ))
            story.append(Spacer(1, 20))
            
            # Press Release Content - Clean up and format
            paragraphs = press_release_text.split('\n\n')
            
            for paragraph in paragraphs:
                if paragraph.strip():
                    clean_paragraph = paragraph.strip()
                    clean_paragraph = clean_paragraph.replace('<', '&lt;').replace('>', '&gt;')
                    # Clean up markdown formatting for PDF
                    #clean_paragraph = paragraph.strip()
                    #clean_paragraph = clean_paragraph.replace('**', '<b>').replace('**', '</b>')
                    #clean_paragraph = clean_paragraph.replace('*', '<i>').replace('*', '</i>')
                    # Remove any remaining markdown
                    #clean_paragraph = clean_paragraph.replace('**', '').replace('*', '')
                    
                    story.append(Paragraph(clean_paragraph, body_style))
                    story.append(Spacer(1, 12))
            
            story.append(Spacer(1, 30))
            
            # Separator line
            story.append(Paragraph("─" * 50, 
                ParagraphStyle('Separator', fontSize=10, alignment=TA_CENTER, textColor=colors.grey)
            ))
            story.append(Spacer(1, 20))
            
            # Contact Information
            story.append(Paragraph("<b>Media Contact Information</b>", header_style))
            story.append(Paragraph(f"<b>Contact Person:</b> {user.full_name}", body_style))
            story.append(Paragraph(f"<b>Company:</b> {user.company_name or 'Not specified'}", body_style))
            story.append(Paragraph(f"<b>Email:</b> {user.email}", body_style))
            story.append(Spacer(1, 30))
            
            # Footer
            story.append(Paragraph("###", 
                ParagraphStyle('End', fontSize=16, alignment=TA_CENTER, textColor=colors.grey)
            ))
            story.append(Spacer(1, 20))
            
            story.append(Paragraph(
                f"This press release was created by {pitch.company_name}", 
                ParagraphStyle('Footer', fontSize=8, textColor=colors.grey, alignment=TA_CENTER)
            ))
            
            # Build PDF
            doc.build(story)
            buffer.seek(0)
            print(f"✅ PDF generated successfully: {len(buffer.getvalue())} bytes")
            return buffer.getvalue()
            
        except Exception as e:
            print(f"Error generating PDF: {e}")
            import traceback
            traceback.print_exc()
            # Return a simple fallback
            return self._generate_simple_pdf_fallback(pitch, user)

    def _extract_press_release_text(self, pitch: 'Pitch') -> str:
        """Extract press release text from pitch object - Fixed for your structure"""
        
        try:
            # Based on your debug output: pitch.content.press_release.body contains the text
            if hasattr(pitch.content, 'press_release') and hasattr(pitch.content.press_release, 'body'):
                #return str(pitch.content.press_release.body)
                #        if hasattr(pitch.content, 'press_release') and hasattr(pitch.content.press_release, 'body'):
                text = str(pitch.content.press_release.body)
                
                # Clean up the text to remove problematic markup
                # Remove all markdown formatting completely
                import re
                
                # Remove **bold** formatting
                text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
                
                # Remove *italic* formatting  
                text = re.sub(r'\*(.*?)\*', r'\1', text)
                
                # Remove any HTML-like tags that might cause issues
                text = re.sub(r'<[^>]+>', '', text)
                
                # Clean up any remaining problematic characters
                text = text.replace('**', '').replace('*', '')
                
                # Remove extra whitespace
                text = re.sub(r'\s+', ' ', text).strip()
                
                return text

            
            # Fallback: Try other possible attributes
            if hasattr(pitch.content, 'press_release'):
                press_release = pitch.content.press_release
                
                # Check for content attribute
                if hasattr(press_release, 'content'):
                    return str(press_release.content)
                
                # Check for text attribute
                if hasattr(press_release, 'text'):
                    return str(press_release.text)
                
                # Try to convert object to string
                return str(press_release)
            
            # Final fallback - create basic content
            fallback_text = f"{pitch.headline}\n\n"
            
            if hasattr(pitch, 'key_points') and pitch.key_points:
                fallback_text += "Key Points:\n"
                for point in pitch.key_points:
                    fallback_text += f"• {point}\n"
                fallback_text += "\n"
            
            fallback_text += f"Industry: {getattr(pitch, 'industry', 'Technology')}\n"
            fallback_text += f"Announcement Type: {getattr(pitch, 'announcement_type', 'General')}\n"
            
            return fallback_text
            
        except Exception as e:
            print(f"Error extracting press release text: {e}")
            return f"Press Release: {pitch.headline}\n\nContent extraction failed. Please contact support."

    def _generate_simple_pdf_fallback(self, pitch: 'Pitch', user: 'User') -> bytes:
        """Simple fallback PDF generation using canvas"""
        
        try:
            from reportlab.pdfgen import canvas
            
            buffer = BytesIO()
            p = canvas.Canvas(buffer, pagesize=A4)
            
            # Simple text-based PDF
            y_position = 750
            
            # Title
            p.setFont("Helvetica-Bold", 20)
            p.drawString(100, y_position, f"PRESS RELEASE")
            y_position -= 40
            
            # Headline
            p.setFont("Helvetica-Bold", 16)
            # Split long headlines into multiple lines
            headline = str(pitch.headline)
            if len(headline) > 60:
                words = headline.split()
                line1 = ' '.join(words[:len(words)//2])
                line2 = ' '.join(words[len(words)//2:])
                p.drawString(100, y_position, line1)
                y_position -= 20
                p.drawString(100, y_position, line2)
            else:
                p.drawString(100, y_position, headline)
            y_position -= 40
            
            # Company and date
            p.setFont("Helvetica", 12)
            p.drawString(100, y_position, f"{pitch.company_name} | {pitch.created_at.strftime('%B %d, %Y')}")
            y_position -= 30
            
            # Content note
            p.drawString(100, y_position, "This is a simplified version of the press release.")
            y_position -= 20
            p.drawString(100, y_position, "Full content generation encountered an error.")
            y_position -= 40
            
            # Key points if available
            if hasattr(pitch, 'key_points') and pitch.key_points:
                p.setFont("Helvetica-Bold", 12)
                p.drawString(100, y_position, "Key Points:")
                y_position -= 20
                
                p.setFont("Helvetica", 11)
                for point in pitch.key_points[:5]:  # Limit to 5 points
                    if y_position > 100:
                        p.drawString(120, y_position, f"• {point}")
                        y_position -= 18
            
            # Contact info
            y_position -= 30
            p.setFont("Helvetica-Bold", 12)
            p.drawString(100, y_position, "Media Contact:")
            y_position -= 20
            
            p.setFont("Helvetica", 11)
            p.drawString(100, y_position, f"Name: {user.full_name}")
            y_position -= 15
            p.drawString(100, y_position, f"Email: {user.email}")
            y_position -= 15
            p.drawString(100, y_position, f"Company: {user.company_name or 'Not specified'}")
            
            p.save()
            buffer.seek(0)
            return buffer.getvalue()
            
        except Exception as e:
            print(f"Even fallback PDF generation failed: {e}")
            # Return minimal PDF content
            buffer = BytesIO()
            buffer.write(b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n")
            buffer.seek(0)
            return buffer.getvalue()

# Global instance
pdf_service = PDFService()
