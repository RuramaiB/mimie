from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import List, Optional
from database.mysql_db import get_mysql_db
from database.postgres_db import get_postgres_db
from database.oracle_db import get_oracle_db
from database.mssql_db import get_mssql_db
from database.mongo_db import get_mongo_db

from models.pydantic_models import SubdivisionCreate, SubdivisionResponse
from models.sqlalchemy_models import StandSubdivisionORM
from auth import get_current_user, RoleGuard

router = APIRouter(tags=["Stand Subdivisions"])

def validate_db(db: str):
    if db not in ("mysql", "postgres", "oracle", "mssql", "mongodb"):
        raise HTTPException(status_code=400, detail="Invalid DBMS target")

@router.get("/{db}/subdivisions/", response_model=List[SubdivisionResponse])
async def list_subdivisions(
    db: str,
    allocated: Optional[bool] = None,
    mysql_db: Session = Depends(get_mysql_db),
    postgres_db: AsyncSession = Depends(get_postgres_db),
    oracle_db: Session = Depends(get_oracle_db),
    mssql_db: Session = Depends(get_mssql_db),
    mongo_db = Depends(get_mongo_db)
):
    """
    Lists stand subdivisions with optional availability filters.
    """
    validate_db(db)

    # 1. PostgreSQL (Async Engine)
    if db == "postgres":
        query_str = "SELECT subdivision_id, stand_number, allocation_status, size_m2, remarks, created_at FROM stand_subdivisions WHERE 1=1"
        params = {}
        if allocated is not None:
            query_str += " AND allocation_status = :alloc"
            params["alloc"] = allocated
        
        result = await postgres_db.execute(text(query_str), params)
        subs = []
        for row in result.fetchall():
            subs.append(SubdivisionResponse(
                subdivision_id=row.subdivision_id,
                stand_number=row.stand_number,
                allocation_status=row.allocation_status,
                size_m2=float(row.size_m2),
                remarks=row.remarks,
                created_at=row.created_at
            ))
        return subs

    # 2. MongoDB (Async Motor)
    elif db == "mongodb":
        query = {}
        if allocated is not None:
            query["allocation_status"] = allocated
            
        cursor = mongo_db.stand_subdivisions.find(query)
        subs = []
        async for doc in cursor:
            subs.append(SubdivisionResponse(
                subdivision_id=doc["subdivision_id"],
                stand_number=doc["stand_number"],
                allocation_status=doc["allocation_status"],
                size_m2=float(doc["size_m2"].to_decimal()),
                remarks=doc.get("remarks")
            ))
        return subs

    # 3. MySQL
    elif db == "mysql":
        q = mysql_db.query(StandSubdivisionORM)
        if allocated is not None:
            q = q.filter(StandSubdivisionORM.allocation_status == allocated)
        return [SubdivisionResponse.model_validate(s) for s in q.all()]

    # 4. Oracle
    elif db == "oracle":
        q = oracle_db.query(StandSubdivisionORM)
        if allocated is not None:
            q = q.filter(StandSubdivisionORM.allocation_status == (1 if allocated else 0))
        return [SubdivisionResponse.model_validate(s) for s in q.all()]

    # 5. MS SQL
    elif db == "mssql":
        query_str = "SELECT subdivision_id, stand_number, allocation_status, size_m2, remarks, created_at FROM stand_subdivisions WHERE 1=1"
        params = {}
        if allocated is not None:
            query_str += " AND allocation_status = :alloc"
            params["alloc"] = 1 if allocated else 0
            
        result = mssql_db.execute(text(query_str), params)
        subs = []
        for row in result.fetchall():
            subs.append(SubdivisionResponse(
                subdivision_id=row.subdivision_id,
                stand_number=row.stand_number,
                allocation_status=bool(row.allocation_status),
                size_m2=float(row.size_m2),
                remarks=row.remarks,
                created_at=row.created_at
            ))
        return subs

@router.post("/{db}/subdivisions/", response_model=SubdivisionResponse, status_code=210)
async def create_subdivision(
    db: str,
    payload: SubdivisionCreate,
    mysql_db: Session = Depends(get_mysql_db),
    postgres_db: AsyncSession = Depends(get_postgres_db),
    oracle_db: Session = Depends(get_oracle_db),
    mssql_db: Session = Depends(get_mssql_db),
    mongo_db = Depends(get_mongo_db),
    current_user = Depends(RoleGuard(["land_app", "land_admin"]))
):
    """
    Subdivides an existing surveyed stand.
    """
    validate_db(db)

    # MongoDB size and survey validation (since Mongo has no triggers)
    if db == "mongodb":
        from bson.decimal128 import Decimal128
        # Check survey
        survey = await mongo_db.stand_survey.find_one({"stand_number": payload.stand_number, "survey_status": True})
        if not survey:
            raise HTTPException(status_code=400, detail="Business Rule Violation: A stand must have an active survey status verified before subdividing.")

        # Check size capacity
        parent = await mongo_db.stands.find_one({"stand_number": payload.stand_number})
        if not parent:
            raise HTTPException(status_code=404, detail="Parent stand not found")
        
        parent_size = float(parent["size_m2"].to_decimal())
        
        cursor = mongo_db.stand_subdivisions.find({"stand_number": payload.stand_number})
        existing_sum = 0.0
        async for doc in cursor:
            existing_sum += float(doc["size_m2"].to_decimal())

        if (existing_sum + payload.size_m2) > parent_size:
            raise HTTPException(status_code=400, detail="Business Rule Violation: Total subdivisions size exceeds parent stand capacity.")

        max_doc = await mongo_db.stand_subdivisions.find_one(sort=[("subdivision_id", -1)])
        new_id = (max_doc["subdivision_id"] + 1) if max_doc else 1

        doc = {
            "subdivision_id": new_id,
            "stand_number": payload.stand_number,
            "allocation_status": False,
            "size_m2": Decimal128(str(payload.size_m2)),
            "remarks": payload.remarks
        }
        await mongo_db.stand_subdivisions.insert_one(doc)
        return SubdivisionResponse(
            subdivision_id=new_id,
            stand_number=payload.stand_number,
            allocation_status=False,
            size_m2=payload.size_m2,
            remarks=payload.remarks
        )

    # Relational Database Trigger-based execution
    try:
        if db == "postgres":
            query = text("INSERT INTO stand_subdivisions (stand_number, allocation_status, size_m2, remarks) VALUES (:num, :alloc, :size, :remarks) RETURNING subdivision_id")
            result = await postgres_db.execute(query, {
                "num": payload.stand_number,
                "alloc": payload.allocation_status,
                "size": payload.size_m2,
                "remarks": payload.remarks
            })
            sub_id = result.scalar()
            await postgres_db.commit()
            return SubdivisionResponse(
                subdivision_id=sub_id,
                stand_number=payload.stand_number,
                allocation_status=payload.allocation_status,
                size_m2=payload.size_m2,
                remarks=payload.remarks
            )

        elif db in ("mysql", "oracle"):
            orm_db = mysql_db if db == "mysql" else oracle_db
            s = StandSubdivisionORM(
                stand_number=payload.stand_number,
                allocation_status=payload.allocation_status,
                size_m2=payload.size_m2,
                remarks=payload.remarks
            )
            orm_db.add(s)
            orm_db.commit()
            orm_db.refresh(s)
            return SubdivisionResponse.model_validate(s)

        elif db == "mssql":
            query = text("INSERT INTO stand_subdivisions (stand_number, size_m2, remarks) VALUES (:num, :size, :remarks)")
            mssql_db.execute(query, {
                "num": payload.stand_number,
                "size": payload.size_m2,
                "remarks": payload.remarks
            })
            mssql_db.commit()
            
            # Fetch auto-generated primary key
            row = mssql_db.execute(text("SELECT @@IDENTITY")).fetchone()
            sub_id = int(row[0]) if row[0] is not None else 1
            return SubdivisionResponse(
                subdivision_id=sub_id,
                stand_number=payload.stand_number,
                allocation_status=False,
                size_m2=payload.size_m2,
                remarks=payload.remarks
            )
    except Exception as e:
        # Wrap trigger SQL raise messages cleanly in FastAPI exception
        raise HTTPException(status_code=400, detail=str(e))
