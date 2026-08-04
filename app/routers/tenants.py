from typing import List
from fastapi import APIRouter, Depends

from app.models import User
from app.schemas import TenantOut
from app.auth import get_current_user

router = APIRouter(prefix="/api/tenants", tags=["tenants"])

@router.get("", response_model=List[TenantOut])
def list_my_tenants(user: User = Depends(get_current_user)):
    return [TenantOut.model_validate(t) for t in user.tenants]