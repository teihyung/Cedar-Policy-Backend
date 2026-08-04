import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, ForeignKey, DateTime, Integer, Table
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .db import Base


def _uuid():
    return str(uuid.uuid4())


def _now():
    return datetime.now(timezone.utc)


class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    customer_name = Column(String, nullable=False)  
    name = Column(String, nullable=False)            
    slug = Column(String, nullable=False, unique=True)

    policy_files = relationship("PolicyFile", back_populates="tenant")


# many-to-many: a user can belong to multiple tenants
user_tenants = Table(
    "user_tenants",
    Base.metadata,
    Column("user_id", UUID(as_uuid=False), ForeignKey("users.id"), primary_key=True),
    Column("tenant_id", UUID(as_uuid=False), ForeignKey("tenants.id"), primary_key=True),
)


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    username = Column(String, nullable=False, unique=True)
    password_hash = Column(String, nullable=False)

    tenants = relationship("Tenant", secondary=user_tenants)


class PolicyFile(Base):
    __tablename__ = "policy_files"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    tenant_id = Column(UUID(as_uuid=False), ForeignKey("tenants.id"), nullable=False, index=True)
    filename = Column(String, nullable=False)
    git_path = Column(String, nullable=False)
    current_commit_hash = Column(String, nullable=False)
    size_bytes = Column(Integer, nullable=False)
    status = Column(String, nullable=False, default="ACTIVE")
    uploaded_by = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=_now)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now)

    tenant = relationship("Tenant", back_populates="policy_files")