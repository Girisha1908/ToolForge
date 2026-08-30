from fastapi import FastAPI

app = FastAPI(title="ToolForge API")

@app.get("/")
def read_root():
    return {"message": "Welcome to ToolForge API"}
