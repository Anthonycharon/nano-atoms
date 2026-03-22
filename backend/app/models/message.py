from datetime import datetime, timezone
from typing import Optional
from sqlmodel import Field, SQLModel


class Message(SQLModel, table=True):
    __tablename__ = "messages"

    id: Optional[int] = Field(default=None, primary_key=True)
    conversation_id: int = Field(foreign_key="conversations.id", index=True)
    role: str  # user | assistant | agent
    agent_name: Optional[str] = None  # product | architect | ui_builder | code | qa
    content: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
