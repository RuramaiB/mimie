import sys
import os
import time
import socket
import logging
from sqlalchemy import create_engine, text
from pymongo import MongoClient
from bson.decimal128 import Decimal128
import datetime
import urllib

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("db_init")

# Add parent directory to path so config can be imported
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import settings

def wait_for_port(host: str, port: int, timeout: int = 120):
    """
    Waits for a service port to open.
    """
    start_time = time.time()
    logger.info(f"Waiting for {host}:{port}...")
    while True:
        try:
            with socket.create_connection((host, port), timeout=2):
                logger.info(f"Port {host}:{port} is open!")
                return True
        except (socket.timeout, ConnectionRefusedError):
            if time.time() - start_time > timeout:
                logger.error(f"Timeout waiting for {host}:{port}")
                return False
            time.sleep(2)

def execute_sql_file(engine, filepath: str, split_char: str = ";\n"):
    """
    Reads an SQL file and executes its statements on the engine.
    """
    logger.info(f"Executing SQL file: {filepath}")
    if not os.path.exists(filepath):
        logger.warning(f"File not found: {filepath}")
        return

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # Split statements. Simple split by semicolon.
    # In PL/SQL or T-SQL, statement separators can be 'GO' or '/'.
    # We will handle custom separators if needed.
    statements = []
    if "oracle" in filepath.lower():
        # Oracle blocks separated by '/'
        raw_statements = content.split("\n/\n")
        for stmt in raw_statements:
            stmt = stmt.strip()
            if stmt and not stmt.startswith("--"):
                statements.append(stmt)
    elif "mssql" in filepath.lower():
        # MS SQL statements separated by 'GO'
        raw_statements = content.split("GO")
        for stmt in raw_statements:
            stmt = stmt.strip()
            if stmt and not stmt.startswith("--"):
                statements.append(stmt)
    else:
        # Standard SQL splitting by semicolon
        raw_statements = content.split(";")
        for stmt in raw_statements:
            stmt = stmt.strip()
            if stmt and not stmt.startswith("--"):
                statements.append(stmt)

    with engine.connect() as conn:
        for statement in statements:
            # Skip empty or meta instructions
            if not statement or statement.isspace() or statement.upper().startswith("SET FOREIGN_KEY_CHECKS"):
                continue
            try:
                # Wrap in text()
                conn.execute(text(statement))
            except Exception as e:
                # If table drop fails, ignore
                if "DROP" in statement.upper() or "IF EXISTS" in statement.upper():
                    continue
                logger.error(f"Error executing statement: {statement[:100]}...\nError: {e}")
                raise e
    logger.info(f"Completed execution: {filepath}")

def init_mysql():
    wait_for_port(settings.MYSQL_HOST, settings.MYSQL_PORT)
    # Connect as root/admin to run schema creations
    admin_url = f"mysql+pymysql://{settings.MYSQL_ADMIN_USER}:{settings.MYSQL_ADMIN_PASSWORD}@{settings.MYSQL_HOST}:{settings.MYSQL_PORT}/{settings.MYSQL_DB}"
    engine = create_engine(admin_url)
    sql_path = os.path.join("/app", "sql", "mysql", "01_schema.sql")
    execute_sql_file(engine, sql_path)

def init_postgres():
    wait_for_port(settings.POSTGRES_HOST, settings.POSTGRES_PORT)
    admin_url = f"postgresql+psycopg2://{settings.POSTGRES_ADMIN_USER}:{settings.POSTGRES_ADMIN_PASSWORD}@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
    engine = create_engine(admin_url)
    sql_path = os.path.join("/app", "sql", "postgres", "01_schema.sql")
    execute_sql_file(engine, sql_path)

def init_oracle():
    wait_for_port(settings.ORACLE_HOST, settings.ORACLE_PORT)
    # Using oracledb thin mode admin
    admin_url = f"oracle+oracledb://{settings.ORACLE_ADMIN_USER}:{settings.ORACLE_ADMIN_PASSWORD}@{settings.ORACLE_HOST}:{settings.ORACLE_PORT}/?service_name={settings.ORACLE_SERVICE}"
    engine = create_engine(admin_url)
    sql_path = os.path.join("/app", "sql", "oracle", "01_schema.sql")
    execute_sql_file(engine, sql_path)

def init_mssql():
    wait_for_port(settings.MSSQL_HOST, settings.MSSQL_PORT)
    
    # 1. Connect to master database to verify/create target database
    params_master = urllib.parse.quote_plus(
        f"DRIVER={{ODBC Driver 18 for SQL Server}};"
        f"SERVER={settings.MSSQL_HOST},{settings.MSSQL_PORT};"
        f"DATABASE=master;"
        f"UID={settings.MSSQL_ADMIN_USER};"
        f"PWD={settings.MSSQL_ADMIN_PASSWORD};"
        f"Encrypt=yes;"
        f"TrustServerCertificate=yes;"
    )
    master_url = f"mssql+pyodbc:///?odbc_connect={params_master}"
    master_engine = create_engine(master_url, isolation_level="AUTOCOMMIT")
    
    with master_engine.connect() as conn:
        db_name = settings.MSSQL_DB
        exists = conn.execute(
            text("SELECT database_id FROM sys.databases WHERE name = :db_name"),
            {"db_name": db_name}
        ).fetchone()
        
        if not exists:
            logger.info(f"MSSQL database '{db_name}' does not exist. Creating database...")
            # Bracket wrap to securely support hyphenated names
            conn.execute(text(f"CREATE DATABASE [{db_name}]"))
            logger.info(f"MSSQL database '{db_name}' created successfully.")

    # 2. Connect to the initialized database to run the schema definitions
    params = urllib.parse.quote_plus(
        f"DRIVER={{ODBC Driver 18 for SQL Server}};"
        f"SERVER={settings.MSSQL_HOST},{settings.MSSQL_PORT};"
        f"DATABASE={settings.MSSQL_DB};"
        f"UID={settings.MSSQL_ADMIN_USER};"
        f"PWD={settings.MSSQL_ADMIN_PASSWORD};"
        f"Encrypt=yes;"
        f"TrustServerCertificate=yes;"
    )
    admin_url = f"mssql+pyodbc:///?odbc_connect={params}"
    engine = create_engine(admin_url)
    sql_path = os.path.join("/app", "sql", "mssql", "01_schema.sql")
    execute_sql_file(engine, sql_path)

def init_mongodb():
    wait_for_port(settings.MONGO_HOST, settings.MONGO_PORT)
    admin_uri = f"mongodb://{settings.MONGO_ADMIN_USER}:{settings.MONGO_ADMIN_PASSWORD}@{settings.MONGO_HOST}:{settings.MONGO_PORT}/?authSource={settings.MONGO_AUTH_DB}"
    client = MongoClient(admin_uri)
    db = client[settings.MONGO_DB]

    # Drop collections to make it idempotent
    for col in ["stands", "stand_survey", "stand_subdivisions", "stand_owners", "dependents", "stand_allocations", "metadata_catalogue"]:
        db[col].drop()

    # Create collection stands with Schema Validation
    db.create_collection("stands", validator={
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["stand_number", "location", "size_m2", "activity", "gps_coordinates", "location_city"],
            "properties": {
                "stand_number": {"bsonType": "string"},
                "location": {"bsonType": "string"},
                "size_m2": {"bsonType": "decimal"},
                "activity": {"enum": ["Residential", "Commercial"]},
                "picture_url": {"bsonType": ["string", "null"]},
                "gps_coordinates": {
                    "bsonType": "object",
                    "required": ["type", "coordinates"],
                    "properties": {
                        "type": {"enum": ["Polygon"]},
                        "coordinates": {"bsonType": "array"}
                    }
                },
                "location_city": {"bsonType": "string"}
            }
        }
    })
    db.stands.create_index([("gps_coordinates", "2dsphere")])
    db.stands.create_index([("location", "text")])
    db.stands.create_index([("stand_number", 1)], unique=True)

    # Create stand_survey
    db.create_collection("stand_survey")
    db.stand_survey.create_index([("province", 1), ("district", 1)])

    # Create subdivisions
    db.create_collection("stand_subdivisions")
    db.stand_subdivisions.create_index([("subdivision_id", 1)], unique=True)
    db.stand_subdivisions.create_index(
        [("subdivision_id", 1), ("size_m2", 1)],
        partialFilterExpression={"allocation_status": False}
    )

    # Create owners
    db.create_collection("stand_owners")
    db.stand_owners.create_index([("stand_owner_id", 1)], unique=True)
    db.stand_owners.create_index([("province", 1), ("district", 1)])

    # Create dependents
    db.create_collection("dependents")

    # Create allocations
    db.create_collection("stand_allocations")
    db.stand_allocations.create_index([("allocation_id", 1)], unique=True)

    # Metadata catalogue
    db.create_collection("metadata_catalogue")

    # Seed stands
    db.stands.insert_many([
        {
            "stand_number": "STD-HAR-001",
            "location": "Borrowdale Brooke Golf Estate, Section A",
            "size_m2": Decimal128("4000.00"),
            "activity": "Residential",
            "picture_url": "http://images.lands.gov.zw/stands/std-har-001.png",
            "gps_coordinates": {
                "type": "Polygon",
                "coordinates": [[[31.111, -17.722], [31.115, -17.722], [31.115, -17.726], [31.111, -17.726], [31.111, -17.722]]]
            },
            "location_city": "Harare"
        },
        {
            "stand_number": "STD-BUL-002",
            "location": "Suburbs Road Near Ascot Mall",
            "size_m2": Decimal128("3000.00"),
            "activity": "Residential",
            "picture_url": "http://images.lands.gov.zw/stands/std-bul-002.png",
            "gps_coordinates": {
                "type": "Polygon",
                "coordinates": [[[28.601, -20.155], [28.605, -20.155], [28.605, -20.159], [28.601, -20.159], [28.601, -20.155]]]
            },
            "location_city": "Bulawayo"
        },
        {
            "stand_number": "STD-MUT-003",
            "location": "Chitepo Main Street Boulevard Commercial Hub",
            "size_m2": Decimal128("7500.00"),
            "activity": "Commercial",
            "picture_url": "http://images.lands.gov.zw/stands/std-mut-003.png",
            "gps_coordinates: ": {
                "type": "Polygon",
                "coordinates": [[[32.668, -18.971], [32.674, -18.971], [32.674, -18.976], [32.668, -18.976], [32.668, -18.971]]]
            },
            "location_city": "Mutare"
        },
        {
            "stand_number": "STD-GWE-004",
            "location": "Senga Industrial Area Main Bypass",
            "size_m2": Decimal128("12000.00"),
            "activity": "Commercial",
            "picture_url": "http://images.lands.gov.zw/stands/std-gwe-004.png",
            "gps_coordinates": {
                "type": "Polygon",
                "coordinates": [[[29.831, -19.461], [29.841, -19.461], [29.841, -19.469], [29.831, -19.469], [29.831, -19.461]]]
            },
            "location_city": "Gweru"
        },
        {
            "stand_number": "STD-MAS-005",
            "location": "Rhodene High-density Layout Block D",
            "size_m2": Decimal128("2500.00"),
            "activity": "Residential",
            "picture_url": "http://images.lands.gov.zw/stands/std-mas-005.png",
            "gps_coordinates": {
                "type": "Polygon",
                "coordinates": [[[30.825, -20.065], [30.829, -20.065], [30.829, -20.069], [30.825, -20.069], [30.825, -20.065]]]
            },
            "location_city": "Masvingo"
        }
    ])

    # Seed surveys
    db.stand_survey.insert_many([
        {"stand_number": "STD-HAR-001", "survey_status": True, "province": "Harare", "district": "Harare Central"},
        {"stand_number": "STD-BUL-002", "survey_status": True, "province": "Bulawayo", "district": "Bulawayo Central"},
        {"stand_number": "STD-MUT-003", "survey_status": True, "province": "Manicaland", "district": "Mutare"},
        {"stand_number": "STD-GWE-004", "survey_status": True, "province": "Midlands", "district": "Gweru"},
        {"stand_number": "STD-MAS-005", "survey_status": True, "province": "Masvingo", "district": "Masvingo"}
    ])

    # Seed subdivisions
    db.stand_subdivisions.insert_many([
        {"subdivision_id": 1, "stand_number": "STD-HAR-001", "allocation_status": True, "size_m2": Decimal128("1500.00"), "remarks": "Divided Brooke plot East Wing"},
        {"subdivision_id": 2, "stand_number": "STD-HAR-001", "allocation_status": False, "size_m2": Decimal128("2000.00"), "remarks": "Divided Brooke plot West Wing"},
        {"subdivision_id": 3, "stand_number": "STD-BUL-002", "allocation_status": True, "size_m2": Decimal128("1200.00"), "remarks": "Ascot subdiv Sector 1"},
        {"subdivision_id": 4, "stand_number": "STD-BUL-002", "allocation_status": False, "size_m2": Decimal128("1500.00"), "remarks": "Ascot subdiv Sector 2"},
        {"subdivision_id": 5, "stand_number": "STD-MUT-003", "allocation_status": True, "size_m2": Decimal128("3500.00"), "remarks": "Commercial plaza division North"},
        {"subdivision_id": 6, "stand_number": "STD-MUT-003", "allocation_status": False, "size_m2": Decimal128("3000.00"), "remarks": "Commercial plaza division South"},
        {"subdivision_id": 7, "stand_number": "STD-GWE-004", "allocation_status": True, "size_m2": Decimal128("6000.00"), "remarks": "Senga Heavy Yard Subdivision A"},
        {"subdivision_id": 8, "stand_number": "STD-MAS-005", "allocation_status": True, "size_m2": Decimal128("1000.00"), "remarks": "Rhodene Corner Lot A"},
        {"subdivision_id": 9, "stand_number": "STD-MAS-005", "allocation_status": False, "size_m2": Decimal128("1200.00"), "remarks": "Rhodene Corner Lot B"}
    ])

    # Seed owners
    db.stand_owners.insert_many([
        {"stand_owner_id": 1, "firstname": "Tendai Mupfumi", "date_of_birth": datetime.datetime(1980, 4, 12), "gender": "Male", "disability_status": False, "province": "Harare", "district": "Harare Central"},
        {"stand_owner_id": 2, "firstname": "Chipo Sibanda", "date_of_birth": datetime.datetime(1988, 11, 23), "gender": "Female", "disability_status": True, "province": "Bulawayo", "district": "Bulawayo Central"},
        {"stand_owner_id": 3, "firstname": "Farai Mutasa", "date_of_birth": datetime.datetime(1975, 6, 30), "gender": "Male", "disability_status": False, "province": "Manicaland", "district": "Mutare"},
        {"stand_owner_id": 4, "firstname": "Nyarai Zhou", "date_of_birth": datetime.datetime(1992, 1, 15), "gender": "Female", "disability_status": False, "province": "Midlands", "district": "Gweru"},
        {"stand_owner_id": 5, "firstname": "Tinashe Moyo", "date_of_birth": datetime.datetime(1982, 8, 5), "gender": "Male", "disability_status": True, "province": "Masvingo", "district": "Masvingo"}
    ])

    # Seed dependents
    db.dependents.insert_many([
        {"stand_owner_id": 1, "firstname": "Rufaro Mupfumi", "date_of_birth": datetime.datetime(2010, 5, 14), "gender": "Female", "disability_status": False},
        {"stand_owner_id": 1, "firstname": "Kundai Mupfumi", "date_of_birth": datetime.datetime(2015, 9, 20), "gender": "Male", "disability_status": False},
        {"stand_owner_id": 2, "firstname": "Lindiwe Sibanda", "date_of_birth": datetime.datetime(2012, 3, 4), "gender": "Female", "disability_status": True},
        {"stand_owner_id": 3, "firstname": "Tariro Mutasa", "date_of_birth": datetime.datetime(2008, 7, 22), "gender": "Female", "disability_status": False},
        {"stand_owner_id": 5, "firstname": "Tatenda Moyo", "date_of_birth": datetime.datetime(2014, 12, 1), "gender": "Male", "disability_status": False}
    ])

    # Seed allocations
    db.stand_allocations.insert_many([
        {"allocation_id": 1, "stand_owner_id": 1, "subdivision_id": 1, "date_of_allocation": datetime.datetime(2026, 1, 10), "price_per_m2": Decimal128("150.00")},
        {"allocation_id": 2, "stand_owner_id": 2, "subdivision_id": 3, "date_of_allocation": datetime.datetime(2026, 2, 15), "price_per_m2": Decimal128("120.00")},
        {"allocation_id": 3, "stand_owner_id": 3, "subdivision_id": 5, "date_of_allocation": datetime.datetime(2026, 3, 20), "price_per_m2": Decimal128("200.00")},
        {"allocation_id": 4, "stand_owner_id": 4, "subdivision_id": 7, "date_of_allocation": datetime.datetime(2026, 4, 18), "price_per_m2": Decimal128("85.00")},
        {"allocation_id": 5, "stand_owner_id": 5, "subdivision_id": 8, "date_of_allocation": datetime.datetime(2026, 5, 12), "price_per_m2": Decimal128("110.00")}
    ])

    # Seed metadata
    db.metadata_catalogue.insert_many([
        {"table_name": "stands", "column_name": "stand_number", "data_type": "string", "is_pii": False, "data_classification": "Public"},
        {"table_name": "stands", "column_name": "gps_coordinates", "data_type": "geojson", "is_pii": False, "data_classification": "Internal"},
        {"table_name": "stand_owners", "column_name": "firstname", "data_type": "string", "is_pii": True, "data_classification": "Confidential"},
        {"table_name": "stand_owners", "column_name": "date_of_birth", "data_type": "date", "is_pii": True, "data_classification": "Confidential"}
    ])

    logger.info("MongoDB seed successfully applied via PyMongo!")

def main():
    logger.info("Starting Multi-DBMS Initialization sequence...")
    
    # 1. MySQL
    try:
        init_mysql()
        logger.info("MySQL Initialized successfully!")
    except Exception as e:
        logger.error(f"MySQL Init Failed: {e}")
        sys.exit(1)

    # 2. PostgreSQL
    try:
        init_postgres()
        logger.info("PostgreSQL Initialized successfully!")
    except Exception as e:
        logger.error(f"PostgreSQL Init Failed: {e}")
        sys.exit(1)

    # 3. Oracle
    try:
        init_oracle()
        logger.info("Oracle Initialized successfully!")
    except Exception as e:
        logger.error(f"Oracle Init Failed: {e}")
        sys.exit(1)

    # 4. MS SQL
    try:
        init_mssql()
        logger.info("MS SQL Server Initialized successfully!")
    except Exception as e:
        logger.error(f"MS SQL Server Init Failed: {e}")
        sys.exit(1)

    # 5. MongoDB
    try:
        init_mongodb()
        logger.info("MongoDB Initialized successfully!")
    except Exception as e:
        logger.error(f"MongoDB Init Failed: {e}")
        sys.exit(1)

    logger.info("Multi-DBMS Initialization completed successfully. All schemas populated!")

if __name__ == "__main__":
    main()
