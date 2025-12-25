"""
Minimal FastAPI app for testing
"""
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Simple app works"}

@app.get("/test")
async def test():
    return {"message": "Test endpoint works"}

@app.get("/api/v1/test")
async def test_api():
    return {"message": "API test endpoint works"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)


