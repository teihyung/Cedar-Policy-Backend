from fastapi import FastAPI
import uvicorn
from sqlalchemy import text

from app.db import engine, Base
from app import models  # noqa: F401 -- import needed so models register on Base.metadata

app = FastAPI()


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/db-check")
def db_check():
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        return {"db": "connected", "result": result.scalar()}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)