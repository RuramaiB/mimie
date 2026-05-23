from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import List, Dict, Any
import oracledb
from database.mysql_db import get_mysql_db
from database.postgres_db import get_postgres_db
from database.oracle_db import get_oracle_db
from database.mssql_db import get_mssql_db
from database.mongo_db import get_mongo_db
from auth import get_current_user

router = APIRouter(tags=["Stored Procedures & Custom Views Reports"])

def validate_db(db: str):
    if db not in ("mysql", "postgres", "oracle", "mssql", "mongodb"):
        raise HTTPException(status_code=400, detail="Invalid DBMS target")

# ═══════════════════════════════════════════════════════
#  REPORT 1: ALLOCATED STANDS VIEW
# ═══════════════════════════════════════════════════════

@router.get("/{db}/reports/allocated-stands", response_model=List[Dict[str, Any]])
async def report_allocated_stands(
    db: str,
    mysql_db: Session = Depends(get_mysql_db),
    postgres_db: AsyncSession = Depends(get_postgres_db),
    oracle_db: Session = Depends(get_oracle_db),
    mssql_db: Session = Depends(get_mssql_db),
    mongo_db = Depends(get_mongo_db)
):
    """
    Queries view `vw_allocated_stands` (Relational) or runs aggregation mapping (NoSQL).
    """
    validate_db(db)

    # 1. PostgreSQL View Query
    if db == "postgres":
        result = await postgres_db.execute(text("SELECT * FROM vw_allocated_stands"))
        return [dict(row._mapping) for row in result.fetchall()]

    # 2. MongoDB Aggregation Pipeline
    elif db == "mongodb":
        pipeline = [
            {
                "$lookup": {
                    "from": "stand_subdivisions",
                    "localField": "subdivision_id",
                    "foreignField": "subdivision_id",
                    "as": "sub"
                }
            },
            {"$unwind": "$sub"},
            {
                "$lookup": {
                    "from": "stands",
                    "localField": "sub.stand_number",
                    "foreignField": "stand_number",
                    "as": "stand"
                }
            },
            {"$unwind": "$stand"},
            {
                "$lookup": {
                    "from": "stand_owners",
                    "localField": "stand_owner_id",
                    "foreignField": "stand_owner_id",
                    "as": "owner"
                }
            },
            {"$unwind": "$owner"},
            {
                "$project": {
                    "_id": 0,
                    "allocation_id": 1,
                    "stand_number": "$stand.stand_number",
                    "stand_location": "$stand.location",
                    "subdivision_id": "$sub.subdivision_id",
                    "sub_size_m2": "$sub.size_m2",
                    "stand_owner_id": "$owner.stand_owner_id",
                    "owner_name": "$owner.firstname",
                    "disability_status": "$owner.disability_status",
                    "date_of_allocation": 1,
                    "total_allocation_price": {"$multiply": ["$sub.size_m2", "$price_per_m2"]}
                }
            }
        ]
        cursor = mongo_db.stand_allocations.aggregate(pipeline)
        results = []
        async for doc in cursor:
            # Convert Decimals
            doc["sub_size_m2"] = float(doc["sub_size_m2"].to_decimal())
            doc["total_allocation_price"] = float(doc["total_allocation_price"].to_decimal())
            doc["date_of_allocation"] = doc["date_of_allocation"].date()
            results.append(doc)
        return results

    # 3. MySQL
    elif db == "mysql":
        result = mysql_db.execute(text("SELECT * FROM vw_allocated_stands")).fetchall()
        return [dict(row._mapping) for row in result]

    # 4. Oracle
    elif db == "oracle":
        result = oracle_db.execute(text("SELECT * FROM vw_allocated_stands")).fetchall()
        return [dict(row._mapping) for row in result]

    # 5. MS SQL
    elif db == "mssql":
        result = mssql_db.execute(text("SELECT * FROM vw_allocated_stands")).fetchall()
        return [dict(row._mapping) for row in result]

# ═══════════════════════════════════════════════════════
#  REPORT 2: OWNER PORTFOLIO REPORT
# ═══════════════════════════════════════════════════════

@router.get("/{db}/reports/owner-portfolio/{owner_id}", response_model=List[Dict[str, Any]])
async def report_owner_portfolio(
    db: str,
    owner_id: int,
    mysql_db: Session = Depends(get_mysql_db),
    postgres_db: AsyncSession = Depends(get_postgres_db),
    oracle_db: Session = Depends(get_oracle_db),
    mssql_db: Session = Depends(get_mssql_db),
    mongo_db = Depends(get_mongo_db)
):
    """
    Invokes stored procedure `sp_owner_report` returning full allocation portfolios.
    """
    validate_db(db)

    # 1. PostgreSQL (Executes function returning TABLE)
    if db == "postgres":
        result = await postgres_db.execute(text("SELECT * FROM sp_owner_report(:id)"), {"id": owner_id})
        return [dict(row._mapping) for row in result.fetchall()]

    # 2. MongoDB Aggregation
    elif db == "mongodb":
        pipeline = [
            {"$match": {"stand_owner_id": owner_id}},
            {
                "$lookup": {
                    "from": "stand_allocations",
                    "localField": "stand_owner_id",
                    "foreignField": "stand_owner_id",
                    "as": "allocs"
                }
            },
            {"$unwind": { "path": "$allocs", "preserveNullAndEmptyArrays": True }},
            {
                "$lookup": {
                    "from": "stand_subdivisions",
                    "localField": "allocs.subdivision_id",
                    "foreignField": "subdivision_id",
                    "as": "sub"
                }
            },
            {"$unwind": { "path": "$sub", "preserveNullAndEmptyArrays": True }},
            {
                "$lookup": {
                    "from": "stands",
                    "localField": "sub.stand_number",
                    "foreignField": "stand_number",
                    "as": "stand"
                }
            },
            {"$unwind": { "path": "$stand", "preserveNullAndEmptyArrays": True }},
            {
                "$project": {
                    "_id": 0,
                    "stand_owner_id": 1,
                    "firstname": 1,
                    "province": 1,
                    "district": 1,
                    "allocation_id": "$allocs.allocation_id",
                    "date_of_allocation": "$allocs.date_of_allocation",
                    "price_per_m2": "$allocs.price_per_m2",
                    "subdivision_id": "$sub.subdivision_id",
                    "size_m2": "$sub.size_m2",
                    "stand_number": "$stand.stand_number",
                    "location": "$stand.location"
                }
            }
        ]
        cursor = mongo_db.stand_owners.aggregate(pipeline)
        results = []
        async for doc in cursor:
            if doc.get("size_m2"):
                doc["size_m2"] = float(doc["size_m2"].to_decimal())
            if doc.get("price_per_m2"):
                doc["price_per_m2"] = float(doc["price_per_m2"].to_decimal())
            if doc.get("date_of_allocation"):
                doc["date_of_allocation"] = doc["date_of_allocation"].date()
            results.append(doc)
        return results

    # 3. MySQL
    elif db == "mysql":
        result = mysql_db.execute(text("CALL sp_owner_report(:id)"), {"id": owner_id}).fetchall()
        return [dict(row._mapping) for row in result]

    # 4. Oracle (PL/SQL REF CURSOR parsing)
    elif db == "oracle":
        # Get raw connection object from engine session
        conn = oracle_db.connection
        cursor = conn.cursor()
        ref_cursor = cursor.var(oracledb.CURSOR)
        
        # Execute oracle package proc passing in OUT REF_CURSOR variable
        cursor.callproc("pkg_land_stand.sp_owner_report", [owner_id, ref_cursor])
        
        col_names = [col[0].lower() for col in ref_cursor.value.description]
        rows = ref_cursor.value.fetchall()
        
        results = []
        for r in rows:
            results.append(dict(zip(col_names, r)))
            
        cursor.close()
        return results

    # 5. MS SQL Server
    elif db == "mssql":
        result = mssql_db.execute(text("EXEC sp_owner_report :id"), {"id": owner_id}).fetchall()
        return [dict(row._mapping) for row in result]

# ═══════════════════════════════════════════════════════
#  REPORT 3: AVAILABLE SUBDIVISIONS BY GEOGRAPHY
# ═══════════════════════════════════════════════════════

@router.get("/{db}/reports/available/{province}/{district}", response_model=List[Dict[str, Any]])
async def report_available_subdivisions(
    db: str,
    province: str,
    district: str,
    mysql_db: Session = Depends(get_mysql_db),
    postgres_db: AsyncSession = Depends(get_postgres_db),
    oracle_db: Session = Depends(get_oracle_db),
    mssql_db: Session = Depends(get_mssql_db),
    mongo_db = Depends(get_mongo_db)
):
    """
    Invokes procedure `sp_available_subdivisions` listing unallocated plots.
    """
    validate_db(db)

    # 1. PostgreSQL (Executes function returning TABLE)
    if db == "postgres":
        result = await postgres_db.execute(text("SELECT * FROM sp_available_subdivisions(:prov, :dist)"), {"prov": province, "dist": district})
        return [dict(row._mapping) for row in result.fetchall()]

    # 2. MongoDB Aggregation
    elif db == "mongodb":
        pipeline = [
            {"$match": {"allocation_status": False}},
            {
                "$lookup": {
                    "from": "stand_survey",
                    "localField": "stand_number",
                    "foreignField": "stand_number",
                    "as": "survey"
                }
            },
            {"$unwind": "$survey"},
            {
                "$match": {
                    "survey.province": province,
                    "survey.district": district
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "subdivision_id": 1,
                    "stand_number": 1,
                    "size_m2": 1,
                    "remarks": 1,
                    "province": "$survey.province",
                    "district": "$survey.district"
                }
            }
        ]
        cursor = mongo_db.stand_subdivisions.aggregate(pipeline)
        results = []
        async for doc in cursor:
            doc["size_m2"] = float(doc["size_m2"].to_decimal())
            results.append(doc)
        return results

    # 3. MySQL
    elif db == "mysql":
        result = mysql_db.execute(text("CALL sp_available_subdivisions(:prov, :dist)"), {"prov": province, "dist": district}).fetchall()
        return [dict(row._mapping) for row in result]

    # 4. Oracle
    elif db == "oracle":
        conn = oracle_db.connection
        cursor = conn.cursor()
        ref_cursor = cursor.var(oracledb.CURSOR)
        cursor.callproc("pkg_land_stand.sp_available_subdivisions", [province, district, ref_cursor])
        col_names = [col[0].lower() for col in ref_cursor.value.description]
        rows = ref_cursor.value.fetchall()
        results = []
        for r in rows:
            results.append(dict(zip(col_names, r)))
        cursor.close()
        return results

    # 5. MS SQL Server
    elif db == "mssql":
        result = mssql_db.execute(text("EXEC sp_available_subdivisions :prov, :dist"), {"prov": province, "dist": district}).fetchall()
        return [dict(row._mapping) for row in result]

# ═══════════════════════════════════════════════════════
#  REPORT 4: DISABILITY RATIO BY PROVINCE VIEW
# ═══════════════════════════════════════════════════════

@router.get("/{db}/reports/disability-summary", response_model=List[Dict[str, Any]])
async def report_disability_summary(
    db: str,
    mysql_db: Session = Depends(get_mysql_db),
    postgres_db: AsyncSession = Depends(get_postgres_db),
    oracle_db: Session = Depends(get_oracle_db),
    mssql_db: Session = Depends(get_mssql_db),
    mongo_db = Depends(get_mongo_db)
):
    """
    Queries view `vw_disability_summary` (PostgreSQL uses Materialized View).
    """
    validate_db(db)

    # 1. PostgreSQL (Queries Materialized View)
    if db == "postgres":
        result = await postgres_db.execute(text("SELECT * FROM vw_disability_summary"))
        return [dict(row._mapping) for row in result.fetchall()]

    # 2. MongoDB Aggregation
    elif db == "mongodb":
        pipeline = [
            {
                "$facet": {
                    "owners": [
                        {"$match": {"disability_status": True}},
                        {"$group": {"_id": "$province", "disabled_owners_count": {"$sum": 1}}}
                    ],
                    "dependents": [
                        {"$match": {"disability_status": True}},
                        {
                            "$lookup": {
                                "from": "stand_owners",
                                "localField": "stand_owner_id",
                                "foreignField": "stand_owner_id",
                                "as": "owner"
                            }
                        },
                        {"$unwind": "$owner"},
                        {"$group": {"_id": "$owner.province", "disabled_dependents_count": {"$sum": 1}}}
                    ]
                }
            }
        ]
        cursor = mongo_db.stand_owners.aggregate(pipeline)
        raw_res = await cursor.to_list(length=1)
        
        # Merge lists of province statistics
        owner_dict = {o["_id"]: o["disabled_owners_count"] for o in raw_res[0]["owners"]} if raw_res else {}
        dep_dict = {d["_id"]: d["disabled_dependents_count"] for d in raw_res[0]["dependents"]} if raw_res else {}
        
        all_provinces = set(list(owner_dict.keys()) + list(dep_dict.keys()))
        results = []
        for p in all_provinces:
            results.append({
                "province": p,
                "disabled_owners_count": owner_dict.get(p, 0),
                "disabled_dependents_count": dep_dict.get(p, 0)
            })
        return results

    # 3. MySQL
    elif db == "mysql":
        result = mysql_db.execute(text("SELECT * FROM vw_disability_summary")).fetchall()
        return [dict(row._mapping) for row in result]

    # 4. Oracle
    elif db == "oracle":
        result = oracle_db.execute(text("SELECT * FROM vw_disability_summary")).fetchall()
        return [dict(row._mapping) for row in result]

    # 5. MS SQL Server
    elif db == "mssql":
        result = mssql_db.execute(text("SELECT * FROM vw_disability_summary")).fetchall()
        return [dict(row._mapping) for row in result]
