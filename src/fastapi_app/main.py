import os
import subprocess
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from passlib.context import CryptContext
from fastapi.templating import Jinja2Templates

from src.fastapi_app.routes import router as main_router
from src.fastapi_app.auth import router as auth_router, get_current_user, get_current_admin_user
from src.utils.consts import USER_REPORTS_FILES_DIR
from src.common.settings import settings
from src.common.models import User, ReportData
from src.common.db_facade import DatabaseFacade
from src.utils.utils import load_default_prompt_files_data

from passlib.context import CryptContext

pwd_context = CryptContext(
    schemes=["argon2", "bcrypt"],
    deprecated="auto"
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Server is starting...")
    
    # Create directories
    if not os.path.exists(USER_REPORTS_FILES_DIR):
        os.makedirs(USER_REPORTS_FILES_DIR)
    
    # Initialize MongoDB
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    await init_beanie(
        database=client[settings.MONGODB_DB_NAME],
        document_models=[User, ReportData]
    )
    
    # Create superadmin user if not exists
    user_facade = DatabaseFacade(User)
    superadmin = await user_facade.get_one(email=settings.AUTH_SUPERADMIN_EMAIL)
    
    if not superadmin:
        hashed_password = pwd_context.hash(settings.AUTH_SUPERADMIN_PASSWORD)
        default_data = load_default_prompt_files_data()
        
        # Create superadmin user
        superadmin = await user_facade.create(
            email=settings.AUTH_SUPERADMIN_EMAIL,
            hashed_password=hashed_password,
            is_superuser=True,
            is_active=True,
            full_name="Super Administrator"
        )
        
        # Create default ReportData for superadmin
        report_facade = DatabaseFacade(ReportData)
        await report_facade.create(
            user_id=str(superadmin.id),
            few_shot_prompt=default_data.get("few_shot_prompt", ""),
            examples=default_data.get("examples", ""),
            important_notes=default_data.get("important_notes", ""),
            words_spelling=default_data.get("words_spelling", "")
        )
        
        print(f"Created superadmin user: {settings.AUTH_SUPERADMIN_EMAIL}")
    else:
        print(f"Superadmin user already exists: {settings.AUTH_SUPERADMIN_EMAIL}")
    
    yield
    
    print("Server is shutting down...")
    client.close()

app = FastAPI(
    title="Medical Text Processor", description="AI-powered medical text analysis",
    lifespan=lifespan,
)

# Configure Jinja2 templates
templates = Jinja2Templates(directory="templates")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(main_router)
app.include_router(auth_router)


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Serve the main UI page with authentication check"""
    try:
        # Check if user has valid token
        try:
            current_user = await get_current_user(request)
            # User is authenticated, serve the main page
            with open("templates/index.html", "r", encoding="utf-8") as f:
                html_content = f.read()
            return HTMLResponse(content=html_content)
        except HTTPException:
            # User is not authenticated, redirect to login
            return RedirectResponse(url="/login", status_code=302)
    except FileNotFoundError:
        return HTMLResponse(
            content="<h1>Error: index.html not found</h1>", status_code=404
        )


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Serve the login page"""
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/signup", response_class=HTMLResponse)
async def signup_page(request: Request):
    """Serve the signup page"""
    return templates.TemplateResponse("signup.html", {"request": request})

@app.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request):
    """Serve the admin page"""
    return templates.TemplateResponse("admin.html", {"request": request})

@app.get("/me", response_class=HTMLResponse)
async def me_page(request: Request):
    """Serve the user profile page with authentication check"""
    try:
        current_user = await get_current_user(request)
        return templates.TemplateResponse("me.html", {"request": request, "user": current_user})
    except HTTPException:
        return RedirectResponse(url="/login", status_code=302)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}
