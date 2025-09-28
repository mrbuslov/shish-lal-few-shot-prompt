import subprocess
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import uvicorn
from dotenv import load_dotenv
from src.fastapi_app.routes import router as main_router

# Load environment variables from .env file
load_dotenv()

app = FastAPI(
    title="Medical Text Processor", description="AI-powered medical text analysis"
)
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


if __name__ == "__main__":
    # Run the server
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
