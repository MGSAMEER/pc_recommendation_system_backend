"""
Minimal FastAPI application for debugging
"""
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Minimal FastAPI app working"}

@app.get("/test")
async def test():
    return {"message": "Test endpoint working"}

@app.get("/api/v1/health")
async def health():
    return {"status": "healthy"}

@app.get("/api/v1/test-components")
async def test_components():
    return {"message": "Test components endpoint", "status": "success"}
