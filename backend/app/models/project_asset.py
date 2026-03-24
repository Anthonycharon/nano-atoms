from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


class ProjectAsset(SQLModel, table=True):
    __tablename__ = "project_assets"

    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="projects.id", index=True)
    original_name: str
    stored_name: str
    relative_path: str
    public_url: str
    media_type: str
    file_size: int
    kind: str = Field(default="file")  # image | document | data | other
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
