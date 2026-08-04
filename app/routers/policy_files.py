from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import Response
from sqlalchemy.orm import Session as DBSession

from app.db import get_db
from app.models import User, PolicyFile
from app.schemas import PolicyFileOut
from app.auth import get_current_user, require_tenant_access
from app.cedar_validate import validate_cedar_policy, CedarValidationError
from app import gitstore
from app.gitstore import GitStoreError

router = APIRouter(prefix="/api/tenants/{tenant_id}/policy-files", tags=["policy-files"])


@router.post("", response_model=PolicyFileOut, status_code=201)
def upload_policy_file(
    tenant_id: str,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    require_tenant_access(tenant_id, user, db)

    existing = (
        db.query(PolicyFile)
        .filter(PolicyFile.tenant_id == tenant_id, PolicyFile.filename == file.filename)
        .first()
    )
    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail=f"A policy file named '{file.filename}' already exists for this tenant. "
                   f"Delete it first or upload under a different name.",
        )

    raw_bytes = file.file.read()

    try:
        policy_text = validate_cedar_policy(raw_bytes)
    except CedarValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)

    try:
        commit_hash = gitstore.write_policy_file(tenant_id, file.filename, policy_text, user.username)
    except GitStoreError as e:
        raise HTTPException(status_code=400, detail=str(e))

    policy_file = PolicyFile(
        tenant_id=tenant_id,
        filename=file.filename,
        git_path=f"{tenant_id}/{file.filename}",
        current_commit_hash=commit_hash,
        size_bytes=len(raw_bytes),
        status="ACTIVE",
        uploaded_by=user.id,
    )
    db.add(policy_file)
    db.commit()
    db.refresh(policy_file)
    return policy_file


@router.get("", response_model=List[PolicyFileOut])
def list_policy_files(
    tenant_id: str,
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    require_tenant_access(tenant_id, user, db)
    return db.query(PolicyFile).filter(PolicyFile.tenant_id == tenant_id).all()


@router.get("/{file_id}/download")
def download_policy_file(
    tenant_id: str,
    file_id: str,
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    require_tenant_access(tenant_id, user, db)

    policy_file = (
        db.query(PolicyFile)
        .filter(PolicyFile.id == file_id, PolicyFile.tenant_id == tenant_id)
        .first()
    )
    if policy_file is None:
        raise HTTPException(status_code=404, detail="Policy file not found")

    try:
        content = gitstore.read_policy_file(tenant_id, policy_file.filename)
    except GitStoreError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return Response(
        content=content,
        media_type="text/plain",
        headers={"Content-Disposition": f'attachment; filename="{policy_file.filename}"'},
    )


@router.delete("/{file_id}", status_code=204)
def delete_policy_file(
    tenant_id: str,
    file_id: str,
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    require_tenant_access(tenant_id, user, db)

    policy_file = (
        db.query(PolicyFile)
        .filter(PolicyFile.id == file_id, PolicyFile.tenant_id == tenant_id)
        .first()
    )
    if policy_file is None:
        raise HTTPException(status_code=404, detail="Policy file not found")

    try:
        gitstore.delete_policy_file(tenant_id, policy_file.filename, user.username)
    except GitStoreError as e:
        raise HTTPException(status_code=404, detail=str(e))

    db.delete(policy_file)
    db.commit()
    return None