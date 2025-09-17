from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import HTTPBearer
from datetime import datetime, timedelta
from app.models.user import User, UserCreate, UserLogin, UserResponse, Token
from app.utils.auth import (
    get_password_hash, 
    authenticate_user, 
    create_access_token,
    get_user_by_email,
    verify_password
)
from app.utils.dependencies import get_current_active_user
from app.config import settings


router = APIRouter()
security = HTTPBearer()


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register_user(user_data: UserCreate):
    """Register a new user"""
    print("=== BACKEND REGISTRATION DEBUG ===")
    print(f"Received email: {user_data.email}")
    print(f"Received password (raw): {user_data.password}")
    
    # Check if user already exists
    existing_user = await get_user_by_email(user_data.email)
    if existing_user:
        print(f"User already exists: {existing_user.email}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user with pending status (email verification required)
    hashed_password = get_password_hash(user_data.password)
    print(f"Generated hash: {hashed_password}")
    
    user = User(
        email=user_data.email,
        password_hash=hashed_password,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        company_name=user_data.company_name,
        status="pending",  # Set to pending until email verification
        email_verified=False,  # Add this field
    )
    
    await user.create()
    print(f"User created in database with ID: {user.id}")

    # Create access token
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.email}, 
        expires_delta=access_token_expires
    )

    print(f"Token created: {access_token[:50]}...")
    
    # Prepare user response
    user_response = UserResponse(
        id=str(user.id),
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        company_name=user.company_name,
        role=user.role,
        plan=user.plan,
        credits_remaining=user.credits_remaining,
        preferences=user.preferences,
        created_at=user.created_at,
        last_login=user.last_login,
        status=user.status,
        email_verified=user.email_verified  # Include in response
    )
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60,  # Convert to seconds
        user=user_response
    )

"""
@router.post("/login", response_model=Token)
async def login_user(user_credentials: UserLogin):
    #Login user and return access token

    
    
    # Updated to allow both active and pending users to login
    # (they can login but should be prompted to verify email)
    user = await User.find_one(User.email == user_credentials.email)
    if not user or not verify_password(user_credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if account is suspended
    if user.status == "inactive":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is suspended. Please contact support."
        )
    
    # Update last login
    user.last_login = datetime.utcnow()
    await user.save()
    
    # Create access token
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.email}, 
        expires_delta=access_token_expires
    )
    
    # Prepare user response
    user_response = UserResponse(
        id=str(user.id),
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        company_name=user.company_name,
        role=user.role,
        plan=user.plan,
        credits_remaining=user.credits_remaining,
        preferences=user.preferences,
        created_at=user.created_at,
        last_login=user.last_login,
        status=user.status,
        email_verified=user.email_verified  # Include in response
    )
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60,
        user=user_response
    )
"""

@router.post("/login", response_model=Token)
async def login_user(user_credentials: UserLogin):
    """Login user and return access token"""

    print("=== BACKEND LOGIN DEBUG ===")
    print(f"Login attempt for: {user_credentials.email}")
    print(f"Password provided: {user_credentials.password}")
    
    # First, check if user exists
    user = await User.find_one(User.email == user_credentials.email)
    if not user:
        print("❌ User not found in database")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    print(f"✅ User found: {user.email}")
    print(f"Stored hash: {user.password_hash}")
    print(f"User status: {user.status}")
    print(f"Email verified: {user.email_verified}")
    
    # Now verify password
    password_match = verify_password(user_credentials.password, user.password_hash)
    print(f"Password verification result: {password_match}")
    
    if not password_match:
        print("❌ Password verification failed")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    print("✅ Password verified successfully")
    
    # Check if account is suspended
    if user.status == "inactive":
        print("❌ Account is suspended")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is suspended. Please contact support."
        )
    
    print("✅ Account status check passed")
    
    # Update last login
    user.last_login = datetime.utcnow()
    await user.save()
    
    # Create access token
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.email}, 
        expires_delta=access_token_expires
    )
    
    print(f"✅ Login successful, token created")
    
    # Prepare user response
    user_response = UserResponse(
        id=str(user.id),
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        company_name=user.company_name,
        role=user.role,
        plan=user.plan,
        credits_remaining=user.credits_remaining,
        preferences=user.preferences,
        created_at=user.created_at,
        last_login=user.last_login,
        status=user.status,
        email_verified=user.email_verified
    )
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60,
        user=user_response
    )



@router.get("/profile", response_model=UserResponse)
async def get_user_profile(current_user: User = Depends(get_current_active_user)):
    """Get current user's profile"""
    
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        company_name=current_user.company_name,
        role=current_user.role,
        plan=current_user.plan,
        credits_remaining=current_user.credits_remaining,
        preferences=current_user.preferences,
        created_at=current_user.created_at,
        last_login=current_user.last_login,
        status=current_user.status,
        email_verified=current_user.email_verified  # Include in response
    )


@router.post("/logout")
async def logout_user(current_user: User = Depends(get_current_active_user)):
    """Logout user (client should discard token)"""
    return {"message": "Successfully logged out"}


# In your backend, add a debug endpoint temporarily
@router.get("/debug/user/{email}")
async def debug_user(email: str):
    user = await User.find_one(User.email == email)
    if user:
        return {
            "email": user.email,
            "password_hash": user.password_hash,
            "status": user.status,
            "email_verified": user.email_verified,
            "created_via": "frontend" if hasattr(user, 'created_via') else "unknown"
        }
    return {"error": "User not found"}
