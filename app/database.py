from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings
from app.models.user import User
from app.models.journalist import Journalist
from app.models.pitch import Pitch
from app.models.interaction import Interaction  # Add Interaction import

class Database:
    client: AsyncIOMotorClient = None
    connected: bool = False
    
database = Database()

async def connect_to_mongo():
    """Create database connection"""
    try:
        print(f"🔌 Connecting to MongoDB at {settings.mongodb_url}")
        database.client = AsyncIOMotorClient(settings.mongodb_url)
        
        # Test the connection
        await database.client.admin.command('ping')
        database.connected = True
        print("✅ MongoDB connection successful!")
        
        # Initialize Beanie with all models
        await init_beanie(
            database=database.client[settings.database_name],
            document_models=[User, Journalist, Pitch, Interaction]  # Add Interaction model
        )
        
        print(f"📊 Database '{settings.database_name}' initialized with all models")
        
    except Exception as e:
        print(f"❌ Failed to connect to MongoDB: {e}")
        database.connected = False
        raise e

async def close_mongo_connection():
    """Close database connection"""
    if database.client:
        database.client.close()
        database.connected = False
        print("👋 Disconnected from MongoDB")

async def get_database():
    """Get database instance"""
    return database.client[settings.database_name] if database.client else None

def is_database_connected() -> bool:
    """Check if database is connected"""
    return database.connected
