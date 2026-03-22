from datetime import datetime, timezone
from typing import Optional
from sqlmodel import Field, SQLModel


class PublishedApp(SQLModel, table=True):
    __tablename__ = "published_apps"

    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="projects.id", index=True)
    version_id: int = Field(foreign_key="app_versions.id")
    slug: str = Field(unique=True, index=True)
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
