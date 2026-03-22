from typing import Optional
from pydantic import BaseModel


class GenerateRequest(BaseModel):
    prompt: str
    mode: str = "standard"  # standard | race_lite


class IterateRequest(BaseModel):
    prompt: str


class PublishRequest(BaseModel):
    version_id: Optional[int] = None  # None 表示使用 latest


class PublishResponse(BaseModel):
    slug: str
    url: str


class AgentStatusMessage(BaseModel):
    type: str = "agent_status"
    agent: str
    status: str  # running | done | error
    summary: Optional[str] = None
    timestamp: str


class GenerationStatusMessage(BaseModel):
    type: str = "generation_status"
    status: str  # queued | running | completed | failed
    version_id: Optional[int] = None
    error: Optional[str] = None
