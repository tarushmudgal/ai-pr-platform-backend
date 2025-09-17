from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime, timedelta
from app.models.user import User
from app.utils.dependencies import get_current_active_user
from app.services.email_service import email_service
from app.utils.auth import verify_password, get_password_hash

router = APIRouter()

# Request Models
class ProfileUpdateRequest(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)
    company_name: str = Field(..., min_length=1, max_length=100)

class PreferencesUpdateRequest(BaseModel):
    default_tone: str
    email_signature: str = ""

class EmailVerificationRequest(BaseModel):
    email: EmailStr

class VerifyEmailRequest(BaseModel):
    email: EmailStr
    otp: str = Field(..., min_length=6, max_length=6)

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    email: EmailStr
    reset_code: str = Field(..., min_length=6, max_length=6)
    new_password: str = Field(..., min_length=6, max_length=100)

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=6, max_length=100)


@router.put("/update")
async def update_profile(
    profile_data: ProfileUpdateRequest,
    current_user: User = Depends(get_current_active_user)
):
    """
    Update user profile information
    
    Updates: first_name, last_name, company_name
    """
    
    try:
        current_user.first_name = profile_data.first_name
        current_user.last_name = profile_data.last_name
        current_user.company_name = profile_data.company_name
        current_user.updated_at = datetime.utcnow()
        
        await current_user.save()
        
        return {
            "message": "Profile updated successfully",
            "user": {
                "id": str(current_user.id),
                "email": current_user.email,
                "first_name": current_user.first_name,
                "last_name": current_user.last_name,
                "company_name": current_user.company_name,
                "role": current_user.role,
                "plan": current_user.plan,
                "status": current_user.status,
                "credits_remaining": current_user.credits_remaining,
                "preferences": current_user.preferences.dict(),
                "created_at": current_user.created_at.isoformat(),
                "last_login": current_user.last_login.isoformat() if current_user.last_login else None,
                "email_verified": current_user.email_verified,
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update profile: {str(e)}"
        )


@router.put("/preferences")
async def update_preferences(
    preferences_data: PreferencesUpdateRequest,
    current_user: User = Depends(get_current_active_user)
):
    """
    Update user AI and email preferences
    
    Updates: default_tone, email_signature
    """
    
    try:
        current_user.preferences.default_tone = preferences_data.default_tone
        current_user.preferences.email_signature = preferences_data.email_signature
        current_user.updated_at = datetime.utcnow()
        
        await current_user.save()
        
        return {
            "message": "Preferences updated successfully",
            "preferences": current_user.preferences.dict()
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update preferences: {str(e)}"
        )


@router.post("/send-verification")
async def send_verification_email(request: EmailVerificationRequest):
    """
    Send 6-digit OTP for email verification
    
    - Generates and sends OTP to user's email
    - OTP expires in 10 minutes
    - Returns success message and expiry time
    """
    
    user = await User.find_one(User.email == request.email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is already verified"
        )
    
    try:
        # Generate 6-digit OTP
        otp = email_service.generate_otp(6)
        
        # Save OTP to user (expires in 10 minutes)
        user.verification_code = otp
        user.verification_code_expires = datetime.utcnow() + timedelta(minutes=10)
        await user.save()
        
        # Send email
        email_sent = await email_service.send_verification_email(
            user_email=user.email,
            user_name=user.full_name,
            otp=otp
        )
        
        return {
            "message": "Verification email sent successfully",
            "expires_in": 600,  # 10 minutes in seconds
            # Remove this in production:
            "debug_otp": otp  # For testing purposes
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send verification email: {str(e)}"
        )


@router.post("/verify-email")
async def verify_email(request: VerifyEmailRequest):
    """
    Verify email with 6-digit OTP
    
    - Validates OTP against stored code
    - Checks expiry time (10 minutes)
    - Activates user account on success
    """
    
    user = await User.find_one(User.email == request.email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if user.email_verified:
        return {"message": "Email is already verified"}
    
    # Check if OTP exists and is valid
    if not user.verification_code or not user.verification_code_expires:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No verification code found. Please request a new one."
        )
    
    # Check if OTP is expired
    if datetime.utcnow() > user.verification_code_expires:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification code has expired. Please request a new one."
        )
    
    # Check if OTP matches
    if user.verification_code != request.otp:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code"
        )
    
    try:
        # Mark email as verified
        user.email_verified = True
        user.status = "active"
        user.verification_code = None
        user.verification_code_expires = None
        user.updated_at = datetime.utcnow()
        
        await user.save()
        
        return {
            "message": "Email verified successfully",
            "user": {
                "id": str(user.id),
                "email": user.email,
                "email_verified": user.email_verified,
                "status": user.status
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to verify email: {str(e)}"
        )


@router.post("/forgot-password")
async def forgot_password(request: ForgotPasswordRequest):
    """
    Send 6-digit OTP for password reset
    
    - Generates and sends reset code to user's email
    - Code expires in 15 minutes
    - Returns generic message for security
    """
    
    user = await User.find_one(User.email == request.email)
    if not user:
        # Don't reveal that user doesn't exist for security
        return {
            "message": "If the email exists, a password reset code has been sent",
            # Remove this in production:
            "debug_code": "000000"  # For testing when user doesn't exist
        }
    
    try:
        # Generate 6-digit reset code
        reset_code = email_service.generate_otp(6)
        
        # Save reset code (expires in 15 minutes)
        user.reset_code = reset_code
        user.reset_code_expires = datetime.utcnow() + timedelta(minutes=15)
        await user.save()
        
        # Send email
        email_sent = await email_service.send_password_reset_email(
            user_email=user.email,
            user_name=user.full_name,
            reset_code=reset_code
        )
        
        return {
            "message": "If the email exists, a password reset code has been sent",
            "expires_in": 900,  # 15 minutes
            # Remove this in production:
            "debug_code": reset_code  # For testing purposes
        }
        
    except Exception as e:
        print(f"Password reset error: {str(e)}")
        return {
            "message": "If the email exists, a password reset code has been sent"
        }


@router.post("/reset-password")
async def reset_password(request: ResetPasswordRequest):
    """
    Reset password with 6-digit OTP
    
    - Validates reset code against stored code
    - Checks expiry time (15 minutes)
    - Updates password hash on success
    """
    
    user = await User.find_one(User.email == request.email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid reset code"
        )
    
    # Check reset code
    if not user.reset_code or not user.reset_code_expires:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset code"
        )
    
    if datetime.utcnow() > user.reset_code_expires:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset code has expired"
        )
    
    if user.reset_code != request.reset_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid reset code"
        )
    
    try:
        # Update password
        user.password_hash = get_password_hash(request.new_password)
        user.reset_code = None
        user.reset_code_expires = None
        user.updated_at = datetime.utcnow()
        
        await user.save()
        
        return {"message": "Password reset successfully"}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reset password"
        )


@router.post("/change-password")
async def change_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_active_user)
):
    """
    Change password for authenticated user
    
    - Requires current password verification
    - New password must be different from current
    - Updates password hash on success
    """
    
    # Verify current password
    if not verify_password(request.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Check if new password is same as current
    if verify_password(request.new_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from current password"
        )
    
    try:
        # Update password
        current_user.password_hash = get_password_hash(request.new_password)
        current_user.updated_at = datetime.utcnow()
        
        await current_user.save()
        
        return {"message": "Password changed successfully"}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to change password"
        )
