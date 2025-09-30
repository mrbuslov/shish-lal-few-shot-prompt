import os
import subprocess
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from passlib.context import CryptContext

from src.fastapi_app.routes import router as main_router
from src.utils.consts import USER_REPORTS_FILES_DIR
from src.common.settings import settings
from src.common.models import User, ReportData
from src.common.db_facade import DatabaseFacade
from src.utils.utils import load_default_prompt_files_data

from passlib.context import CryptContext

pwd_context = CryptContext(
    schemes=["argon2", "bcrypt"],  # argon2 первый
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

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(main_router)


@app.get("/", response_class=HTMLResponse)
async def home():
    """Serve the main UI page from file"""
    try:
        with open("templates/index.html", "r", encoding="utf-8") as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    except FileNotFoundError:
        return HTMLResponse(
            content="<h1>Error: index.html not found</h1>", status_code=404
        )


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


@app.get("/update")
def update():
    try:
        result = subprocess.check_output(
            ["git", "pull"],
            stderr=subprocess.STDOUT,
            cwd="C:/Users/krisa/OneDrive/Рабочий стол/shish-lal-few-shot-prompt",
        )
        return {"status": "ok", "output": result.decode()}
    except subprocess.CalledProcessError as e:
        return {"status": "error", "output": e.output.decode()}
