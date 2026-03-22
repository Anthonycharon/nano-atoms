from datetime import datetime, timezone
from typing import Optional
from sqlmodel import Field, SQLModel


class AppVersion(SQLModel, table=True):
    __tablename__ = "app_versions"

    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="projects.id", index=True)
    version_no: int = 1
    prompt_snapshot: str = ""
    schema_json: Optional[str] = None   # JSON string: AppSchema
    code_json: Optional[str] = None     # JSON string: CodeBundle
    preview_snapshot: Optional[str] = None  # base64 or URL
    status: str = "queued"  # queued | running | completed | failed
    race_pair_id: Optional[str] = None  # Race Lite 关联 ID
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
