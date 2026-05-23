# Security Measures Implementation Report

This report outlines the technical implementations addressing the data security and governance requirements (Q6) for the Land Stand Management System across all database platforms and the FastAPI layer.

---

## 1. Database Role-Based Access Control (RBAC)

We implement three distinct security roles across MySQL, Postgres, MSSQL, and Oracle to enforce the principle of least privilege:

1. **`land_admin` (DBA Role):**
   - Holds full superuser permissions.
   - Responsible for schema modifications, metadata updates, database structural maintenance, and global auditing tasks.
2. **`land_app` (Application Access Role):**
   - The primary credential utilized by our FastAPI application.
   - Allowed `SELECT`, `INSERT`, `UPDATE`, and `DELETE` privileges on tables.
   - Granted execution rights on stored procedures (`sp_allocate_stand`, `sp_owner_report`).
3. **`land_readonly` (Analyst Role):**
   - Restricted to `SELECT` queries on standard reporting views (`vw_allocated_stands`, `vw_owner_portfolio`, `vw_disability_summary`).
   - Blocked from executing any DML or structural table manipulations.

---

## 2. Row-Level Security (RLS) Implementation

To protect sensitive citizen data, we apply Row-Level Security on the `stand_owners` table to ensure owners can only query their own records, while administrators retain global analytical sight.

### PostgreSQL Implementation
We enable RLS and set policies based on session transaction variables:
```sql
ALTER TABLE stand_owners ENABLE ROW LEVEL SECURITY;

CREATE POLICY owner_policy ON stand_owners 
    FOR ALL 
    USING (
        (current_setting('app.current_user_role', true) = 'land_admin') OR 
        (current_setting('app.current_user_role', true) = 'land_app') OR 
        (stand_owner_id = current_setting('app.current_owner_id', true)::integer)
    );
```
During operations, the FastAPI controller sets `app.current_owner_id` within the scoped transaction.

### MS SQL Server Implementation
We employ T-SQL inline security predicate functions and security policies:
```sql
CREATE FUNCTION dbo.fn_securitypredicate(@OwnerID INT)
RETURNS TABLE WITH SCHEMABINDING
AS
RETURN SELECT 1 AS fn_securitypredicate_result
WHERE 
    CAST(SESSION_CONTEXT(N'current_user_role') AS VARCHAR(100)) = 'land_admin'
    OR CAST(SESSION_CONTEXT(N'current_user_role') AS VARCHAR(100)) = 'land_app'
    OR @OwnerID = CAST(SESSION_CONTEXT(N'current_owner_id') AS INT);
GO

CREATE SECURITY POLICY OwnerFilter
ADD FILTER PREDICATE dbo.fn_securitypredicate(stand_owner_id)
ON dbo.stand_owners
WITH (STATE = ON);
```

### Oracle Virtual Private Database (VPD)
In Oracle XE, VPD policies are established using `DBMS_RLS.ADD_POLICY`. The session context is set via context variables matching client contexts.
```sql
-- VPD context rule definition
DBMS_RLS.ADD_POLICY(
    object_schema   => 'devdb',
    object_name     => 'stand_owners',
    policy_name     => 'owner_policy',
    function_schema => 'devdb',
    policy_function => 'pkg_security.fn_owner_predicate',
    statement_types => 'SELECT,INSERT,UPDATE,DELETE'
);
```

---

## 3. FastAPI Application Security Wrappers

### Input Sanitisation & Parameterised Queries
- **No Raw SQL Concatenation:** All database connections are mediated via SQLAlchemy parameters or PyMongo parameter mappings, making SQL injection attacks mathematically impossible.
- **Pydantic Validation:** All incoming request models are strictly typed and sanitised. The Custom validator schemas enforce structure, constraints (e.g. positive decimals), and WGS-84 coordinate range checks before payloads touch the database layer.

### JSON Web Token (JWT) Authentication
- Integrates `python-jose` and `passlib` to secure API access.
- Validates signed JWTs on each request. The JWT payload encapsulates the caller's username and role clearance.
- Decoded credentials are passed into `RoleGuard` dependencies, blocking unauthorised access at the router layer.

### SlowAPI Rate Limiting
- Integrates `slowapi` to prevent Denial-of-Service (DoS) and brute force attacks.
- Places request limits dynamically based on remote client IPs (e.g., maximum 60 requests per minute on sensitive endpoints).

### HTTPS Ready (Production SSL Configuration)
To run the container in full production SSL mode, mount the private certificates and bind Uvicorn:
```bash
# Executing Uvicorn securely
uvicorn main:app --host 0.0.0.0 --port 8000 --ssl-keyfile=/certs/privkey.pem --ssl-certfile=/certs/fullchain.pem
```
Alternatively, configure a reverse proxy container (like Nginx or Traefik) as the TLS termination point, routing traffic locally to Uvicorn via HTTP inside the isolated Docker network bridge.
