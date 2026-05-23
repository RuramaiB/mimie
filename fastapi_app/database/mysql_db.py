import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
from config import settings

logger = logging.getLogger("land_system.database.mysql")

# Construct MySQL Connection URI (using PyMySQL)
MYSQL_URL = f"mysql+pymysql://{settings.MYSQL_USER}:{settings.MYSQL_PASSWORD}@{settings.MYSQL_HOST}:{settings.MYSQL_PORT}/{settings.MYSQL_DB}"

# Initialize pool size and overflow configuration
engine = create_engine(
    MYSQL_URL,
    pool_size=settings.POOL_SIZE,
    max_overflow=settings.MAX_OVERFLOW,
    pool_recycle=1800,
    pool_pre_ping=True
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_mysql_db() -> Generator[Session, None, None]:
    """
    FastAPI Dependency yielding scoped SQLAlchemy Session instances for MySQL.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def check_mysql_health() -> bool:
    """
    Performs quick SELECT query to verify MySQL active state.
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"MySQL Health Check Failed: {e}")
        return False
