"""
Minimal working FastAPI backend - rebuild starting point
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings

app = FastAPI(
    title=settings.app_name,
    version=settings.version
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Working backend", "version": settings.version}

@app.get("/api/v1/test")
async def test():
    return {"message": "Test endpoint works"}

@app.get("/api/v1/components")
async def test_components():
    return {"message": "Components endpoint works", "components": []}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)


