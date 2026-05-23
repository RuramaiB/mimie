from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import List, Optional
from datetime import date
from database.mysql_db import get_mysql_db
from database.postgres_db import get_postgres_db
from database.oracle_db import get_oracle_db
from database.mssql_db import get_mssql_db
from database.mongo_db import get_mongo_db

from models.pydantic_models import OwnerCreate, OwnerResponse
from models.sqlalchemy_models import StandOwnerORM
from auth import get_current_user, RoleGuard

router = APIRouter(tags=["Stand Owners Catalogue"])

def validate_db(db: str):
    if db not in ("mysql", "postgres", "oracle", "mssql", "mongodb"):
        raise HTTPException(status_code=400, detail="Invalid DBMS target")

@router.get("/{db}/owners/", response_model=List[OwnerResponse])
async def list_owners(
    db: str,
    province: Optional[str] = None,
    district: Optional[str] = None,
    mysql_db: Session = Depends(get_mysql_db),
    postgres_db: AsyncSession = Depends(get_postgres_db),
    oracle_db: Session = Depends(get_oracle_db),
    mssql_db: Session = Depends(get_mssql_db),
    mongo_db = Depends(get_mongo_db),
    current_user = Depends(get_current_user)
):
    """
    Lists registered stand owners with optional geographic filtering (Enforces current active user scope).
    """
    validate_db(db)

    # 1. PostgreSQL (Enforcing RLS context setting)
    if db == "postgres":
        # Inject context role parameters into local Postgres transaction context
        await postgres_db.execute(text("SET LOCAL app.current_user_role = :role"), {"role": current_user.role})
        
        query_str = "SELECT stand_owner_id, firstname, date_of_birth, gender, disability_status, province, district, created_at FROM stand_owners WHERE 1=1"
        params = {}
        if province:
            query_str += " AND province = :prov"
            params["prov"] = province
        if district:
            query_str += " AND district = :dist"
            params["dist"] = district

        result = await postgres_db.execute(text(query_str), params)
        owners = []
        for row in result.fetchall():
            owners.append(OwnerResponse(
                stand_owner_id=row.stand_owner_id,
                firstname=row.firstname,
                date_of_birth=row.date_of_birth,
                gender=row.gender,
                disability_status=row.disability_status,
                province=row.province,
                district=row.district,
                created_at=row.created_at
            ))
        return owners

    # 2. MongoDB
    elif db == "mongodb":
        query = {}
        if province:
            query["province"] = province
        if district:
            query["district"] = district
        
        cursor = mongo_db.stand_owners.find(query)
        owners = []
        async for doc in cursor:
            # Parse Date field safely from MongoDB datetime
            dob = doc["date_of_birth"]
            dob_date = dob.date() if isinstance(dob, datetime) else dob
            owners.append(OwnerResponse(
                stand_owner_id=doc["stand_owner_id"],
                firstname=doc["firstname"],
                date_of_birth=dob_date,
                gender=doc["gender"],
                disability_status=doc["disability_status"],
                province=doc["province"],
                district=doc["district"]
            ))
        return owners

    # 3. MySQL
    elif db == "mysql":
        q = mysql_db.query(StandOwnerORM)
        if province:
            q = q.filter(StandOwnerORM.province == province)
        if district:
            q = q.filter(StandOwnerORM.district == district)
        return [OwnerResponse.model_validate(o) for o in q.all()]

    # 4. Oracle
    elif db == "oracle":
        q = oracle_db.query(StandOwnerORM)
        if province:
            q = q.filter(StandOwnerORM.province == province)
        if district:
            q = q.filter(StandOwnerORM.district == district)
        return [OwnerResponse.model_validate(o) for o in q.all()]

    # 5. MS SQL (Apply session contexts)
    elif db == "mssql":
        # Inject MSSQL Session contexts for RLS security mapping
        mssql_db.execute(text("EXEC sp_set_session_context 'current_user_role', :role"), {"role": current_user.role})
        
        query_str = "SELECT stand_owner_id, firstname, date_of_birth, gender, disability_status, province, district, created_at FROM stand_owners WHERE 1=1"
        params = {}
        if province:
            query_str += " AND province = :prov"
            params["prov"] = province
        if district:
            query_str += " AND district = :dist"
            params["dist"] = district
            
        result = mssql_db.execute(text(query_str), params)
        owners = []
        for row in result.fetchall():
            owners.append(OwnerResponse(
                stand_owner_id=row.stand_owner_id,
                firstname=row.firstname,
                date_of_birth=row.date_of_birth,
                gender=row.gender,
                disability_status=row.disability_status,
                province=row.province,
                district=row.district,
                created_at=row.created_at
            ))
        return owners

@router.get("/{db}/owners/{owner_id}", response_model=OwnerResponse)
async def get_owner(
    db: str,
    owner_id: int,
    mysql_db: Session = Depends(get_mysql_db),
    postgres_db: AsyncSession = Depends(get_postgres_db),
    oracle_db: Session = Depends(get_oracle_db),
    mssql_db: Session = Depends(get_mssql_db),
    mongo_db = Depends(get_mongo_db),
    current_user = Depends(get_current_user)
):
    """
    Fetches details of a single stand owner.
    """
    validate_db(db)

    if db == "postgres":
        await postgres_db.execute(text("SET LOCAL app.current_user_role = :role"), {"role": current_user.role})
        await postgres_db.execute(text("SET LOCAL app.current_owner_id = :id"), {"id": owner_id})
        
        query = text("SELECT stand_owner_id, firstname, date_of_birth, gender, disability_status, province, district, created_at FROM stand_owners WHERE stand_owner_id = :id")
        result = await postgres_db.execute(query, {"id": owner_id})
        row = result.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Owner not registered or access denied by RLS policy")
        return OwnerResponse(
            stand_owner_id=row.stand_owner_id,
            firstname=row.firstname,
            date_of_birth=row.date_of_birth,
            gender=row.gender,
            disability_status=row.disability_status,
            province=row.province,
            district=row.district,
            created_at=row.created_at
        )

    elif db == "mongodb":
        doc = await mongo_db.stand_owners.find_one({"stand_owner_id": owner_id})
        if not doc:
            raise HTTPException(status_code=404, detail="Owner not registered")
        dob = doc["date_of_birth"]
        dob_date = dob.date() if isinstance(dob, datetime) else dob
        return OwnerResponse(
            stand_owner_id=doc["stand_owner_id"],
            firstname=doc["firstname"],
            date_of_birth=dob_date,
            gender=doc["gender"],
            disability_status=doc["disability_status"],
            province=doc["province"],
            district=doc["district"]
        )

    elif db == "mysql":
        o = mysql_db.query(StandOwnerORM).filter(StandOwnerORM.stand_owner_id == owner_id).first()
        if not o:
            raise HTTPException(status_code=404, detail="Owner not registered")
        return OwnerResponse.model_validate(o)

    elif db == "oracle":
        o = oracle_db.query(StandOwnerORM).filter(StandOwnerORM.stand_owner_id == owner_id).first()
        if not o:
            raise HTTPException(status_code=404, detail="Owner not registered")
        return OwnerResponse.model_validate(o)

    elif db == "mssql":
        mssql_db.execute(text("EXEC sp_set_session_context 'current_user_role', :role"), {"role": current_user.role})
        mssql_db.execute(text("EXEC sp_set_session_context 'current_owner_id', :id"), {"id": owner_id})
        
        query = text("SELECT stand_owner_id, firstname, date_of_birth, gender, disability_status, province, district, created_at FROM stand_owners WHERE stand_owner_id = :id")
        result = mssql_db.execute(query, {"id": owner_id})
        row = result.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Owner not registered or access denied by RLS policy")
        return OwnerResponse(
            stand_owner_id=row.stand_owner_id,
            firstname=row.firstname,
            date_of_birth=row.date_of_birth,
            gender=row.gender,
            disability_status=row.disability_status,
            province=row.province,
            district=row.district,
            created_at=row.created_at
        )

@router.post("/{db}/owners/", response_model=OwnerResponse, status_code=210)
async def create_owner(
    db: str,
    payload: OwnerCreate,
    mysql_db: Session = Depends(get_mysql_db),
    postgres_db: AsyncSession = Depends(get_postgres_db),
    oracle_db: Session = Depends(get_oracle_db),
    mssql_db: Session = Depends(get_mssql_db),
    mongo_db = Depends(get_mongo_db),
    current_user = Depends(RoleGuard(["land_app", "land_admin"]))
):
    """
    Registers a new stand owner (Requires write privileges).
    """
    validate_db(db)

    if db == "postgres":
        query = text("INSERT INTO stand_owners (firstname, date_of_birth, gender, disability_status, province, district) VALUES (:first, :dob, :gender, :dis, :prov, :dist) RETURNING stand_owner_id")
        result = await postgres_db.execute(query, {
            "first": payload.firstname,
            "dob": payload.date_of_birth,
            "gender": payload.gender,
            "dis": payload.disability_status,
            "prov": payload.province,
            "dist": payload.district
        })
        owner_id = result.scalar()
        await postgres_db.commit()
        return OwnerResponse(
            stand_owner_id=owner_id,
            firstname=payload.firstname,
            date_of_birth=payload.date_of_birth,
            gender=payload.gender,
            disability_status=payload.disability_status,
            province=payload.province,
            district=payload.district
        )

    elif db == "mongodb":
        # Compute incremental sequence ID
        max_doc = await mongo_db.stand_owners.find_one(sort=[("stand_owner_id", -1)])
        new_id = (max_doc["stand_owner_id"] + 1) if max_doc else 1
        
        dob_dt = datetime.combine(payload.date_of_birth, datetime.min.time())
        doc = {
            "stand_owner_id": new_id,
            "firstname": payload.firstname,
            "date_of_birth": dob_dt,
            "gender": payload.gender,
            "disability_status": payload.disability_status,
            "province": payload.province,
            "district": payload.district
        }
        await mongo_db.stand_owners.insert_one(doc)
        return OwnerResponse(
            stand_owner_id=new_id,
            firstname=payload.firstname,
            date_of_birth=payload.date_of_birth,
            gender=payload.gender,
            disability_status=payload.disability_status,
            province=payload.province,
            district=payload.district
        )

    elif db in ("mysql", "oracle"):
        orm_db = mysql_db if db == "mysql" else oracle_db
        o = StandOwnerORM(
            firstname=payload.firstname,
            date_of_birth=payload.date_of_birth,
            gender=payload.gender,
            disability_status=payload.disability_status,
            province=payload.province,
            district=payload.district
        )
        orm_db.add(o)
        orm_db.commit()
        orm_db.refresh(o)
        return OwnerResponse.model_validate(o)

    elif db == "mssql":
        query = text("INSERT INTO stand_owners (firstname, date_of_birth, gender, disability_status, province, district) OUTPUT INSERTED.stand_owner_id VALUES (:first, :dob, :gender, :dis, :prov, :dist)")
        result = mssql_db.execute(query, {
            "first": payload.firstname,
            "dob": payload.date_of_birth,
            "gender": payload.gender,
            "dis": payload.disability_status,
            "prov": payload.province,
            "dist": payload.district
        })
        owner_id = result.scalar()
        mssql_db.commit()
        return OwnerResponse(
            stand_owner_id=owner_id,
            firstname=payload.firstname,
            date_of_birth=payload.date_of_birth,
            gender=payload.gender,
            disability_status=payload.disability_status,
            province=payload.province,
            district=payload.district
        )

from datetime import datetime
