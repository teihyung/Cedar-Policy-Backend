from typing import List

import uvicorn
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session as DBSession

from app.db import engine, Base, get_db
from app import models  # noqa: F401 -- import needed so models register on Base.metadata
from app.models import User
from app.schemas import LoginRequest, LoginResponse, TenantOut
from app.auth import verify_password, create_session, get_current_user

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

@app.post("/api/auth/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: DBSession = Depends(get_db)):
    user = db.query(User).filter(User.username == payload.username).first()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = create_session(db, user)
    return LoginResponse(token=token, username=user.username)

@app.get("/api/tenants", response_model=List[TenantOut])
def list_my_tenants(user: User = Depends(get_current_user)):
    return [TenantOut.model_validate(t) for t in user.tenants]


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)