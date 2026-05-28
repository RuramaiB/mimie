from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import List, Optional
from datetime import date, datetime
from database.mysql_db import get_mysql_db
from database.postgres_db import get_postgres_db
from database.oracle_db import get_oracle_db
from database.mssql_db import get_mssql_db
from database.mongo_db import get_mongo_db

from models.pydantic_models import DependentCreate, DependentResponse
from models.sqlalchemy_models import DependentORM
from auth import get_current_user, RoleGuard

router = APIRouter(tags=["Stand Owner Dependents"])

def validate_db(db: str):
    if db not in ("mysql", "postgres", "oracle", "mssql", "mongodb"):
        raise HTTPException(status_code=400, detail="Invalid DBMS target")

@router.get("/{db}/dependents/", response_model=List[DependentResponse])
async def list_dependents(
    db: str,
    owner_id: int,
    mysql_db: Session = Depends(get_mysql_db),
    postgres_db: AsyncSession = Depends(get_postgres_db),
    oracle_db: Session = Depends(get_oracle_db),
    mssql_db: Session = Depends(get_mssql_db),
    mongo_db = Depends(get_mongo_db)
):
    """
    Lists all dependents matching a specific stand owner ID.
    """
    validate_db(db)

    # 1. PostgreSQL (Async Engine)
    if db == "postgres":
        query = text("SELECT dependent_id, stand_owner_id, firstname, date_of_birth, gender, disability_status, created_at FROM dependents WHERE stand_owner_id = :owner_id")
        result = await postgres_db.execute(query, {"owner_id": owner_id})
        deps = []
        for row in result.fetchall():
            deps.append(DependentResponse(
                dependent_id=row.dependent_id,
                stand_owner_id=row.stand_owner_id,
                firstname=row.firstname,
                date_of_birth=row.date_of_birth,
                gender=row.gender,
                disability_status=row.disability_status,
                created_at=row.created_at
            ))
        return deps

    # 2. MongoDB (Async Motor)
    elif db == "mongodb":
        cursor = mongo_db.dependents.find({"stand_owner_id": owner_id})
        deps = []
        async for doc in cursor:
            dob = doc["date_of_birth"]
            dob_date = dob.date() if isinstance(dob, datetime) else dob
            deps.append(DependentResponse(
                dependent_id=hash(doc["firstname"]) & 0xffffffff,  # Simulating dependent_id
                stand_owner_id=doc["stand_owner_id"],
                firstname=doc["firstname"],
                date_of_birth=dob_date,
                gender=doc["gender"],
                disability_status=doc["disability_status"]
            ))
        return deps

    # 3. MySQL
    elif db == "mysql":
        db_deps = mysql_db.query(DependentORM).filter(DependentORM.stand_owner_id == owner_id).all()
        return [DependentResponse.model_validate(d) for d in db_deps]

    # 4. Oracle
    elif db == "oracle":
        db_deps = oracle_db.query(DependentORM).filter(DependentORM.stand_owner_id == owner_id).all()
        return [DependentResponse.model_validate(d) for d in db_deps]

    # 5. MS SQL
    elif db == "mssql":
        query = text("SELECT dependent_id, stand_owner_id, firstname, date_of_birth, gender, disability_status, created_at FROM dependents WHERE stand_owner_id = :owner_id")
        result = mssql_db.execute(query, {"owner_id": owner_id})
        deps = []
        for row in result.fetchall():
            deps.append(DependentResponse(
                dependent_id=row.dependent_id,
                stand_owner_id=row.stand_owner_id,
                firstname=row.firstname,
                date_of_birth=row.date_of_birth,
                gender=row.gender,
                disability_status=bool(row.disability_status),
                created_at=row.created_at
            ))
        return deps

@router.post("/{db}/dependents/", response_model=DependentResponse, status_code=210)
async def create_dependent(
    db: str,
    payload: DependentCreate,
    mysql_db: Session = Depends(get_mysql_db),
    postgres_db: AsyncSession = Depends(get_postgres_db),
    oracle_db: Session = Depends(get_oracle_db),
    mssql_db: Session = Depends(get_mssql_db),
    mongo_db = Depends(get_mongo_db),
    current_user = Depends(RoleGuard(["land_app", "land_admin"]))
):
    """
    Registers a new dependent under an owner (Requires write privileges).
    """
    validate_db(db)

    if db == "postgres":
        query = text("INSERT INTO dependents (stand_owner_id, firstname, date_of_birth, gender, disability_status) VALUES (:owner, :first, :dob, :gender, :dis) RETURNING dependent_id")
        result = await postgres_db.execute(query, {
            "owner": payload.stand_owner_id,
            "first": payload.firstname,
            "dob": payload.date_of_birth,
            "gender": payload.gender,
            "dis": payload.disability_status
        })
        dep_id = result.scalar()
        await postgres_db.commit()
        return DependentResponse(
            dependent_id=dep_id,
            stand_owner_id=payload.stand_owner_id,
            firstname=payload.firstname,
            date_of_birth=payload.date_of_birth,
            gender=payload.gender,
            disability_status=payload.disability_status
        )

    elif db == "mongodb":
        dob_dt = datetime.combine(payload.date_of_birth, datetime.min.time())
        doc = {
            "stand_owner_id": payload.stand_owner_id,
            "firstname": payload.firstname,
            "date_of_birth": dob_dt,
            "gender": payload.gender,
            "disability_status": payload.disability_status
        }
        await mongo_db.dependents.insert_one(doc)
        return DependentResponse(
            dependent_id=hash(payload.firstname) & 0xffffffff,
            stand_owner_id=payload.stand_owner_id,
            firstname=payload.firstname,
            date_of_birth=payload.date_of_birth,
            gender=payload.gender,
            disability_status=payload.disability_status
        )

    elif db in ("mysql", "oracle"):
        orm_db = mysql_db if db == "mysql" else oracle_db
        d = DependentORM(
            stand_owner_id=payload.stand_owner_id,
            firstname=payload.firstname,
            date_of_birth=payload.date_of_birth,
            gender=payload.gender,
            disability_status=payload.disability_status
        )
        orm_db.add(d)
        orm_db.commit()
        orm_db.refresh(d)
        return DependentResponse.model_validate(d)

    elif db == "mssql":
        query = text("INSERT INTO dependents (stand_owner_id, firstname, date_of_birth, gender, disability_status) OUTPUT INSERTED.dependent_id VALUES (:owner, :first, :dob, :gender, :dis)")
        result = mssql_db.execute(query, {
            "owner": payload.stand_owner_id,
            "first": payload.firstname,
            "dob": payload.date_of_birth,
            "gender": payload.gender,
            "dis": payload.disability_status
        })
        dep_id = result.scalar()
        mssql_db.commit()
        return DependentResponse(
            dependent_id=dep_id,
            stand_owner_id=payload.stand_owner_id,
            firstname=payload.firstname,
            date_of_birth=payload.date_of_birth,
            gender=payload.gender,
            disability_status=payload.disability_status
        )
