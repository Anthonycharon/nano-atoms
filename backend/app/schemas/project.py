from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ProjectCreate(BaseModel):
    name: str
    app_type: str = "auto"
    description: Optional[str] = None


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class ProjectResponse(BaseModel):
    id: int
    name: str
    app_type: str
    description: Optional[str]
    latest_version_id: Optional[int]
    created_at: datetime
    updated_at: datetime


class VersionResponse(BaseModel):
    id: int
    project_id: int
    version_no: int
    status: str
    prompt_snapshot: str
    schema_json: Optional[str]
    code_json: Optional[str]
    created_at: datetime


class ConversationMessageResponse(BaseModel):
    id: int
    role: str
    content: str
    agent_name: Optional[str]
    created_at: datetime


class AgentRunResponse(BaseModel):
    agent_name: str
    status: str
    output_summary: Optional[str]


class ProjectAssetResponse(BaseModel):
    id: int
    project_id: int
    original_name: str
    public_url: str
    media_type: str
    file_size: int
    kind: str
    created_at: datetime
