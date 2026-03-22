from datetime import datetime, timezone
from typing import Optional
from sqlmodel import Field, SQLModel


class AgentRun(SQLModel, table=True):
    __tablename__ = "agent_runs"

    id: Optional[int] = Field(default=None, primary_key=True)
    version_id: int = Field(foreign_key="app_versions.id", index=True)
    agent_name: str  # product | architect | ui_builder | code | qa
    status: str = "pending"  # pending | running | done | error
    output_summary: Optional[str] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
