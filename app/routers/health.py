from fastapi import APIRouter
from sqlalchemy import text
from app.db import engine

router = APIRouter(tags=["health"])

@router.get("/api/health")
def health():
    return {"status": "ok"}

@router.get("/api/db-check")
def db_check():
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        return {"db": "connected", "result": result.scalar()}