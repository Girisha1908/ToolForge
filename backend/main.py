from fastapi import FastAPI
from routes.api import router as api_router

app = FastAPI(title="ToolForge API")

app.include_router(api_router, prefix="/api")

@app.get("/")
def read_root():
    return {"message": "Welcome to ToolForge API"}

