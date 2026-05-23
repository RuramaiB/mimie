import os
from datetime import datetime, timedelta, timezone
from typing import Optional, List
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address
from config import settings

# Initialize password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 Scheme targeting standard login endpoint
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Initialize global rate limiter (Q6 security requirement)
limiter = Limiter(key_func=get_remote_address)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifies match of input password with hashed version.
    """
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """
    Computes secure bcrypt hash of password.
    """
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Encodes access credentials into secure signed JWT.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

class UserPrincipal(BaseModel):
    username: str
    role: str  # 'land_readonly' | 'land_app' | 'land_admin'

async def get_current_user(token: str = Depends(oauth2_scheme)) -> UserPrincipal:
    """
    Decodes and validates JWT to fetch calling user context.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        role: str = payload.get("role")
        if username is None or role is None:
            raise credentials_exception
        return UserPrincipal(username=username, role=role)
    except JWTError:
        raise credentials_exception

class RoleGuard:
    """
    FastAPI dependency enforcing specific role clearance on endpoints.
    """
    def __init__(self, allowed_roles: List[str]):
        self.allowed_roles = allowed_roles

    def __call__(self, current_user: UserPrincipal = Depends(get_current_user)) -> UserPrincipal:
        if current_user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Operation not permitted: Insufficient privileges."
            )
        return current_user
