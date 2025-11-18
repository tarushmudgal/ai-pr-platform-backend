import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Any, Optional
from app.config import settings
from app.models.user import User
from app.models.journalist import Journalist
from app.models.pitch import Pitch
from app.models.interaction import Interaction, InteractionType, EmailData
from email.mime.application import MIMEApplication 
from fastapi import HTTPException, status
import uuid
import re
import random
import string


class EmailService:
    
    def __init__(self):
        self.smtp_host = settings.smtp_host
        self.smtp_port = settings.smtp_port
        self.smtp_user = settings.smtp_user
        self.smtp_password = settings.smtp_password
    
    def generate_otp(self, length: int = 6) -> str:
        """Generate a random OTP"""
        return ''.join(random.choices(string.digits, k=length))
    
    async def send_verification_email(self, user_email: str, user_name: str, otp: str) -> bool:
        """Send email verification OTP"""
        try:
            subject = "Verify Your Email - AI PR Platform"
            
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Email Verification</title>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; margin: 0; padding: 0; background-color: #f4f4f4; }}
                    .container {{ max-width: 600px; margin: 0 auto; background-color: #ffffff; }}
                    .header {{ background-color: #2563eb; color: white; padding: 30px; text-align: center; }}
                    .content {{ padding: 30px; }}
                    .otp-code {{ background-color: #f8f9fa; border: 2px dashed #2563eb; padding: 25px; text-align: center; margin: 25px 0; border-radius: 8px; }}
                    .otp-number {{ font-size: 36px; font-weight: bold; color: #2563eb; letter-spacing: 8px; font-family: monospace; }}
                    .footer {{ background-color: #f8f9fa; padding: 20px; text-align: center; color: #6b7280; font-size: 14px; }}
                    .button {{ background-color: #2563eb; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; display: inline-block; margin: 15px 0; }}
                    .warning {{ background-color: #fef3c7; border-left: 4px solid #f59e0b; padding: 15px; margin: 20px 0; border-radius: 4px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1 style="margin: 0;">🚀 AI-Powered PR Platform</h1>
                        <h2 style="margin: 10px 0 0 0; font-weight: normal;">Email Verification</h2>
                    </div>
                    <div class="content">
                        <p>Hello <strong>{user_name}</strong>,</p>
                        <p>Welcome to the AI-Powered PR Platform! To complete your registration and start generating professional PR content, please verify your email address using the code below:</p>
                        
                        <div class="otp-code">
                            <p style="margin: 0 0 10px 0; font-size: 16px; color: #374151;">Your verification code is:</p>
                            <div class="otp-number">{otp}</div>
                        </div>
                        
                        <div class="warning">
                            <p style="margin: 0; font-size: 14px;"><strong>⏰ Important:</strong></p>
                            <ul style="margin: 10px 0 0 0; padding-left: 20px; font-size: 14px;">
                                <li>This code is valid for 10 minutes only</li>
                                <li>Enter this code in the verification screen to activate your account</li>
                                <li>If you didn't request this, please ignore this email</li>
                            </ul>
                        </div>
                        
                        <p><strong>🎯 What's next after verification?</strong></p>
                        <ul>
                            <li>✨ Generate professional press releases with AI</li>
                            <li>📧 Create personalized email pitches automatically</li>
                            <li>👥 Manage your journalist database efficiently</li>
                            <li>📊 Track campaign performance and analytics</li>
                        </ul>
                        
                        <p>Questions? We're here to help! Contact us at <a href="mailto:support@prplatform.com" style="color: #2563eb;">support@prplatform.com</a></p>
                    </div>
                    <div class="footer">
                        <p style="margin: 0;"><strong>AI-Powered PR Platform</strong></p>
                        <p style="margin: 5px 0 0 0;">Making PR Simple with Artificial Intelligence</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            text_content = f"""
            AI-Powered PR Platform - Email Verification
            
            Hello {user_name},
            
            Welcome! Please verify your email address to complete registration.
            
            Your verification code: {otp}
            
            This code is valid for 10 minutes.
            
            If you didn't request this, please ignore this email.
            
            Questions? Contact us at support@prplatform.com
            """

            return await self._send_email(user_email, subject, html_content, text_content)
            
        except Exception as e:
            print(f"Failed to send verification email: {e}")
            return False

    async def send_password_reset_email(self, user_email: str, user_name: str, reset_code: str) -> bool:
        """Send password reset OTP"""
        try:
            subject = "Reset Your Password - AI PR Platform"
            
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Password Reset</title>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; margin: 0; padding: 0; background-color: #f4f4f4; }}
                    .container {{ max-width: 600px; margin: 0 auto; background-color: #ffffff; }}
                    .header {{ background-color: #dc2626; color: white; padding: 30px; text-align: center; }}
                    .content {{ padding: 30px; }}
                    .otp-code {{ background-color: #fef2f2; border: 2px dashed #dc2626; padding: 25px; text-align: center; margin: 25px 0; border-radius: 8px; }}
                    .otp-number {{ font-size: 36px; font-weight: bold; color: #dc2626; letter-spacing: 8px; font-family: monospace; }}
                    .footer {{ background-color: #f8f9fa; padding: 20px; text-align: center; color: #6b7280; font-size: 14px; }}
                    .warning {{ background-color: #fef3c7; border-left: 4px solid #f59e0b; padding: 15px; margin: 20px 0; border-radius: 4px; }}
                    .security {{ background-color: #fef2f2; border-left: 4px solid #dc2626; padding: 15px; margin: 20px 0; border-radius: 4px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1 style="margin: 0;">🔒 AI-Powered PR Platform</h1>
                        <h2 style="margin: 10px 0 0 0; font-weight: normal;">Password Reset Request</h2>
                    </div>
                    <div class="content">
                        <p>Hello <strong>{user_name}</strong>,</p>
                        <p>We received a request to reset your password for your AI PR Platform account. Use the code below to set a new password:</p>
                        
                        <div class="otp-code">
                            <p style="margin: 0 0 10px 0; font-size: 16px; color: #374151;">Your password reset code is:</p>
                            <div class="otp-number">{reset_code}</div>
                        </div>
                        
                        <div class="security">
                            <p style="margin: 0; font-size: 14px;"><strong>🔐 Security Notice:</strong></p>
                            <ul style="margin: 10px 0 0 0; padding-left: 20px; font-size: 14px;">
                                <li>This code is valid for 15 minutes only</li>
                                <li>Use this code to set a new secure password</li>
                                <li>If you didn't request this reset, please ignore this email</li>
                                <li>Never share this code with anyone</li>
                            </ul>
                        </div>
                        
                        <div class="warning">
                            <p style="margin: 0; font-size: 14px;"><strong>⚠️ Didn't request this?</strong></p>
                            <p style="margin: 5px 0 0 0; font-size: 14px;">If you didn't request a password reset, your account is still secure. Someone may have entered your email address by mistake.</p>
                        </div>
                        
                        <p>If you continue to have problems accessing your account, please contact our support team at <a href="mailto:support@prplatform.com" style="color: #dc2626;">support@prplatform.com</a></p>
                    </div>
                    <div class="footer">
                        <p style="margin: 0;"><strong>AI-Powered PR Platform</strong></p>
                        <p style="margin: 5px 0 0 0;">Making PR Simple with Artificial Intelligence</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            text_content = f"""
            AI-Powered PR Platform - Password Reset
            
            Hello {user_name},
            
            We received a request to reset your password.
            
            Your password reset code: {reset_code}
            
            This code is valid for 15 minutes.
            
            If you didn't request this, please ignore this email.
            
            Questions? Contact us at support@prplatform.com
            """

            return await self._send_email(user_email, subject, html_content, text_content)
            
        except Exception as e:
            print(f"Failed to send password reset email: {e}")
            return False

    async def _send_email(self, to_email: str, subject: str, html_content: str, text_content: str) -> bool:
        """Send email using SMTP"""
        try:
            # Create message
            message = MIMEMultipart('alternative')
            message['Subject'] = subject
            message['From'] = f"Redfern & Chase <{self.smtp_user}>"
            message['To'] = to_email

            # Add text content
            #text_part = MIMEText(text_content, 'plain')
            #message.attach(text_part)

            # Add HTML content
            html_part = MIMEText(html_content, 'html')
            message.attach(html_part)

            # Send via existing SMTP method
            await self._send_smtp_email(message, to_email)
            return True
            
        except Exception as e:
            print(f"Email sending failed: {str(e)}")
            return False
    """
    async def send_pitch_to_journalists(
        self, 
        pitch: Pitch,
        journalist_ids: List[str], 
        current_user: User,
        custom_subject: Optional[str] = None,
        custom_message: Optional[str] = None
    ) -> Dict[str, Any]:
        Send pitch to multiple journalists
        
        results = {
            "sent": [],
            "failed": [],
            "total_sent": 0,
            "total_failed": 0
        }
        
        for journalist_id in journalist_ids:
            try:
                # Get journalist
                journalist = await Journalist.get(journalist_id)
                if not journalist or journalist.added_by_user_id != str(current_user.id):
                    results["failed"].append({
                        "journalist_id": journalist_id,
                        "error": "Journalist not found or not accessible"
                    })
                    continue
                
                # Send email
                success = await self._send_single_email(
                    pitch=pitch,
                    journalist=journalist,
                    current_user=current_user,
                    custom_subject=custom_subject,
                    custom_message=custom_message
                )
                
                if success:
                    results["sent"].append({
                        "journalist_id": journalist_id,
                        "journalist_name": journalist.name,
                        "journalist_email": journalist.email
                    })
                    results["total_sent"] += 1
                    
                    # Update pitch performance
                    pitch.record_email_sent(1)
                    
                    # Update journalist stats
                    journalist.record_email_sent()
                    await journalist.save()
                    
                else:
                    results["failed"].append({
                        "journalist_id": journalist_id,
                        "error": "Email sending failed"
                    })
                    results["total_failed"] += 1
                    
            except Exception as e:
                results["failed"].append({
                    "journalist_id": journalist_id,
                    "error": str(e)
                })
                results["total_failed"] += 1
        
        # Update pitch status and save
        if results["total_sent"] > 0:
            pitch.mark_as_sent()
        
        await pitch.save()
        
        return results
    """
    async def _send_single_email(
        self,
        pitch: Pitch,
        journalist: Journalist,
        current_user: User,
        custom_subject: Optional[str] = None,
        custom_message: Optional[str] = None
    ) -> bool:
        """Send email to single journalist with branding and PDF attachment"""
        
        try:
            # Personalize content
            subject = custom_subject or pitch.content.email_pitch.subject
            body = custom_message or pitch.content.email_pitch.body
            
            # Replace placeholders
            personalized_subject = self._personalize_content(subject, journalist, current_user)
            personalized_body = self._personalize_content(body, journalist, current_user)
            
            # Create branded HTML email
            html_body = self._create_branded_email(personalized_body, current_user, pitch)
            
            # Create multipart message
            message = MIMEMultipart()
            message["Subject"] = personalized_subject
#            message["From"] = f"{current_user.full_name} <{self.smtp_user}>"
            message["From"] = f"Redfern & Chase - PR Alert <{self.smtp_user}>"
            message["To"] = journalist.email
            message["Message-ID"] = f"<{uuid.uuid4()}@{self.smtp_host}>"
            
            # Add HTML content
            html_part = MIMEText(html_body, "html")
            message.attach(html_part)
            
            # Add plain text version
            #text_part = MIMEText(personalized_body, "plain")
            #message.attach(text_part)
            
            # Generate PDF and attach
            try:
                from app.services.pdf_service import pdf_service
                pdf_content = pdf_service.generate_press_release_pdf(pitch, current_user) 
            #    pdf_content = self._generate_press_release_pdf(pitch, current_user)
                pdf_attachment = MIMEApplication(pdf_content, _subtype='pdf')
                pdf_attachment.add_header(
                    'Content-Disposition', 
                    'attachment', 
                    filename=f"{pitch.company_name.replace(' ', '_')}_Press_Release.pdf"
                )
                message.attach(pdf_attachment)
                print(f"✅ PDF attachment added for {journalist.email}")
            except Exception as e:
                print(f"⚠️ Failed to attach PDF: {e}")
                # Continue without PDF if generation fails
            
            # Send email
            await self._send_smtp_email(message, journalist.email)
            
            # Record interaction
            await self._record_email_interaction(
                user_id=str(current_user.id),
                journalist_id=str(journalist.id),
                pitch_id=str(pitch.id),
                subject=personalized_subject,
                content=personalized_body,
                message_id=message["Message-ID"]
            )
            
            return True
            
        except Exception as e:
            print(f"Failed to send email to {journalist.email}: {e}")
            return False

    def _create_branded_email(self, body: str, user: User, pitch: Pitch) -> str:
        """Create branded HTML email template"""
        
        # Convert plain text to HTML
        html_body = body.replace('\n', '<br>')
        
        # Get company branding
        company_name = user.company_name or "Your Company"
        platform_name = "AI PR Platform"
        
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Press Release from {company_name}</title>
    <style>
        body {{ 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            line-height: 1.6; 
            color: #333; 
            margin: 0; 
            padding: 0; 
            background-color: #f8f9fa;
        }}
        .container {{ 
            max-width: 650px; 
            margin: 0 auto; 
            background: #ffffff; 
            box-shadow: 0 0 20px rgba(0,0,0,0.1);
        }}
        .header {{ 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
            color: white; 
            padding: 40px 30px; 
            text-align: center; 
        }}
        .logo {{ 
            font-size: 28px; 
            font-weight: bold; 
            margin-bottom: 8px; 
        }}
        .tagline {{ 
            font-size: 14px; 
            opacity: 0.9; 
            margin: 0;
        }}
        .content {{ 
            padding: 40px 30px; 
            background: #ffffff;
        }}
        .company-info {{
            background: #f8f9ff;
            border-left: 4px solid #667eea;
            padding: 20px;
            margin: 30px 0;
            border-radius: 0 8px 8px 0;
        }}
        .attachment-notice {{
            background: linear-gradient(90deg, #e3f2fd 0%, #f3e5f5 100%);
            border: 1px solid #e1bee7;
            padding: 20px;
            margin: 30px 0;
            border-radius: 8px;
            text-align: center;
        }}
        .attachment-icon {{
            font-size: 24px;
            margin-bottom: 10px;
        }}
        .footer {{ 
            background: #f8f9fa; 
            padding: 30px; 
            text-align: center; 
            border-top: 1px solid #e9ecef; 
        }}
        .footer-logo {{
            color: #667eea;
            font-weight: bold;
            font-size: 16px;
            margin-bottom: 8px;
        }}
        .footer-text {{
            color: #6c757d;
            font-size: 12px;
            margin: 5px 0;
        }}
        .social-links a {{
            color: #667eea;
            text-decoration: none;
            margin: 0 10px;
            font-size: 12px;
        }}
        .cta-button {{
            background: #667eea;
            color: white;
            padding: 12px 24px;
            text-decoration: none;
            border-radius: 6px;
            display: inline-block;
            margin: 20px 0;
            font-weight: 500;
        }}
        @media (max-width: 600px) {{
            .container {{ margin: 0 10px; }}
            .header, .content, .footer {{ padding: 20px !important; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <div class="header">
            <div class="logo"> {company_name}</div>
            <p class="tagline">Press Release & Media Kit</p>
        </div>
        
        <!-- Main Content -->
        <div class="content">
            {html_body}
            
            <!-- Company Info Box -->
            <div class="company-info">
                <h3 style="margin: 0 0 10px 0; color: #667eea;">📋 About {company_name}</h3>
                <p style="margin: 0; font-size: 14px; color: #6c757d;">
                    This press release was created by {company_name} using Redfern & Chase PR Agent. 
                    For more information about {company_name}, please see the attached press release.
                </p>
            </div>
            
            <!-- PDF Attachment Notice -->
            <div class="attachment-notice">
                <h3 style="margin: 0 0 10px 0; color: #333;">Complete Press Release Attached</h3>
                <p style="margin: 0; color: #666; font-size: 14px;">
                    Please find the full press release attached as a PDF document for your reference and potential publication.
                </p>
            </div>
            
            <!-- Contact Info -->
            <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #e9ecef;">
                <h4 style="color: #667eea; margin-bottom: 10px;">📞 Media Contact</h4>
                <p style="margin: 5px 0; font-size: 14px;"><strong>Name:</strong> {user.full_name}</p>
                <p style="margin: 5px 0; font-size: 14px;"><strong>Company:</strong> {company_name}</p>
                <p style="margin: 5px 0; font-size: 14px;"><strong>Email:</strong> {user.email}</p>
            </div>
        </div>
        
        <!-- Footer -->
        <div class="footer">
            <div class="footer-logo">{platform_name}</div>
            <p class="footer-text">Making PR Simple with Artificial Intelligence</p>
            <p class="footer-text">
                This email was sent using {platform_name} - 
                <a href="https://yourplatform.com" style="color: #667eea;">Learn more about our AI PR solutions</a>
            </p>
            <div style="margin-top: 15px;">
                <a href="https://yourplatform.com" style="color: #667eea; text-decoration: none; margin: 0 8px; font-size: 11px;">Website</a> •
                <a href="mailto:support@yourplatform.com" style="color: #667eea; text-decoration: none; margin: 0 8px; font-size: 11px;">Support</a> •
                <a href="https://yourplatform.com/unsubscribe" style="color: #667eea; text-decoration: none; margin: 0 8px; font-size: 11px;">Unsubscribe</a>
            </div>
        </div>
    </div>
</body>
</html>"""

    def _generate_press_release_pdf(self, pitch: Pitch, user: User) -> bytes:
        """Generate PDF from pitch content using reportlab"""
        
        try:
            from reportlab.lib.pagesizes import letter, A4
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
            from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
            from reportlab.lib import colors
            from io import BytesIO
            import textwrap
            
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
                alignment=TA_JUSTIFY,
                leftIndent=0,
                rightIndent=0
            )
            
            # Build PDF content
            story = []
            
            # Header with branding
            story.append(Paragraph("🚀 AI PR PLATFORM", 
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
            story.append(Paragraph(pitch.headline, title_style))
            story.append(Spacer(1, 20))
            
            # Company & Date
            story.append(Paragraph(
                f"<b>{pitch.company_name}</b> | {pitch.created_at.strftime('%B %d, %Y')}", 
                body_style
            ))
            story.append(Spacer(1, 20))
            
            # Press Release Content
            # Clean and format the content
            content = pitch.content.press_release
            paragraphs = content.split('\n\n')
            
            for paragraph in paragraphs:
                if paragraph.strip():
                    story.append(Paragraph(paragraph.strip(), body_style))
                    story.append(Spacer(1, 12))
            
            story.append(Spacer(1, 30))
            
            # Separator line
            story.append(Paragraph("─" * 50, 
                ParagraphStyle('Separator', fontSize=10, alignment=TA_CENTER, textColor=colors.grey)
            ))
            story.append(Spacer(1, 20))
            
            # About Company (if available)
            if hasattr(pitch, 'company_description') and pitch.company_description:
                story.append(Paragraph(f"<b>About {pitch.company_name}</b>", header_style))
                story.append(Paragraph(pitch.company_description, body_style))
                story.append(Spacer(1, 20))
            
            # Contact Information
            story.append(Paragraph("<b>Media Contact Information</b>", header_style))
            story.append(Paragraph(f"<b>Contact Person:</b> {user.full_name}", body_style))
            story.append(Paragraph(f"<b>Company:</b> {user.company_name}", body_style))
            story.append(Paragraph(f"<b>Email:</b> {user.email}", body_style))
            story.append(Spacer(1, 30))
            
            # Footer
            story.append(Paragraph("###", 
                ParagraphStyle('End', fontSize=16, alignment=TA_CENTER, textColor=colors.grey)
            ))
            story.append(Spacer(1, 20))
            
            story.append(Paragraph(
                "This press release was generated using AI PR Platform - Making PR Simple with Artificial Intelligence", 
                ParagraphStyle('Footer', fontSize=8, textColor=colors.grey, alignment=TA_CENTER)
            ))
            
            # Build PDF
            doc.build(story)
            buffer.seek(0)
            return buffer.getvalue()
            
        except Exception as e:
            print(f"Error generating PDF: {e}")
            # Return a simple text-based PDF fallback
            return self._generate_simple_pdf_fallback(pitch, user)

    def _generate_simple_pdf_fallback(self, pitch: Pitch, user: User) -> bytes:
        """Simple fallback PDF generation"""
        from reportlab.pdfgen import canvas
        from io import BytesIO
        
        buffer = BytesIO()
        p = canvas.Canvas(buffer)
        
        # Simple text-based PDF
        p.drawString(100, 750, f"PRESS RELEASE - {pitch.company_name}")
        p.drawString(100, 720, f"Date: {pitch.created_at.strftime('%B %d, %Y')}")
        p.drawString(100, 690, f"Headline: {pitch.headline}")
        
        # Add content (simplified)
        y_position = 650
        content_lines = pitch.content.press_release.split('\n')
        for line in content_lines[:20]:  # Limit lines for simple version
            if y_position > 100:
                p.drawString(100, y_position, line[:80])  # Limit line length
                y_position -= 20
        
        # Contact info
        p.drawString(100, y_position - 40, f"Contact: {user.full_name}")
        p.drawString(100, y_position - 60, f"Email: {user.email}")
        
        p.save()
        buffer.seek(0)
        return buffer.getvalue()
    
    async def _send_smtp_email(self, message: MIMEMultipart, to_email: str):
        """Send email via SMTP"""
        
        if not all([self.smtp_host, self.smtp_user, self.smtp_password]):
            # For development - just print the email content
            print(f"\n=== EMAIL WOULD BE SENT TO: {to_email} ===")
            print(f"Subject: {message['Subject']}")
            print(f"From: {message['From']}")
            print("Content:")
            for part in message.walk():
                if part.get_content_type() == "text/plain":
                    print(part.get_payload())
                    break
            print("=== END EMAIL ===\n")
            return
        
        try:
            # Connect and send
            async with aiosmtplib.SMTP(
                hostname=self.smtp_host,
                port=self.smtp_port,
                start_tls=True
            ) as server:
                await server.login(self.smtp_user, self.smtp_password)
                await server.send_message(message)
                
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to send email: {str(e)}"
            )
    
    def _personalize_content(self, content: str, journalist: Journalist, user: User) -> str:
        """Replace placeholders with actual values"""
        
        # Replace journalist placeholders
        content = content.replace("{journalist_name}", journalist.name)
        content = content.replace("{publication}", journalist.publication)
        
        # Replace user placeholders
        content = content.replace("{sender_name}", user.full_name)
        content = content.replace("{company_name}", user.company_name)
        
        # Add email signature if configured
        if user.preferences.email_signature:
            if not content.endswith('\n'):
                content += '\n'
            content += f"\n{user.preferences.email_signature}"
        
        return content
    
    async def _record_email_interaction(
        self,
        user_id: str,
        journalist_id: str,
        pitch_id: str,
        subject: str,
        content: str,
        message_id: str
    ):
        """Record email interaction in database"""
        
        email_data = EmailData(
            subject=subject,
            content=content,
            sent_via="smtp",
            message_id=message_id
        )
        
        interaction = Interaction(
            user_id=user_id,
            journalist_id=journalist_id,
            pitch_id=pitch_id,
            type=InteractionType.EMAIL_SENT,
            email_data=email_data
        )
        
        await interaction.create()
    
    async def get_user_interactions(
        self,
        user_id: str,
        limit: int = 20,
        skip: int = 0
    ) -> Dict[str, Any]:
        """Get user's email interactions"""
        
        interactions = await Interaction.find(
            Interaction.user_id == user_id
        ).sort(-Interaction.interaction_date).skip(skip).limit(limit).to_list()
        
        total_count = await Interaction.find(Interaction.user_id == user_id).count()
        
        # Enrich with journalist and pitch details
        enriched_interactions = []
        
        for interaction in interactions:
            # Get journalist details
            journalist = await Journalist.get(interaction.journalist_id)
            journalist_info = {
                "id": str(journalist.id),
                "name": journalist.name,
                "email": journalist.email,
                "publication": journalist.publication
            } if journalist else None
            
            # Get pitch details
            pitch_info = None
            if interaction.pitch_id:
                pitch = await Pitch.get(interaction.pitch_id)
                pitch_info = {
                    "id": str(pitch.id),
                    "headline": pitch.headline,
                    "company_name": pitch.company_name
                } if pitch else None
            
            enriched_interactions.append({
                "id": str(interaction.id),
                "type": interaction.type,
                "status": interaction.status,
                "email_data": interaction.email_data,
                "journalist": journalist_info,
                "pitch": pitch_info,
                "response_received": interaction.response_received,
                "interaction_date": interaction.interaction_date,
                "response_date": interaction.response_date,
                "notes": interaction.notes
            })
        
        return {
            "interactions": enriched_interactions,
            "total": total_count,
            "page": skip // limit + 1,
            "pages": (total_count + limit - 1) // limit,
            "has_next": skip + limit < total_count
        }
    
    async def send_campaign(self, campaign_data: Dict[str, Any], user: User) -> Dict[str, Any]:
        """Send email campaign - method for chatbot integration"""
        try:
            # Get the pitch
            pitch_id = campaign_data.get("pitch_id")
            if not pitch_id:
                raise Exception("Pitch ID is required")
            
            from beanie import PydanticObjectId
            try:
                pitch_obj_id = PydanticObjectId(pitch_id)
                pitch = await Pitch.get(pitch_obj_id)
            except:
                raise Exception("Invalid pitch ID")
            
            if not pitch or pitch.user_id != str(user.id):
                raise Exception("Pitch not found or not accessible")
            
            # Get journalist IDs
            journalist_ids = campaign_data.get("journalist_ids", [])
            if not journalist_ids:
                raise Exception("At least one journalist ID is required")
            
            # Convert string IDs to PydanticObjectId
            valid_journalist_ids = []
            for jid in journalist_ids:
                try:
                    valid_journalist_ids.append(PydanticObjectId(jid))
                except:
                    continue
            
            if not valid_journalist_ids:
                raise Exception("No valid journalist IDs provided")
            
            # Send emails using existing method
            results = await self.send_pitch_to_journalists(
                pitch=pitch,
                journalist_ids=[str(jid) for jid in valid_journalist_ids],
                current_user=user,
                custom_subject=campaign_data.get("custom_subject"),
                custom_message=campaign_data.get("custom_message")
            )
            
            return results
            
        except Exception as e:
            raise Exception(f"Campaign sending failed: {str(e)}")
        
    # Update the send_pitch_to_journalists method in your EmailService class

    async def send_pitch_to_journalists(
        self, 
        pitch: Pitch,
        journalist_ids: List[str], 
        current_user: User,
        custom_subject: Optional[str] = None,
        custom_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send pitch to multiple journalists"""
        
        results = {
            "sent": [],
            "failed": [],
            "total_sent": 0,
            "total_failed": 0
        }
        
        for journalist_id in journalist_ids:
            try:
                # Get journalist
                from beanie import PydanticObjectId
                try:
                    journalist_obj_id = PydanticObjectId(journalist_id)
                    journalist = await Journalist.get(journalist_obj_id)
                except:
                    results["failed"].append({
                        "journalist_id": journalist_id,
                        "error": "Invalid journalist ID"
                    })
                    continue
                
                # Check if journalist exists and belongs to user
                if not journalist or journalist.added_by_user_id != str(current_user.id):  # Fix: use added_by instead of added_by_user_id
                    results["failed"].append({
                        "journalist_id": journalist_id,
                        "error": "Journalist not found or not accessible"
                    })
                    continue
                
                # Send email
                success = await self._send_single_email(
                    pitch=pitch,
                    journalist=journalist,
                    current_user=current_user,
                    custom_subject=custom_subject,
                    custom_message=custom_message
                )
                
                if success:
                    results["sent"].append({
                        "journalist_id": journalist_id,
                        "journalist_name": journalist.name,
                        "journalist_email": journalist.email
                    })
                    results["total_sent"] += 1
                    
                    # Update pitch performance
                    pitch.record_email_sent(1)
                    
                    # Update journalist stats - check if method exists
                    if hasattr(journalist, 'record_email_sent'):
                        journalist.record_email_sent()
                        await journalist.save()
                    
                else:
                    results["failed"].append({
                        "journalist_id": journalist_id,
                        "error": "Email sending failed"
                    })
                    results["total_failed"] += 1
                    
            except Exception as e:
                results["failed"].append({
                    "journalist_id": journalist_id,
                    "error": str(e)
                })
                results["total_failed"] += 1
        
        # Update pitch status and save
        if results["total_sent"] > 0:
            if hasattr(pitch, 'mark_as_sent'):
                pitch.mark_as_sent()
        
        await pitch.save()
        
        return results



# Global email service instance
email_service = EmailService()
