# Apache Superset Dashboard Integration Guide

This guide details how to spin up Apache Superset, establish a connection to our PostgreSQL database, and build the 4 required analytical charts for the Ministry of Lands dashboard.

---

## 1. Quick Start Commands

If running Superset via our `docker-compose.yml` or `docker-compose.superset.yml`, initialize the container with these commands:

```bash
# 1. Initialize the internal metadata database in Superset
docker compose exec superset superset db upgrade

# 2. Create the administrator account
docker compose exec superset superset fab create-admin \
    --username admin \
    --firstname Admin \
    --lastname User \
    --email admin@lands.gov.zw \
    --password Admin1234!

# 3. Load default roles and permissions
docker compose exec superset superset init
```

Open your browser and navigate to: **[http://localhost:8088](http://localhost:8088)**. Login using `admin` / `Admin1234!`.

---

## 2. Connecting Superset to PostgreSQL

Since Superset joins the same `dbnet` Docker network, use the following connection parameter:

1. In the top-right menu, select **+** → **Data** → **Connect Database**.
2. Select **PostgreSQL** from the supported databases.
3. Enter the SQL-Alchemy URI:
   ```text
   postgresql://admin:Admin1234!@postgres-db:5432/devdb
   ```
4. Click **Connect** and save.

---

## 3. Creating the Dashboard Charts

Use the SQL Lab tool inside Superset to load our pre-built queries:

### Chart 1: Stands by Activity Type (Pie Chart)
- **SQL Source:** [dashboard_queries.sql](file:///c:/Users/rbotso.ZBFH/Desktop/mimie/land_stand_system/superset/dashboard_queries.sql#L7-L13)
- **Chart Type:** Pie Chart
- **Dimensions:** `activity_type`
- **Metric:** `SUM(total_footprint_m2)` or `SUM(stands_count)`

### Chart 2: Allocations Over Time (Line Chart)
- **SQL Source:** [dashboard_queries.sql](file:///c:/Users/rbotso.ZBFH/Desktop/mimie/land_stand_system/superset/dashboard_queries.sql#L18-L28)
- **Chart Type:** Line Chart
- **Time Column:** `allocation_month`
- **Metrics:** `SUM(total_allocation_usd)` (Total Value Allocated) and `SUM(allocation_count)` (Allotments Count)

### Chart 3: Owners by Province (Bar Chart)
- **SQL Source:** [dashboard_queries.sql](file:///c:/Users/rbotso.ZBFH/Desktop/mimie/land_stand_system/superset/dashboard_queries.sql#L33-L41)
- **Chart Type:** Grouped Bar Chart
- **X-Axis Column:** `province`
- **Metrics:** `SUM(male_owners)` and `SUM(female_owners)`

### Chart 4: Disability Ratio (Donut Chart)
- **SQL Source:** [dashboard_queries.sql](file:///c:/Users/rbotso.ZBFH/Desktop/mimie/land_stand_system/superset/dashboard_queries.sql#L46-L74)
- **Chart Type:** Pie Chart (Check **Donut** styling option)
- **Dimension:** `category`
- **Metric:** `SUM(count)`
