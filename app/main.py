from fastapi import FastAPI
from fastapi.templating import Jinja2Templates
from app.config import get_settings

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
)

templates = Jinja2Templates(directory="app/templates")


@app.get("/")
async def root():
    return {"message": "GLM Coding Bot is running!", "status": "ok"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
