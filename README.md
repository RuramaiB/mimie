# Zimbabwe Ministry of Lands — Stand Management System (MCS 504)

An enterprise-grade, high-performance **Multi-DBMS Land Stand Management & Data Governance System** addressing university assignment requirements 2 through 11.

---

## 1. Quick Start Single-Command Deployment

Get the entire application stack running locally in seconds:

```bash
# 1. Navigate to the project directory
cd land_stand_system

# 2. Duplicate the environment configuration template
cp .env.example .env

# 3. Start all containers (FastAPI App, Apache Superset, and trigger the database initializer)
docker compose up -d --build
```

### Accessing the Web Services

- **FastAPI Core Application & HTMX UI Portal:** **[http://localhost:8000](http://localhost:8000)**
- **FastAPI Interactive Swagger REST API Docs:** **[http://localhost:8000/docs](http://localhost:8000/docs)**
- **Apache Superset Dashboard Portal:** **[http://localhost:8088](http://localhost:8088)** *(Admin: `admin` / `Admin1234!`)*

---

## 2. Automated Migration Engine (`db-init`)

Our custom Docker Compose stack includes an automated initialization container (`db-init`) built off the same Python runtime. 
- It actively **waits for all 5 database service ports** (MySQL:3306, Postgres:5432, Oracle:1521, MSSQL:1433, Mongo:27017) to become healthy.
- Once healthy, it automatically parses and runs all SQL and JavaScript schema files (`01_schema.sql` / `01_schema.js`) in sequence.
- Prepopulates all tables with Zimbabwean seed records and executes stored procedures to establish starting allocation records.
- Installs spatial schemas, metadata catalogs, triggers, and auditing mechanisms before gracefully exiting with code `0`.
- Only after successful completion does the main `fastapi-app` container spin up, ensuring no startup connection crashes occur!

---

## 3. Requirements Implementation Mapping Matrix (Q2 – Q11)

| Requirement | Assignment Question Topic | Core Files Addressing Requirement | Key Features Implemented |
|---|---|---|---|
| **Q2** | MongoDB Atlas Link | `mongodb_atlas_sync/atlas_sync.py` | Sync utility migrating local documents to Atlas free tiers. |
| **Q3** | Exact Schemas in 5 DBMS | `sql/mysql/01_schema.sql`<br>`sql/postgres/01_schema.sql`<br>`sql/oracle/01_schema.sql`<br>`sql/mssql/01_schema.sql`<br>`sql/mongodb/01_schema.js` | Schema files creating constraints, tables, and indices. |
| **Q4** | Views, Triggers, Procs | All `01_schema.sql` files | 3 Views, 3 Auditing/Validation Triggers, 3 Stored Procedures. |
| **Q5** | FastAPI Multi-DBMS | `fastapi_app/main.py`<br>`fastapi_app/database/`<br>`fastapi_app/routers/` | Scoped dependency injections targeting specific database engines. |
| **Q6** | Row-Level Security & Auth | `fastapi_app/auth.py`<br>`sql/postgres/01_schema.sql`<br>`sql/mssql/01_schema.sql` | Signed JWT Auth, role guards, Postgres/MSSQL Row-Level Security, rate limiters. |
| **Q7** | Database Optimisations | `docs/optimisation_report.md`<br>`docs/query_plans.md` | GiST/2dsphere spatial indexes, filtered indexes, materialized views, query stores. |
| **Q8** | Governance Metadata | `sql/` catalog tables<br>`fastapi_app/routers/metadata.py`<br>`docs/metadata_strategy.md` | Business data catalog, PII definitions, PII governance JSON API endpoints. |
| **Q9** | HTMX & Leaflet Frontend | `fastapi_app/templates/` (base, stands, owners, dashboard) | Glassmorphic interface with Leaflet maps fed by PostGIS GeoJSON endpoints. |
| **Q10** | PostgreSQL → QGIS Layers | `qgis/qgis_queries.sql`<br>`qgis/qgis_setup_guide.md`<br>`qgis/project_template.qgs` | Centroid points, boundary polygons, color-coded status symbology definitions. |
| **Q11** | Superset Analytics | `superset/docker-compose.superset.yml`<br>`superset/dashboard_queries.sql`<br>`superset/superset_setup_guide.md` | SQL pipelines for stands pie charts, timeline line plots, and disability ratio donuts. |
