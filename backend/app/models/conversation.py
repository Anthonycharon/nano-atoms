from datetime import datetime, timezone
from typing import Optional
from sqlmodel import Field, SQLModel


class Conversation(SQLModel, table=True):
    __tablename__ = "conversations"

    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="projects.id", index=True)
    mode: str = "standard"  # standard | race_lite
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
