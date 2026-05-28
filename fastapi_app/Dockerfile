# ═══════════════════════════════════════════════════════
#  STAGE 1: BUILD ENVIRONMENT
# ═══════════════════════════════════════════════════════
FROM python:3.12-slim AS builder

WORKDIR /build

# Install system compilation dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    gnupg2 \
    unixodbc-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Install packages globally in build stage
RUN pip install --default-timeout=1000 --no-cache-dir -r requirements.txt


# ═══════════════════════════════════════════════════════
#  STAGE 2: PRODUCTION RUNTIME
# ═══════════════════════════════════════════════════════
FROM python:3.12-slim AS runtime

WORKDIR /app

# Install system runtimes: ODBC dependencies and tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    unixodbc \
    odbcinst \
    curl \
    gnupg2 \
    apt-transport-https \
    && rm -rf /var/lib/apt/lists/*

# Add Microsoft SQL Server ODBC repository and install driver
RUN mkdir -p /usr/share/keyrings \
    && curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg \
    && curl -fsSL https://packages.microsoft.com/config/debian/12/prod.list -o /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y --no-install-recommends msodbcsql18 \
    && rm -rf /var/lib/apt/lists/*

# Copy vendor python packages from Builder
COPY --from=builder /usr/local /usr/local

# Copy application source code
COPY . .

# Setup a secure non-root system user
RUN useradd -u 8888 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Health check setup targeting FastAPI app
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

ENTRYPOINT ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
