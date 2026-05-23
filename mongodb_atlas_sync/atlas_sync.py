import os
import sys
import logging
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("atlas_sync")

# Load environment configurations
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
load_dotenv(env_path)

LOCAL_MONGO_URI = os.getenv("MONGO_URI", "mongodb://land_app:AppPassword123!@localhost:27017/?authSource=admin")
ATLAS_MONGO_URI = os.getenv("MONGODB_ATLAS_URI")
DB_NAME = os.getenv("MONGO_DB", "devdb")

COLLECTIONS = [
    "stands",
    "stand_survey",
    "stand_subdivisions",
    "stand_owners",
    "dependents",
    "stand_allocations",
    "metadata_catalogue"
]

def get_primary_key(collection_name: str) -> str:
    """
    Returns the appropriate primary key name for a given collection.
    """
    pk_mapping = {
        "stands": "stand_number",
        "stand_subdivisions": "subdivision_id",
        "stand_owners": "stand_owner_id",
        "stand_allocations": "allocation_id"
    }
    return pk_mapping.get(collection_name, "_id")

def run_sync():
    """
    Connects to local MongoDB and mirrors all collections to the MongoDB Atlas cluster.
    """
    if not ATLAS_MONGO_URI or "atlas_user" in ATLAS_MONGO_URI:
        logger.error("Error: MONGODB_ATLAS_URI environment variable is missing or using placeholder credentials.")
        logger.info("Please set a valid Atlas connection string in your .env file.")
        sys.exit(1)

    logger.info("Initializing connection to Local MongoDB instance...")
    try:
        local_client = MongoClient(LOCAL_MONGO_URI)
        local_db = local_client[DB_NAME]
        # Quick query to check connectivity
        local_client.admin.command("ping")
        logger.info("Successfully connected to Local MongoDB!")
    except PyMongoError as e:
        logger.error(f"Failed to connect to local MongoDB: {e}")
        sys.exit(1)

    logger.info("Initializing connection to MongoDB Atlas Cluster...")
    try:
        atlas_client = MongoClient(ATLAS_MONGO_URI)
        atlas_db = atlas_client[DB_NAME]
        atlas_client.admin.command("ping")
        logger.info("Successfully connected to MongoDB Atlas!")
    except PyMongoError as e:
        logger.error(f"Failed to connect to MongoDB Atlas: {e}")
        sys.exit(1)

    # Sync loop
    for col_name in COLLECTIONS:
        logger.info(f"Syncing collection: '{col_name}'...")
        local_col = local_db[col_name]
        atlas_col = atlas_db[col_name]

        # Fetch local records
        local_docs = list(local_col.find({}))
        if not local_docs:
            logger.info(f"Collection '{col_name}' is empty on local database. Skipping.")
            continue

        logger.info(f"Found {len(local_docs)} documents in local collection '{col_name}'. Transferring...")
        
        # Upsert documents one-by-one to avoid primary key duplicate violations
        pk = get_primary_key(col_name)
        success_count = 0
        
        for doc in local_docs:
            try:
                # If collection has standard PK mapping, use it to upsert
                if pk != "_id" and pk in doc:
                    atlas_col.replace_one({pk: doc[pk]}, doc, upsert=True)
                else:
                    atlas_col.replace_one({"_id": doc["_id"]}, doc, upsert=True)
                success_count += 1
            except PyMongoError as e:
                logger.error(f"Failed to sync document ID {doc.get(pk, doc.get('_id'))} in '{col_name}': {e}")
                
        logger.info(f"Successfully synced {success_count}/{len(local_docs)} documents to Atlas for '{col_name}'!")

    logger.info("MongoDB Local-to-Atlas synchronization completed successfully!")

if __name__ == "__main__":
    run_sync()
