from fastapi import APIRouter
from database.mysql_db import check_mysql_health
from database.postgres_db import check_postgres_health
from database.oracle_db import check_oracle_health
from database.mssql_db import check_mssql_health
from database.mongo_db import check_mongo_health

router = APIRouter(prefix="/health", tags=["System Health"])

@router.get("")
async def get_health_status():
    """
    Consolidated Health endpoint verifying connectivity state across all 5 DBMS instances.
    """
    mysql_ok = check_mysql_health()
    postgres_ok = await check_postgres_health()
    oracle_ok = check_oracle_health()
    mssql_ok = check_mssql_health()
    mongo_ok = await check_mongo_health()

    overall_status = "HEALTHY" if all([mysql_ok, postgres_ok, oracle_ok, mssql_ok, mongo_ok]) else "DEGRADED"

    return {
        "status": overall_status,
        "services": {
            "mysql": "UP" if mysql_ok else "DOWN",
            "postgresql_postgis": "UP" if postgres_ok else "DOWN",
            "oracle_xe": "UP" if oracle_ok else "DOWN",
            "mssql_server": "UP" if mssql_ok else "DOWN",
            "mongodb": "UP" if mongo_ok else "DOWN"
        }
    }
