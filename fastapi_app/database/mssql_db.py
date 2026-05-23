import logging
import urllib
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
from config import settings

logger = logging.getLogger("land_system.database.mssql")

# Construct Connection Parameters for ODBC Driver 18
params = urllib.parse.quote_plus(
    f"DRIVER={{ODBC Driver 18 for SQL Server}};"
    f"SERVER={settings.MSSQL_HOST},{settings.MSSQL_PORT};"
    f"DATABASE={settings.MSSQL_DB};"
    f"UID={settings.MSSQL_USER};"
    f"PWD={settings.MSSQL_PASSWORD};"
    f"Encrypt=yes;"
    f"TrustServerCertificate=yes;"
)

MSSQL_URL = f"mssql+pyodbc:///?odbc_connect={params}"

engine = create_engine(
    MSSQL_URL,
    pool_size=settings.POOL_SIZE,
    max_overflow=settings.MAX_OVERFLOW,
    pool_recycle=1800,
    pool_pre_ping=True
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_mssql_db() -> Generator[Session, None, None]:
    """
    FastAPI Dependency yielding scoped Session instances for MS SQL.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def check_mssql_health() -> bool:
    """
    Performs quick SELECT query to verify MS SQL active state.
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"MS SQL Health Check Failed: {e}")
        return False
