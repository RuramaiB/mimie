import os
from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from datetime import timedelta
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from config import settings
from auth import limiter, create_access_token, verify_password, get_password_hash
from routers import health, stands, owners, subdivisions, allocations, dependents, reports, metadata

# Initialize FastAPI application with OpenAPI/Swagger settings
app = FastAPI(
    title="Land Stand Management System",
    description="MCS 504 Database Engineering assignment - Python FastAPI Connector for Multi-DBMS",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Wire global slowapi rate limiter configuration
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Configure Cross-Origin Resource Sharing (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Jinja2 templates for the Web CRUD UI frontend (Q9)
TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# Register routers
app.include_router(health.router)
app.include_router(stands.router)
app.include_router(owners.router)
app.include_router(subdivisions.router)
app.include_router(allocations.router)
app.include_router(dependents.router)
app.include_router(reports.router)
app.include_router(metadata.router)

# ═══════════════════════════════════════════════════════
#  SECURITY: OAUTH2 TOKEN GENERATION (JWT AUTH)
# ═══════════════════════════════════════════════════════

# In-Memory system roles dictionary matching universal credentials
SYSTEM_USERS = {
    "admin": {"password_hash": get_password_hash("Admin1234!"), "role": "land_admin"},
    "app": {"password_hash": get_password_hash("AppPassword123!"), "role": "land_app"},
    "readonly": {"password_hash": get_password_hash("ReadPass123!"), "role": "land_readonly"}
}

@app.post("/token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Standard OAuth2 token endpoint returning signed JWT on successful auth.
    """
    user = SYSTEM_USERS.get(form_data.username)
    if not user or not verify_password(form_data.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(
        data={"sub": form_data.username, "role": user["role"]},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return {"access_token": access_token, "token_type": "bearer"}

# ═══════════════════════════════════════════════════════
#  Q9 FRONTEND CRUD WEB UI (JINJA2 + HTMX)
# ═══════════════════════════════════════════════════════

@app.get("/", response_class=HTMLResponse)
async def index_dashboard(request: Request):
    """
    Renders main dynamic land analytics dashboard.
    """
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/stands", response_class=HTMLResponse)
async def stands_crud_page(request: Request):
    """
    Renders stands administration interface page.
    """
    return templates.TemplateResponse("stands/list.html", {"request": request})

@app.get("/stands/new", response_class=HTMLResponse)
async def stands_create_form(request: Request):
    """
    Renders modal overlay form for adding new stands.
    """
    return templates.TemplateResponse("stands/form.html", {"request": request})

@app.get("/owners", response_class=HTMLResponse)
async def owners_crud_page(request: Request):
    """
    Renders owner catalog administration page.
    """
    return templates.TemplateResponse("owners/list.html", {"request": request})

@app.get("/owners/new", response_class=HTMLResponse)
async def owners_create_form(request: Request):
    """
    Renders modal form for registering new owners.
    """
    return templates.TemplateResponse("owners/form.html", {"request": request})

@app.get("/allocations/new", response_class=HTMLResponse)
async def allocation_create_form(request: Request):
    """
    Renders transaction prompt for stand subdivision allocation.
    """
    return templates.TemplateResponse("allocations/form.html", {"request": request})
