"""Server-side login sessions. Only the SHA-256 of the cookie token is stored."""
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from teacher_materials.models import Base


class AuthSession(Base):
    __tablename__ = "auth_session"
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    token_hash: Mapped[str] = mapped_column(String(64), index=True, unique=True)
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("user.id", ondelete="CASCADE"), index=True)
    csrf_token: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
