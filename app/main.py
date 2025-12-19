from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import settings
from app.database import connect_to_mongo, close_mongo_connection, is_database_connected
from app.routers import auth, journalists, pitches, emails, imports, profile, newsroom, chatbot, subscriptions, payments  # Add imports import
from app.services.ai_new.api_client import api_client
from app.services.subscription_service import subscription_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🚀 Starting PR Platform MVP...")
    await connect_to_mongo()
    await api_client.start()
    print("✅ API Client initialized")

    # Initialize subscription plans
    await subscription_service.initialize_default_plans()
    print("✅ Subscription plans initialized")

    yield
    # Shutdown
    print("👋 Shutting down PR Platform MVP...")
    await close_mongo_connection()
    await api_client.stop()
    print("✅ API Client closed")

app = FastAPI(
    title="AI-Powered PR Platform MVP",
    description="Minimal viable product for PR automation",
    version="2.0.0", # Final Version
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix=f"{settings.api_v1_prefix}/auth", tags=["Authentication"])
app.include_router(journalists.router, prefix=f"{settings.api_v1_prefix}/journalists", tags=["Journalists"])
app.include_router(pitches.router, prefix=f"{settings.api_v1_prefix}/pitches", tags=["Pitches"])
app.include_router(emails.router, prefix=f"{settings.api_v1_prefix}/emails", tags=["Email"])  
app.include_router(imports.router, prefix=f"{settings.api_v1_prefix}/import", tags=["Import"]) # Add imports router
app.include_router(profile.router, prefix=f"{settings.api_v1_prefix}/profile", tags=["Profile"])
app.include_router(newsroom.router, prefix=f"{settings.api_v1_prefix}/newsroom", tags=["Newsroom"])
app.include_router(chatbot.router, prefix=f"{settings.api_v1_prefix}/chatbot", tags=["chatbot"])
app.include_router(payments.router, prefix=f"{settings.api_v1_prefix}/payments", tags=["Payments"])
app.include_router(subscriptions.router, prefix=f"{settings.api_v1_prefix}/subscriptions", tags=["Subscriptions"])



@app.get("/")
async def root():
    return {
        "message": "AI-Powered PR Platform API", 
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "features": [
            "User Authentication",
            "Journalist Management", 
            "AI Pitch Generation",
            "Email Integration"
        ]
    }



@app.get("/health")
async def health_check():
    db_connected = is_database_connected()
    
    return {
        "status": "healthy", 
        "environment": settings.environment,
        "database": "connected" if db_connected else "disconnected",
        "database_name": settings.database_name,
        "ai_service": "ready" if settings.openai_api_key else "not_configured",
        "email_service": "configured" if all([settings.smtp_host, settings.smtp_user, settings.smtp_password]) else "not_configured"
    }
