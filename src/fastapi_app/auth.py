from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Form, Request, Cookie
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse, RedirectResponse
from passlib.context import CryptContext
from jose import JWTError, jwt
import os

from src.common.models import User, ReportData
from src.common.db_facade import DatabaseFacade
from src.common.settings import settings
from src.utils.utils import load_default_prompt_files_data

router = APIRouter(prefix="/auth")

# JWT Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30 * 4

# Password hashing
pwd_context = CryptContext(schemes=["argon2", "bcrypt"], deprecated="auto")
security = HTTPBearer(auto_error=False)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Generate password hash"""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(request: Request) -> User:
    """Get current user from JWT token (from cookie or Authorization header)"""
    token = None
    
    # Try to get token from cookie first
    token = request.cookies.get("access_token")
    
    # If not in cookie, try Authorization header
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_facade = DatabaseFacade(User)
    user = await user_facade.get_one(email=email)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

async def get_current_admin_user(email: str, password: str) -> bool:
    """Verify admin credentials against environment variables"""
    return (email == settings.AUTH_SUPERADMIN_EMAIL and 
            password == settings.AUTH_SUPERADMIN_PASSWORD)

@router.post("/login")
async def login(email: str = Form(...), password: str = Form(...)):
    """Login endpoint"""
    user_facade = DatabaseFacade(User)
    user = await user_facade.get_one(email=email)
    
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    
    response = RedirectResponse(url="/", status_code=302)
    response.set_cookie(key="access_token", value=access_token, httponly=True)
    return response

@router.post("/signup")
async def signup(
    email: str = Form(...),
    password: str = Form(...),
    full_name: str = Form(...)
):
    """Signup endpoint"""
    user_facade = DatabaseFacade(User)
    
    # Check if user already exists
    existing_user = await user_facade.get_one(email=email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    hashed_password = get_password_hash(password)
    user = await user_facade.create(
        email=email,
        hashed_password=hashed_password,
        full_name=full_name,
        is_active=True,
        is_superuser=False
    )
    
    # Create default ReportData for new user
    default_data = load_default_prompt_files_data()
    report_facade = DatabaseFacade(ReportData)
    await report_facade.create(
        user_id=str(user.id),
        few_shot_prompt=default_data.get("few_shot_prompt", ""),
        examples=default_data.get("examples", ""),
        important_notes=default_data.get("important_notes", ""),
        words_spelling=default_data.get("words_spelling", "")
    )
    
    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    
    response = RedirectResponse(url="/", status_code=302)
    response.set_cookie(key="access_token", value=access_token, httponly=True)
    return response

@router.post("/admin-login")
async def admin_login(email: str = Form(...), password: str = Form(...)):
    """Admin login endpoint"""
    if not await get_current_admin_user(email, password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin credentials"
        )
    
    # For admin, we can redirect to a specific admin dashboard or main page
    # You can modify this based on your needs
    return JSONResponse(content={"success": True, "message": "Admin authenticated successfully"})

@router.post("/logout")
async def logout():
    """Logout endpoint"""
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie(key="access_token")
    return response

@router.get("/me")
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information"""
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "full_name": current_user.full_name,
        "is_active": current_user.is_active,
        "is_superuser": current_user.is_superuser,
        "created_at": current_user.created_at
    }
