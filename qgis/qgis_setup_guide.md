# QGIS Desktop Integration Setup Guide

This guide describes how to connect QGIS Desktop to the PostgreSQL/PostGIS database container and overlay dynamic spatial vectors of stand boundaries.

## 1. Prerequisites
- **QGIS Desktop** installed on your workstation (LTR v3.28 or v3.34 recommended).
- The Land Stand System Docker stack running (`docker compose up -d`).

---

## 2. Connection Settings

Use the following parameters inside QGIS to establish a database connection:

| Parameter | Value |
|---|---|
| **Service Type** | PostgreSQL / PostGIS |
| **Host** | `localhost` *(or the Docker Host IP)* |
| **Port** | `5432` |
| **Database** | `devdb` |
| **Schema** | `public` |
| **Authentication** | Basic |
| **Username** | `admin` (or `land_app` / `land_readonly`) |
| **Password** | `Admin1234!` (or `AppPassword123!` / `ReadPass123!`) |

---

## 3. Connecting to the Database in QGIS

1. Open **QGIS Desktop**.
2. Locate the **Browser Panel** on the left side.
3. Right-click on **PostgreSQL** and select **New Connection...**.
4. Enter `Ministry of Lands - PostGIS` in the **Name** field.
5. Enter the connection settings from the table above.
6. Click **Test Connection** to confirm connectivity.
7. Click **OK** to save the profile connection.

---

## 4. Loading Spatial Layers

Once connected, you can load layers in two ways:

### Option A: Drag-and-Drop Base Tables
Expand the connection in the browser and drag these tables directly onto the canvas:
- `stands` (Adds the default boundary footprints)
- `stand_survey`
- `stand_subdivisions`

### Option B: Run custom SQL layers (DB Manager)
To run advanced queries (like centroids or color-coded subdivisions):
1. Go to the top menu: **Database** → **DB Manager...**
2. Expand **PostgreSQL** → select `Ministry of Lands - PostGIS`.
3. Click the **SQL Window** button (feather icon).
4. Copy and paste any query from [qgis_queries.sql](file:///c:/Users/rbotso.ZBFH/Desktop/mimie/land_stand_system/qgis/qgis_queries.sql).
5. Click **Execute**.
6. Check **Load as new layer**, specify the Geometry Column (`geom_point` or `geom_polygon`), and click **Load**.

---

## 5. Styling and Color-Coding Layers

### Color Coding Subdivisions by Status
1. Right-click the Subdivision layer in your layers panel and select **Properties...**.
2. Navigate to the **Symbology** tab.
3. Change the renderer dropdown from **Single Symbol** to **Categorized**.
4. Set the **Value** column to `allocation_status` (or `allocation_state` if using Layer 3).
5. Click **Classify** at the bottom.
6. Set the styling colors:
   - `Available` / `False` → **Green** (`#38A169` fill, with dark borders)
   - `Allocated` / `True` → **Red** (`#E53E3E` fill)
7. Click **Apply** to render the colored divisions overlay instantly!
