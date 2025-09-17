import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Any, Optional
from app.config import settings
from app.models.user import User
from app.models.journalist import Journalist
from app.models.pitch import Pitch
from app.models.interaction import Interaction, InteractionType, EmailData
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
            message['From'] = f"AI PR Platform <{self.smtp_user}>"
            message['To'] = to_email

            # Add text content
            text_part = MIMEText(text_content, 'plain')
            message.attach(text_part)

            # Add HTML content
            html_part = MIMEText(html_content, 'html')
            message.attach(html_part)

            # Send via existing SMTP method
            await self._send_smtp_email(message, to_email)
            return True
            
        except Exception as e:
            print(f"Email sending failed: {str(e)}")
            return False

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
    
    async def _send_single_email(
        self,
        pitch: Pitch,
        journalist: Journalist,
        current_user: User,
        custom_subject: Optional[str] = None,
        custom_message: Optional[str] = None
    ) -> bool:
        """Send email to single journalist"""
        
        try:
            # Personalize content
            subject = custom_subject or pitch.content.email_pitch.subject
            body = custom_message or pitch.content.email_pitch.body
            
            # Replace placeholders
            personalized_subject = self._personalize_content(subject, journalist, current_user)
            personalized_body = self._personalize_content(body, journalist, current_user)
            
            # Create email message
            message = MIMEMultipart("alternative")
            message["Subject"] = personalized_subject
            message["From"] = f"{current_user.full_name} <{self.smtp_user}>"
            message["To"] = journalist.email
            
            # Add text content
            text_part = MIMEText(personalized_body, "plain")
            message.attach(text_part)
            
            # Generate unique message ID for tracking
            message_id = f"<{uuid.uuid4()}@{self.smtp_host}>"
            message["Message-ID"] = message_id
            
            # Send email
            await self._send_smtp_email(message, journalist.email)
            
            # Record interaction
            await self._record_email_interaction(
                user_id=str(current_user.id),
                journalist_id=str(journalist.id),
                pitch_id=str(pitch.id),
                subject=personalized_subject,
                content=personalized_body,
                message_id=message_id
            )
            
            return True
            
        except Exception as e:
            print(f"Failed to send email to {journalist.email}: {e}")
            return False
    
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


# Global email service instance
email_service = EmailService()
