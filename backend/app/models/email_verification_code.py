from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


class EmailVerificationCode(SQLModel, table=True):
    __tablename__ = "email_verification_codes"

    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(index=True)
    purpose: str = Field(index=True)
    token_id: str = Field(unique=True, index=True)
    code_hash: str
    expires_at: datetime
    consumed_at: Optional[datetime] = Field(default=None, nullable=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), index=True)
