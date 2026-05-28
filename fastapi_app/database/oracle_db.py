import logging
import oracledb
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
import urllib.parse
from config import settings

logger = logging.getLogger("land_system.database.oracle")

# Ensure oracledb is running in "Thin Mode" (default behavior in v2+)
# No need to call oracledb.init_oracle_client()

# Construct Oracle connection URL
_user = urllib.parse.quote_plus(settings.ORACLE_USER)
_pwd = urllib.parse.quote_plus(settings.ORACLE_PASSWORD)
ORACLE_URL = f"oracle+oracledb://{_user}:{_pwd}@{settings.ORACLE_HOST}:{settings.ORACLE_PORT}/?service_name={settings.ORACLE_SERVICE}"

engine = create_engine(
    ORACLE_URL,
    pool_size=settings.POOL_SIZE,
    max_overflow=settings.MAX_OVERFLOW,
    pool_recycle=1800,
    pool_pre_ping=True
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_oracle_db() -> Generator[Session, None, None]:
    """
    FastAPI Dependency yielding scoped Session instances for Oracle.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def check_oracle_health() -> bool:
    """
    Performs quick SELECT query to verify Oracle active state.
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1 FROM dual"))
        return True
    except Exception as e:
        logger.error(f"Oracle Health Check Failed: {e}")
        return False
