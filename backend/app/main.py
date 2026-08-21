from fastapi import FastAPI
from dotenv import load_dotenv

from app.database import check_db_connection
from app.api.chat import router as chat_router

load_dotenv()

app = FastAPI(
    title="Founder Sidekick API",
    description="Backend API for Founder Sidekick",
    version="0.1.0"
)

app.include_router(chat_router)


@app.get("/")
def read_root():
    return {"message": "Founder Sidekick API is running!"}


@app.get("/health")
def health_check():
    db_status = check_db_connection()
    status_str = "healthy" if db_status.get("connected") else "degraded"
    return {
        "status": status_str,
        "database": db_status
    }
