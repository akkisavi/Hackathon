from datetime import datetime
import enum

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.core.db import Base


class ApiKeyStatusEnum(str, enum.Enum):
    active = "active"
    revoked = "revoked"
    expired = "expired"


class ApiKey(Base):
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey(
        "users.id", ondelete="CASCADE"), nullable=False, index=True)
    key_hash = Column(String, unique=True, index=True, nullable=False)
    status = Column(Enum(ApiKeyStatusEnum),
                    default=ApiKeyStatusEnum.active, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_used_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)

    user = relationship("User", backref="api_keys")
