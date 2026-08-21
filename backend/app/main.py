from fastapi import FastAPI
from dotenv import load_dotenv
import os

load_dotenv()

app = FastAPI(
    title="Founder Sidekick API",
    description="Backend API for Founder Sidekick",
    version="0.1.0"
)

@app.get("/")
def read_root():
    return {"message": "Founder Sidekick API is running!"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}
