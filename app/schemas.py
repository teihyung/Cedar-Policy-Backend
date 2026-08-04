from pydantic import BaseModel
from typing import List
from datetime import datetime


class LoginRequest(BaseModel):
    username: str
    password: str


class TenantOut(BaseModel):
    id: str
    name: str
    slug: str

    class Config:
        from_attributes = True  # lets Pydantic read directly off SQLAlchemy objects


class LoginResponse(BaseModel):
    token: str
    username: str

class PolicyFileOut(BaseModel):
    id: str
    filename: str
    status: str
    size_bytes: int
    current_commit_hash: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True