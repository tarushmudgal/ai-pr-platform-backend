from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Database
    mongodb_url: str = "mongodb://localhost:27017"
    database_name: str = "pr_platform_mvp"
    
    # OpenAI
    openai_api_key: str = ""
    
    # JWT
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440
    
    # Email
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""

    # AWS S3
    aws_access_key_id: str
    aws_secret_access_key: str
    aws_region: str
    s3_bucket: str
    
    # App
    environment: str = "development"
    debug: bool = True
    api_v1_prefix: str = "/api/v1"

    # Razorpay Configuration
    razorpay_key_id: str
    razorpay_key_secret: str
    
    class Config:
        env_file = ".env"

settings = Settings()
