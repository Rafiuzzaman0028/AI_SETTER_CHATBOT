# JamieBot/app/main.py
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from app.api.routes import router
from app.api.comment_routes import router as comment_router # <--- IMPORT

app = FastAPI(
    title="Jamie AI Setter",
    description="State-driven AI Setter chatbot service",
    version="1.0.0",
)

app.include_router(router)
app.include_router(comment_router)  # New /process-comment
app.mount("/static", StaticFiles(directory="app/static"), name="static")

@app.get("/")
async def read_root():
    return FileResponse("app/static/index.html")
