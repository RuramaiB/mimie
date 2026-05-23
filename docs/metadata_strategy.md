# Enterprise Metadata & Data Governance Strategy

This document details the metadata strategy, classification levels, and data governance policies (Q8) implemented to ensure data compliance and protection within the Land Stand Management System.

---

## 1. 3-Layer Metadata Architecture

We implement a highly structured 3-layer metadata model to organize information assets:

```text
┌─────────────────────────────────────────────────────────┐
│                 BUSINESS METADATA LAYER                 │
│  - Data Classification (Public, Internal, Confidential)  │
│  - Data Owners & Stewards (Ministry of Lands)           │
│  - PII Flag Identifications                             │
└────────────────────────────┬────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────┐
│                TECHNICAL METADATA LAYER                 │
│  - Column Names & Table Schemas                         │
│  - Data Types (VARCHAR2, INT, GEOMETRY, BSON DECIMAL)   │
│  - Primary and Foreign Key Constraints                  │
└────────────────────────────┬────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────┐
│               OPERATIONAL METADATA LAYER                │
│  - Creation Timestamps (created_at)                     │
│  - Audit Trails (stand_allocations_audit)               │
│  - Access Control logs & DB connection sessions         │
└─────────────────────────────────────────────────────────┘
```

---

## 2. Personal Identifiable Information (PII) Inventory

The following attributes are classified as sensitive personal data and are protected under specific access guards:

| Table | Attribute | Classification | PII Flag | Description | Data Steward |
|---|---|---|---|---|---|
| `stand_owners` | `firstname` | **Confidential** | Yes | Full legal name of citizen holding stand deed. | GIS Department |
| `stand_owners` | `date_of_birth` | **Confidential** | Yes | Birth date used to verify legal majority status. | Registrar General |
| `stand_owners` | `gender` | **Internal** | Yes | Citizen demographic gender. | GIS Department |
| `stand_owners` | `disability_status`| **Confidential** | Yes | Health status used for priority queue scoring. | Ministry of Health |
| `dependents` | `firstname` | **Confidential** | Yes | Dependant child or spouse legal name. | GIS Department |
| `dependents` | `date_of_birth` | **Confidential** | Yes | Dependant birth date. | Registrar General |
| `stands` | `gps_coordinates` | **Internal** | No | Spatial coordinates for land boundaries. | Surveyor General |
| `stands` | `stand_number` | **Public** | No | Publicly accessible land stand reference identifier. | GIS Department |

---

## 3. Data Classification Matrix Definitions

- **Public:** Information accessible to all citizens (e.g. `stand_number`, `location_city`). Does not represent risk to individuals or national security.
- **Internal:** Restrictive within state servers (e.g. `gps_coordinates`, `size_m2`, `activity`). Requires standard access clearance.
- **Confidential:** Restrictive under strict data privacy regulations (e.g. citizen names, birth dates, disability statements). Access is granted only to registered owners or authorised handlers via scoped security credentials (`land_app`).
- **Restricted:** Highly critical data (e.g. system passwords, private encryption certificates, audit logs). Blocked from standard API pathways.

---

## 4. Metadata Catalogue JSON API Endpoint

To expose this strategy dynamically as required by the metadata specification, we build specific endpoints:
- **`GET /metadata/{db}`:** Exposes the full governance catalog for the targeted system.
- **`GET /metadata/{db}/pii`:** Returns only fields flagged as PII, allowing external privacy engines to audit sensitive data points dynamically.
