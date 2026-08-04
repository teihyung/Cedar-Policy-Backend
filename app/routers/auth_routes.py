from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession

from app.db import get_db
from app.models import User
from app.schemas import LoginRequest, LoginResponse
from app.auth import verify_password, create_session

router = APIRouter(prefix="/api/auth", tags=["auth"])

@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: DBSession = Depends(get_db)):
    user = db.query(User).filter(User.username == payload.username).first()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    token = create_session(db, user)
    return LoginResponse(token=token, username=user.username)