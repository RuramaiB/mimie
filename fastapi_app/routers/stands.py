from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select
from typing import List, Optional
from config import settings

from database.mysql_db import get_mysql_db
from database.postgres_db import get_postgres_db
from database.oracle_db import get_oracle_db
from database.mssql_db import get_mssql_db
from database.mongo_db import get_mongo_db

from models.pydantic_models import StandCreate, StandResponse
from models.sqlalchemy_models import StandORM
from auth import get_current_user, RoleGuard

router = APIRouter(tags=["Land Stands Management"])

# Helper validation for DBMS parameter
def validate_db(db: str):
    if db not in ("mysql", "postgres", "oracle", "mssql", "mongodb"):
        raise HTTPException(status_code=400, detail="Invalid DBMS target. Must be mysql, postgres, oracle, mssql, or mongodb")

@router.get("/{db}/stands/", response_model=List[StandResponse])
async def list_stands(
    db: str,
    skip: int = 0,
    limit: int = 100,
    mysql_db: Session = Depends(get_mysql_db),
    postgres_db: AsyncSession = Depends(get_postgres_db),
    oracle_db: Session = Depends(get_oracle_db),
    mssql_db: Session = Depends(get_mssql_db),
    mongo_db = Depends(get_mongo_db)
):
    """
    Lists all land stands across any targeted database platform with pagination.
    """
    validate_db(db)

    # 1. PostgreSQL (Async Engine + PostGIS)
    if db == "postgres":
        # Select spatial boundary as WKT
        query = text("SELECT stand_number, location, size_m2, activity, picture_url, ST_AsText(gps_coordinates) AS gps_coordinates, location_city, created_at FROM stands OFFSET :skip LIMIT :limit")
        result = await postgres_db.execute(query, {"skip": skip, "limit": limit})
        stands = []
        for row in result.fetchall():
            stands.append(StandResponse(
                stand_number=row.stand_number,
                location=row.location,
                size_m2=float(row.size_m2),
                activity=row.activity,
                picture_url=row.picture_url,
                gps_coordinates=row.gps_coordinates,
                location_city=row.location_city,
                created_at=row.created_at
            ))
        return stands

    # 2. MongoDB (Async Motor)
    elif db == "mongodb":
        cursor = mongo_db.stands.find().skip(skip).limit(limit)
        stands = []
        async for doc in cursor:
            # Format gps_coordinates (GeoJSON polygon to WKT approximation for response consistency)
            coords = doc["gps_coordinates"]["coordinates"][0]
            wkt = f"POLYGON(({', '.join(f'{pt[0]} {pt[1]}' for pt in coords)}))"
            stands.append(StandResponse(
                stand_number=doc["stand_number"],
                location=doc["location"],
                size_m2=float(doc["size_m2"].to_decimal()),
                activity=doc["activity"],
                picture_url=doc.get("picture_url"),
                gps_coordinates=wkt,
                location_city=doc["location_city"]
            ))
        return stands

    # 3. MySQL (Sync ORM)
    elif db == "mysql":
        db_stands = mysql_db.query(StandORM).offset(skip).limit(limit).all()
        return [StandResponse.model_validate(s) for s in db_stands]

    # 4. Oracle (Sync ORM)
    elif db == "oracle":
        db_stands = oracle_db.query(StandORM).offset(skip).limit(limit).all()
        return [StandResponse.model_validate(s) for s in db_stands]

    # 5. MS SQL Server (Sync + Spatial STAsText)
    elif db == "mssql":
        query = text("SELECT stand_number, location, size_m2, activity, picture_url, gps_coordinates.STAsText() AS gps_coordinates, location_city, created_at FROM stands ORDER BY stand_number OFFSET :skip ROWS FETCH NEXT :limit ROWS ONLY")
        result = mssql_db.execute(query, {"skip": skip, "limit": limit})
        stands = []
        for row in result.fetchall():
            stands.append(StandResponse(
                stand_number=row.stand_number,
                location=row.location,
                size_m2=float(row.size_m2),
                activity=row.activity,
                picture_url=row.picture_url,
                gps_coordinates=row.gps_coordinates,
                location_city=row.location_city,
                created_at=row.created_at
            ))
        return stands

@router.get("/{db}/stands/{stand_number}", response_model=StandResponse)
async def get_stand(
    db: str,
    stand_number: str,
    mysql_db: Session = Depends(get_mysql_db),
    postgres_db: AsyncSession = Depends(get_postgres_db),
    oracle_db: Session = Depends(get_oracle_db),
    mssql_db: Session = Depends(get_mssql_db),
    mongo_db = Depends(get_mongo_db)
):
    """
    Fetches details of a single land stand.
    """
    validate_db(db)

    if db == "postgres":
        query = text("SELECT stand_number, location, size_m2, activity, picture_url, ST_AsText(gps_coordinates) AS gps_coordinates, location_city, created_at FROM stands WHERE stand_number = :num")
        result = await postgres_db.execute(query, {"num": stand_number})
        row = result.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Stand not found")
        return StandResponse(
            stand_number=row.stand_number,
            location=row.location,
            size_m2=float(row.size_m2),
            activity=row.activity,
            picture_url=row.picture_url,
            gps_coordinates=row.gps_coordinates,
            location_city=row.location_city,
            created_at=row.created_at
        )

    elif db == "mongodb":
        doc = await mongo_db.stands.find_one({"stand_number": stand_number})
        if not doc:
            raise HTTPException(status_code=404, detail="Stand not found")
        coords = doc["gps_coordinates"]["coordinates"][0]
        wkt = f"POLYGON(({', '.join(f'{pt[0]} {pt[1]}' for pt in coords)}))"
        return StandResponse(
            stand_number=doc["stand_number"],
            location=doc["location"],
            size_m2=float(doc["size_m2"].to_decimal()),
            activity=doc["activity"],
            picture_url=doc.get("picture_url"),
            gps_coordinates=wkt,
            location_city=doc["location_city"]
        )

    elif db == "mysql":
        s = mysql_db.query(StandORM).filter(StandORM.stand_number == stand_number).first()
        if not s:
            raise HTTPException(status_code=404, detail="Stand not found")
        return StandResponse.model_validate(s)

    elif db == "oracle":
        s = oracle_db.query(StandORM).filter(StandORM.stand_number == stand_number).first()
        if not s:
            raise HTTPException(status_code=404, detail="Stand not found")
        return StandResponse.model_validate(s)

    elif db == "mssql":
        query = text("SELECT stand_number, location, size_m2, activity, picture_url, gps_coordinates.STAsText() AS gps_coordinates, location_city, created_at FROM stands WHERE stand_number = :num")
        result = mssql_db.execute(query, {"num": stand_number})
        row = result.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Stand not found")
        return StandResponse(
            stand_number=row.stand_number,
            location=row.location,
            size_m2=float(row.size_m2),
            activity=row.activity,
            picture_url=row.picture_url,
            gps_coordinates=row.gps_coordinates,
            location_city=row.location_city,
            created_at=row.created_at
        )

@router.post("/{db}/stands/", response_model=StandResponse, status_code=210)
async def create_stand(
    db: str,
    payload: StandCreate,
    mysql_db: Session = Depends(get_mysql_db),
    postgres_db: AsyncSession = Depends(get_postgres_db),
    oracle_db: Session = Depends(get_oracle_db),
    mssql_db: Session = Depends(get_mssql_db),
    mongo_db = Depends(get_mongo_db),
    current_user = Depends(RoleGuard(["land_app", "land_admin"]))
):
    """
    Registers a new stand (Requires land_app or land_admin role).
    """
    validate_db(db)

    # Coordinates payload could be WKT string
    gps_str = payload.gps_coordinates if isinstance(payload.gps_coordinates, str) else ""

    if db == "postgres":
        query = text("INSERT INTO stands (stand_number, location, size_m2, activity, picture_url, gps_coordinates, location_city) VALUES (:stand_number, :location, :size_m2, :activity, :picture_url, ST_GeomFromText(:coords, 4326), :location_city)")
        await postgres_db.execute(query, {
            "stand_number": payload.stand_number,
            "location": payload.location,
            "size_m2": payload.size_m2,
            "activity": payload.activity,
            "picture_url": payload.picture_url,
            "coords": gps_str,
            "location_city": payload.location_city
        })
        await postgres_db.commit()
        return StandResponse(
            stand_number=payload.stand_number,
            location=payload.location,
            size_m2=payload.size_m2,
            activity=payload.activity,
            picture_url=payload.picture_url,
            gps_coordinates=payload.gps_coordinates,
            location_city=payload.location_city
        )

    elif db == "mongodb":
        # Parse WKT to GeoJSON if WKT is provided
        # e.g., POLYGON((31.111 -17.722, ...))
        from bson.decimal128 import Decimal128
        coords_list = []
        if gps_str:
            match = re.search(r"\(\((.*?)\)\)", gps_str)
            if match:
                pts = match.group(1).split(",")
                coords_list = [[[float(c.split()[0]), float(c.split()[1])] for c in pts]]
        else:
            coords_list = payload.gps_coordinates.coordinates

        doc = {
            "stand_number": payload.stand_number,
            "location": payload.location,
            "size_m2": Decimal128(str(payload.size_m2)),
            "activity": payload.activity,
            "picture_url": payload.picture_url,
            "gps_coordinates": {
                "type": "Polygon",
                "coordinates": coords_list
            },
            "location_city": payload.location_city
        }
        await mongo_db.stands.insert_one(doc)
        return StandResponse(
            stand_number=payload.stand_number,
            location=payload.location,
            size_m2=payload.size_m2,
            activity=payload.activity,
            picture_url=payload.picture_url,
            gps_coordinates=payload.gps_coordinates,
            location_city=payload.location_city
        )

    elif db in ("mysql", "oracle"):
        orm_db = mysql_db if db == "mysql" else oracle_db
        s = StandORM(
            stand_number=payload.stand_number,
            location=payload.location,
            size_m2=payload.size_m2,
            activity=payload.activity,
            picture_url=payload.picture_url,
            gps_coordinates=gps_str,
            location_city=payload.location_city
        )
        orm_db.add(s)
        orm_db.commit()
        return StandResponse.model_validate(s)

    elif db == "mssql":
        query = text("INSERT INTO stands (stand_number, location, size_m2, activity, picture_url, gps_coordinates, location_city) VALUES (:stand_number, :location, :size_m2, :activity, :picture_url, geography::STGeomFromText(:coords, 4326), :location_city)")
        mssql_db.execute(query, {
            "stand_number": payload.stand_number,
            "location": payload.location,
            "size_m2": payload.size_m2,
            "activity": payload.activity,
            "picture_url": payload.picture_url,
            "coords": gps_str,
            "location_city": payload.location_city
        })
        mssql_db.commit()
        return StandResponse(
            stand_number=payload.stand_number,
            location=payload.location,
            size_m2=payload.size_m2,
            activity=payload.activity,
            picture_url=payload.picture_url,
            gps_coordinates=payload.gps_coordinates,
            location_city=payload.location_city
        )

# ═══════════════════════════════════════════════════════
#  Q10 GIS GEOJSON ENDPOINTS (POSTGIS LAYERS)
# ═══════════════════════════════════════════════════════

import json

@router.get("/postgres/gis/stands-geojson")
async def get_stands_geojson(postgres_db: AsyncSession = Depends(get_postgres_db)):
    """
    Returns PostGIS boundaries of stands represented as a standard GeoJSON FeatureCollection.
    """
    query = text("SELECT stand_number, location, size_m2, activity, location_city, ST_AsGeoJSON(gps_coordinates) AS geom FROM stands")
    result = await postgres_db.execute(query)
    
    features = []
    for row in result.fetchall():
        geom_dict = json.loads(row.geom)
        features.append({
            "type": "Feature",
            "geometry": geom_dict,
            "properties": {
                "stand_number": row.stand_number,
                "location": row.location,
                "size_m2": float(row.size_m2),
                "activity": row.activity,
                "location_city": row.location_city
            }
        })
        
    return {
        "type": "FeatureCollection",
        "features": features
    }

@router.get("/postgres/gis/subdivisions-geojson")
async def get_subdivisions_geojson(postgres_db: AsyncSession = Depends(get_postgres_db)):
    """
    Returns PostGIS boundaries of subdivided plots colored by active allocation status.
    """
    query = text(
        "SELECT sub.subdivision_id, sub.allocation_status, sub.size_m2, s.stand_number, s.location, ST_AsGeoJSON(s.gps_coordinates) AS geom "
        "FROM stand_subdivisions sub "
        "JOIN stands s ON sub.stand_number = s.stand_number"
    )
    result = await postgres_db.execute(query)
    
    features = []
    for row in result.fetchall():
        geom_dict = json.loads(row.geom)
        status_color = "#E53E3E" if row.allocation_status else "#38A169"  # Red if allocated, Green if free
        features.append({
            "type": "Feature",
            "geometry": geom_dict,
            "properties": {
                "subdivision_id": row.subdivision_id,
                "stand_number": row.stand_number,
                "allocation_status": row.allocation_status,
                "size_m2": float(row.size_m2),
                "location": row.location,
                "fill": status_color,
                "color": "#2D3748"
            }
        })
        
    return {
        "type": "FeatureCollection",
        "features": features
    }

import re

@router.put("/{db}/stands/{stand_number}", response_model=StandResponse)
async def update_stand(
    db: str,
    stand_number: str,
    payload: StandCreate,
    mysql_db: Session = Depends(get_mysql_db),
    postgres_db: AsyncSession = Depends(get_postgres_db),
    oracle_db: Session = Depends(get_oracle_db),
    mssql_db: Session = Depends(get_mssql_db),
    mongo_db = Depends(get_mongo_db),
    current_user = Depends(RoleGuard(["land_app", "land_admin"]))
):
    """
    Updates an existing stand (Requires land_app or land_admin role).
    """
    validate_db(db)
    gps_str = payload.gps_coordinates if isinstance(payload.gps_coordinates, str) else ""

    if db == "postgres":
        query = text("UPDATE stands SET location = :location, size_m2 = :size_m2, activity = :activity, picture_url = :picture_url, gps_coordinates = ST_GeomFromText(:coords, 4326), location_city = :location_city WHERE stand_number = :stand_number")
        await postgres_db.execute(query, {
            "location": payload.location,
            "size_m2": payload.size_m2,
            "activity": payload.activity,
            "picture_url": payload.picture_url,
            "coords": gps_str,
            "location_city": payload.location_city,
            "stand_number": stand_number
        })
        await postgres_db.commit()
        return StandResponse(
            stand_number=stand_number,
            location=payload.location,
            size_m2=payload.size_m2,
            activity=payload.activity,
            picture_url=payload.picture_url,
            gps_coordinates=payload.gps_coordinates,
            location_city=payload.location_city
        )

    elif db == "mongodb":
        from bson.decimal128 import Decimal128
        coords_list = []
        if gps_str:
            match = re.search(r"\(\((.*?)\)\)", gps_str)
            if match:
                pts = match.group(1).split(",")
                coords_list = [[[float(c.split()[0]), float(c.split()[1])] for c in pts]]
        else:
            coords_list = payload.gps_coordinates.coordinates

        await mongo_db.stands.update_one(
            {"stand_number": stand_number},
            {"$set": {
                "location": payload.location,
                "size_m2": Decimal128(str(payload.size_m2)),
                "activity": payload.activity,
                "picture_url": payload.picture_url,
                "gps_coordinates": {
                    "type": "Polygon",
                    "coordinates": coords_list
                },
                "location_city": payload.location_city
            }}
        )
        return StandResponse(
            stand_number=stand_number,
            location=payload.location,
            size_m2=payload.size_m2,
            activity=payload.activity,
            picture_url=payload.picture_url,
            gps_coordinates=payload.gps_coordinates,
            location_city=payload.location_city
        )

    elif db in ("mysql", "oracle"):
        orm_db = mysql_db if db == "mysql" else oracle_db
        s = orm_db.query(StandORM).filter(StandORM.stand_number == stand_number).first()
        if not s:
            raise HTTPException(status_code=404, detail="Stand not found")
        s.location = payload.location
        s.size_m2 = payload.size_m2
        s.activity = payload.activity
        s.picture_url = payload.picture_url
        s.gps_coordinates = gps_str
        s.location_city = payload.location_city
        orm_db.commit()
        return StandResponse.model_validate(s)

    elif db == "mssql":
        query = text("UPDATE stands SET location = :location, size_m2 = :size_m2, activity = :activity, picture_url = :picture_url, gps_coordinates = geography::STGeomFromText(:coords, 4326), location_city = :location_city WHERE stand_number = :stand_number")
        mssql_db.execute(query, {
            "location": payload.location,
            "size_m2": payload.size_m2,
            "activity": payload.activity,
            "picture_url": payload.picture_url,
            "coords": gps_str,
            "location_city": payload.location_city,
            "stand_number": stand_number
        })
        mssql_db.commit()
        return StandResponse(
            stand_number=stand_number,
            location=payload.location,
            size_m2=payload.size_m2,
            activity=payload.activity,
            picture_url=payload.picture_url,
            gps_coordinates=payload.gps_coordinates,
            location_city=payload.location_city
        )

@router.delete("/{db}/stands/{stand_number}", status_code=204)
async def delete_stand(
    db: str,
    stand_number: str,
    mysql_db: Session = Depends(get_mysql_db),
    postgres_db: AsyncSession = Depends(get_postgres_db),
    oracle_db: Session = Depends(get_oracle_db),
    mssql_db: Session = Depends(get_mssql_db),
    mongo_db = Depends(get_mongo_db),
    current_user = Depends(RoleGuard(["land_app", "land_admin"]))
):
    """
    Deletes an existing stand (Requires land_app or land_admin role).
    """
    validate_db(db)

    if db == "postgres":
        query = text("DELETE FROM stands WHERE stand_number = :stand_number")
        await postgres_db.execute(query, {"stand_number": stand_number})
        await postgres_db.commit()

    elif db == "mongodb":
        await mongo_db.stands.delete_one({"stand_number": stand_number})

    elif db in ("mysql", "oracle"):
        orm_db = mysql_db if db == "mysql" else oracle_db
        s = orm_db.query(StandORM).filter(StandORM.stand_number == stand_number).first()
        if s:
            orm_db.delete(s)
            orm_db.commit()

    elif db == "mssql":
        query = text("DELETE FROM stands WHERE stand_number = :stand_number")
        mssql_db.execute(query, {"stand_number": stand_number})
        mssql_db.commit()

    return None


