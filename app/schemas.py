from pydantic import BaseModel
from typing import List


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