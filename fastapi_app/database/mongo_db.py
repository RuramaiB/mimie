import logging
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient
import urllib.parse
from config import settings

logger = logging.getLogger("land_system.database.mongo")

# Construct MongoDB URI
# Authenticates via admin or custom database defined in MONGO_AUTH_DB
_user = urllib.parse.quote_plus(settings.MONGO_USER)
_pwd = urllib.parse.quote_plus(settings.MONGO_PASSWORD)
MONGO_URI = f"mongodb://{_user}:{_pwd}@{settings.MONGO_HOST}:{settings.MONGO_PORT}/?authSource={settings.MONGO_AUTH_DB}"

# Async Client (Motor)
async_client = AsyncIOMotorClient(MONGO_URI)
async_db = async_client[settings.MONGO_DB]

# Sync Client (PyMongo - used for scripts or quick non-async utilities)
sync_client = MongoClient(MONGO_URI)
sync_db = sync_client[settings.MONGO_DB]

def get_mongo_db():
    """
    FastAPI Dependency yielding active MongoDB Async database handler.
    """
    return async_db

async def check_mongo_health() -> bool:
    """
    Performs ping check to verify MongoDB active state.
    """
    try:
        # Run admin ping command
        await async_client.admin.command('ping')
        return True
    except Exception as e:
        logger.error(f"MongoDB Health Check Failed: {e}")
        return False
