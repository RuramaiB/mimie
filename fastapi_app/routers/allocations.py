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

from models.pydantic_models import AllocationCreate, AllocationResponse
from models.sqlalchemy_models import StandAllocationORM
from auth import get_current_user, RoleGuard

router = APIRouter(tags=["Stand Allocations Manager"])

def validate_db(db: str):
    if db not in ("mysql", "postgres", "oracle", "mssql", "mongodb"):
        raise HTTPException(status_code=400, detail="Invalid DBMS target")

@router.get("/{db}/allocations/", response_model=List[AllocationResponse])
async def list_allocations(
    db: str,
    mysql_db: Session = Depends(get_mysql_db),
    postgres_db: AsyncSession = Depends(get_postgres_db),
    oracle_db: Session = Depends(get_oracle_db),
    mssql_db: Session = Depends(get_mssql_db),
    mongo_db = Depends(get_mongo_db)
):
    """
    List all subdivisions allocated to owners.
    """
    validate_db(db)

    # 1. PostgreSQL (Async Engine)
    if db == "postgres":
        result = await postgres_db.execute(text("SELECT allocation_id, stand_owner_id, subdivision_id, date_of_allocation, price_per_m2, created_at FROM stand_allocations"))
        allocs = []
        for row in result.fetchall():
            allocs.append(AllocationResponse(
                allocation_id=row.allocation_id,
                stand_owner_id=row.stand_owner_id,
                subdivision_id=row.subdivision_id,
                date_of_allocation=row.date_of_allocation,
                price_per_m2=float(row.price_per_m2),
                created_at=row.created_at
            ))
        return allocs

    # 2. MongoDB
    elif db == "mongodb":
        cursor = mongo_db.stand_allocations.find()
        allocs = []
        async for doc in cursor:
            allocs.append(AllocationResponse(
                allocation_id=doc["allocation_id"],
                stand_owner_id=doc["stand_owner_id"],
                subdivision_id=doc["subdivision_id"],
                date_of_allocation=doc["date_of_allocation"].date(),
                price_per_m2=float(doc["price_per_m2"].to_decimal())
            ))
        return allocs

    # 3. MySQL
    elif db == "mysql":
        db_allocs = mysql_db.query(StandAllocationORM).all()
        return [AllocationResponse.model_validate(a) for a in db_allocs]

    # 4. Oracle
    elif db == "oracle":
        db_allocs = oracle_db.query(StandAllocationORM).all()
        return [AllocationResponse.model_validate(a) for a in db_allocs]

    # 5. MS SQL
    elif db == "mssql":
        result = mssql_db.execute(text("SELECT allocation_id, stand_owner_id, subdivision_id, date_of_allocation, price_per_m2, created_at FROM stand_allocations"))
        allocs = []
        for row in result.fetchall():
            allocs.append(AllocationResponse(
                allocation_id=row.allocation_id,
                stand_owner_id=row.stand_owner_id,
                subdivision_id=row.subdivision_id,
                date_of_allocation=row.date_of_allocation,
                price_per_m2=float(row.price_per_m2),
                created_at=row.created_at
            ))
        return allocs

@router.post("/{db}/allocations/", response_model=AllocationResponse, status_code=210)
async def create_allocation(
    db: str,
    payload: AllocationCreate,
    mysql_db: Session = Depends(get_mysql_db),
    postgres_db: AsyncSession = Depends(get_postgres_db),
    oracle_db: Session = Depends(get_oracle_db),
    mssql_db: Session = Depends(get_mssql_db),
    mongo_db = Depends(get_mongo_db),
    current_user = Depends(RoleGuard(["land_app", "land_admin"]))
):
    """
    Allocates a subdivision to an owner via Transactional Stored Procedure.
    """
    validate_db(db)

    # 1. MongoDB Allocation logic (simulating transactional stored procedure)
    if db == "mongodb":
        from bson.decimal128 import Decimal128
        import datetime

        # Check owner validity
        owner = await mongo_db.stand_owners.find_one({"stand_owner_id": payload.stand_owner_id})
        if not owner:
            raise HTTPException(status_code=400, detail="Validation Error: Owner ID is not registered.")
        
        # Check subdivision validity
        sub = await mongo_db.stand_subdivisions.find_one({"subdivision_id": payload.subdivision_id})
        if not sub:
            raise HTTPException(status_code=400, detail="Validation Error: Subdivision ID does not exist.")
        
        if sub.get("allocation_status") is True:
            raise HTTPException(status_code=400, detail="Business Rule Violation: This subdivision is already allocated.")

        max_doc = await mongo_db.stand_allocations.find_one(sort=[("allocation_id", -1)])
        new_id = (max_doc["allocation_id"] + 1) if max_doc else 1

        # Atomically allocate
        await mongo_db.stand_subdivisions.update_one(
            {"subdivision_id": payload.subdivision_id},
            {"$set": {"allocation_status": True}}
        )
        
        doc = {
            "allocation_id": new_id,
            "stand_owner_id": payload.stand_owner_id,
            "subdivision_id": payload.subdivision_id,
            "date_of_allocation": datetime.datetime.now(),
            "price_per_m2": Decimal128(str(payload.price_per_m2))
        }
        await mongo_db.stand_allocations.insert_one(doc)
        
        return AllocationResponse(
            allocation_id=new_id,
            stand_owner_id=payload.stand_owner_id,
            subdivision_id=payload.subdivision_id,
            date_of_allocation=date.today(),
            price_per_m2=payload.price_per_m2
        )

    # 2. Relational Database Stored Procedure Trigger
    try:
        if db == "postgres":
            # Call postgres sp_allocate_stand function
            await postgres_db.execute(
                text("SELECT sp_allocate_stand(:owner, :sub, :price)"),
                {"owner": payload.stand_owner_id, "sub": payload.subdivision_id, "price": payload.price_per_m2}
            )
            await postgres_db.commit()
            
            # Fetch latest allocation record
            result = await postgres_db.execute(
                text("SELECT allocation_id, date_of_allocation FROM stand_allocations WHERE subdivision_id = :sub"),
                {"sub": payload.subdivision_id}
            )
            row = result.fetchone()
            return AllocationResponse(
                allocation_id=row.allocation_id,
                stand_owner_id=payload.stand_owner_id,
                subdivision_id=payload.subdivision_id,
                date_of_allocation=row.date_of_allocation,
                price_per_m2=payload.price_per_m2
            )

        elif db == "mysql":
            mysql_db.execute(
                text("CALL sp_allocate_stand(:owner, :sub, :price)"),
                {"owner": payload.stand_owner_id, "sub": payload.subdivision_id, "price": payload.price_per_m2}
            )
            mysql_db.commit()
            row = mysql_db.execute(
                text("SELECT allocation_id, date_of_allocation FROM stand_allocations WHERE subdivision_id = :sub"),
                {"sub": payload.subdivision_id}
            ).fetchone()
            return AllocationResponse(
                allocation_id=row.allocation_id,
                stand_owner_id=payload.stand_owner_id,
                subdivision_id=payload.subdivision_id,
                date_of_allocation=row.date_of_allocation,
                price_per_m2=payload.price_per_m2
            )

        elif db == "oracle":
            # Call Oracle package procedure
            cursor = oracle_db.connection.cursor()
            cursor.callproc("pkg_land_stand.sp_allocate_stand", [payload.stand_owner_id, payload.subdivision_id, payload.price_per_m2])
            oracle_db.commit()
            
            row = oracle_db.execute(
                text("SELECT allocation_id, date_of_allocation FROM stand_allocations WHERE subdivision_id = :sub"),
                {"sub": payload.subdivision_id}
            ).fetchone()
            return AllocationResponse(
                allocation_id=row.allocation_id,
                stand_owner_id=payload.stand_owner_id,
                subdivision_id=payload.subdivision_id,
                date_of_allocation=row.date_of_allocation,
                price_per_m2=payload.price_per_m2
            )

        elif db == "mssql":
            mssql_db.execute(
                text("EXEC sp_allocate_stand :owner, :sub, :price"),
                {"owner": payload.stand_owner_id, "sub": payload.subdivision_id, "price": payload.price_per_m2}
            )
            mssql_db.commit()
            
            row = mssql_db.execute(
                text("SELECT allocation_id, date_of_allocation FROM stand_allocations WHERE subdivision_id = :sub"),
                {"sub": payload.subdivision_id}
            ).fetchone()
            return AllocationResponse(
                allocation_id=row.allocation_id,
                stand_owner_id=payload.stand_owner_id,
                subdivision_id=payload.subdivision_id,
                date_of_allocation=row.date_of_allocation,
                price_per_m2=payload.price_per_m2
            )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Database Procedure Execution Failed: {str(e)}")

@router.delete("/{db}/allocations/{id}", status_code=204)
async def delete_allocation(
    db: str,
    id: int,
    mysql_db: Session = Depends(get_mysql_db),
    postgres_db: AsyncSession = Depends(get_postgres_db),
    oracle_db: Session = Depends(get_oracle_db),
    mssql_db: Session = Depends(get_mssql_db),
    mongo_db = Depends(get_mongo_db),
    current_user = Depends(RoleGuard(["land_app", "land_admin"]))
):
    """
    Cancels an active stand allocation (Triggers will automatically reset subdivision state).
    """
    validate_db(db)

    if db == "postgres":
        # Check if allocation exists
        result = await postgres_db.execute(text("SELECT allocation_id FROM stand_allocations WHERE allocation_id = :id"), {"id": id})
        if not result.fetchone():
            raise HTTPException(status_code=404, detail="Allocation not found")
        await postgres_db.execute(text("DELETE FROM stand_allocations WHERE allocation_id = :id"), {"id": id})
        await postgres_db.commit()
        return

    elif db == "mongodb":
        alloc = await mongo_db.stand_allocations.find_one({"allocation_id": id})
        if not alloc:
            raise HTTPException(status_code=404, detail="Allocation not found")
        # Reset subdivision allocation status
        await mongo_db.stand_subdivisions.update_one(
            {"subdivision_id": alloc["subdivision_id"]},
            {"$set": {"allocation_status": False}}
        )
        await mongo_db.stand_allocations.delete_one({"allocation_id": id})
        return

    elif db == "mysql":
        a = mysql_db.query(StandAllocationORM).filter(StandAllocationORM.allocation_id == id).first()
        if not a:
            raise HTTPException(status_code=404, detail="Allocation not found")
        mysql_db.delete(a)
        mysql_db.commit()
        return

    elif db == "oracle":
        a = oracle_db.query(StandAllocationORM).filter(StandAllocationORM.allocation_id == id).first()
        if not a:
            raise HTTPException(status_code=404, detail="Allocation not found")
        oracle_db.delete(a)
        oracle_db.commit()
        return

    elif db == "mssql":
        row = mssql_db.execute(text("SELECT allocation_id FROM stand_allocations WHERE allocation_id = :id"), {"id": id}).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Allocation not found")
        mssql_db.execute(text("DELETE FROM stand_allocations WHERE allocation_id = :id"), {"id": id})
        mssql_db.commit()
        return
