from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import List, Dict, Any
from database.mysql_db import get_mysql_db
from database.postgres_db import get_postgres_db
from database.oracle_db import get_oracle_db
from database.mssql_db import get_mssql_db
from database.mongo_db import get_mongo_db

router = APIRouter(prefix="/metadata", tags=["Metadata Governance"])

def validate_db(db: str):
    if db not in ("mysql", "postgres", "oracle", "mssql", "mongodb"):
        raise HTTPException(status_code=400, detail="Invalid DBMS target")

@router.get("/{db}", response_model=List[Dict[str, Any]])
async def get_metadata_catalogue(
    db: str,
    mysql_db: Session = Depends(get_mysql_db),
    postgres_db: AsyncSession = Depends(get_postgres_db),
    oracle_db: Session = Depends(get_oracle_db),
    mssql_db: Session = Depends(get_mssql_db),
    mongo_db = Depends(get_mongo_db)
):
    """
    Exposes the complete data classification catalog matrix for the selected target system.
    """
    validate_db(db)

    # 1. PostgreSQL (Async Engine)
    if db == "postgres":
        result = await postgres_db.execute(text("SELECT * FROM metadata_catalogue"))
        return [dict(row._mapping) for row in result.fetchall()]

    # 2. MongoDB
    elif db == "mongodb":
        cursor = mongo_db.metadata_catalogue.find()
        results = []
        async for doc in cursor:
            results.append({
                "table_name": doc["table_name"],
                "column_name": doc["column_name"],
                "data_type": doc["data_type"],
                "is_pii": doc["is_pii"],
                "data_classification": doc["data_classification"],
                "data_owner": doc.get("data_owner", "Ministry of Lands"),
                "data_steward": doc.get("data_steward", "GIS Department")
            })
        return results

    # 3. MySQL
    elif db == "mysql":
        result = mysql_db.execute(text("SELECT * FROM metadata_catalogue")).fetchall()
        return [dict(row._mapping) for row in result]

    # 4. Oracle
    elif db == "oracle":
        result = oracle_db.execute(text("SELECT * FROM metadata_catalogue")).fetchall()
        return [dict(row._mapping) for row in result]

    # 5. MS SQL
    elif db == "mssql":
        result = mssql_db.execute(text("SELECT * FROM metadata_catalogue")).fetchall()
        return [dict(row._mapping) for row in result]

@router.get("/{db}/pii", response_model=List[Dict[str, Any]])
async def get_pii_fields(
    db: str,
    mysql_db: Session = Depends(get_mysql_db),
    postgres_db: AsyncSession = Depends(get_postgres_db),
    oracle_db: Session = Depends(get_oracle_db),
    mssql_db: Session = Depends(get_mssql_db),
    mongo_db = Depends(get_mongo_db)
):
    """
    Returns only PII flagged classifications (Requires specific governance masking).
    """
    validate_db(db)

    # 1. PostgreSQL (Async Engine)
    if db == "postgres":
        result = await postgres_db.execute(text("SELECT * FROM metadata_catalogue WHERE is_pii = TRUE"))
        return [dict(row._mapping) for row in result.fetchall()]

    # 2. MongoDB
    elif db == "mongodb":
        cursor = mongo_db.metadata_catalogue.find({"is_pii": True})
        results = []
        async for doc in cursor:
            results.append({
                "table_name": doc["table_name"],
                "column_name": doc["column_name"],
                "data_type": doc["data_type"],
                "is_pii": doc["is_pii"],
                "data_classification": doc["data_classification"],
                "data_owner": doc.get("data_owner"),
                "data_steward": doc.get("data_steward")
            })
        return results

    # 3. MySQL
    elif db == "mysql":
        result = mysql_db.execute(text("SELECT * FROM metadata_catalogue WHERE is_pii = 1")).fetchall()
        return [dict(row._mapping) for row in result]

    # 4. Oracle
    elif db == "oracle":
        result = oracle_db.execute(text("SELECT * FROM metadata_catalogue WHERE is_pii = 1")).fetchall()
        return [dict(row._mapping) for row in result]

    # 5. MS SQL
    elif db == "mssql":
        result = mssql_db.execute(text("SELECT * FROM metadata_catalogue WHERE is_pii = 1")).fetchall()
        return [dict(row._mapping) for row in result]
