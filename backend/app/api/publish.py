"""
发布相关 API：发布版本为公开链接，获取发布内容。
"""
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.api.auth import get_current_user
from app.core.database import get_session
from app.models import AgentRun, AppVersion, Project, PublishedApp, User
from app.schemas.generation import PublishRequest, PublishResponse
from app.schemas.project import AgentRunResponse
from app.services.version_recovery import reconcile_version_status

router = APIRouter(tags=["publish"])


@router.post("/api/projects/{project_id}/publish", response_model=PublishResponse)
def publish_version(
    project_id: int,
    body: PublishRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
):
    project = session.get(Project, project_id)
    if not project or project.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")

    version_id = body.version_id or project.latest_version_id
    if not version_id:
        raise HTTPException(status_code=400, detail="No version to publish")

    version = session.get(AppVersion, version_id)
    if not version or version.status != "completed":
        raise HTTPException(status_code=400, detail="Version not ready")

    # 生成唯一 slug（8位 UUID 片段）
    slug = uuid.uuid4().hex[:8]

    # 停用当前活跃发布
    existing = session.exec(
        select(PublishedApp)
        .where(PublishedApp.project_id == project_id)
        .where(PublishedApp.is_active == True)
    ).all()
    for pub in existing:
        pub.is_active = False
        session.add(pub)

    published = PublishedApp(
        project_id=project_id,
        version_id=version_id,
        slug=slug,
        is_active=True,
    )
    session.add(published)
    session.commit()

    return PublishResponse(slug=slug, url=f"/p/{slug}")


@router.get("/api/published/{slug}")
def get_published(slug: str, session: Annotated[Session, Depends(get_session)]):
    """公开接口：获取已发布版本的完整产物（无需认证）。"""
    published = session.exec(
        select(PublishedApp).where(PublishedApp.slug == slug).where(PublishedApp.is_active == True)
    ).first()

    if not published:
        raise HTTPException(status_code=404, detail="Published app not found")

    version = session.get(AppVersion, published.version_id)
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")

    return {
        "slug": slug,
        "schema_json": version.schema_json,
        "code_json": version.code_json,
        "project_id": published.project_id,
        "version_id": published.version_id,
    }


@router.get("/api/versions/{version_id}")
def get_version(
    version_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
):
    """获取版本详情（含完整产物 JSON）。"""
    version = session.get(AppVersion, version_id)
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")

    # 验证权限
    project = session.get(Project, version.project_id)
    if not project or project.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")

    version = reconcile_version_status(session, version)

    return {
        "id": version.id,
        "project_id": version.project_id,
        "version_no": version.version_no,
        "status": version.status,
        "prompt_snapshot": version.prompt_snapshot,
        "schema_json": version.schema_json,
        "code_json": version.code_json,
        "created_at": version.created_at.isoformat(),
        "agent_runs": [
            AgentRunResponse(
                agent_name=run.agent_name,
                status=run.status,
                output_summary=run.output_summary,
            ).model_dump()
            for run in session.exec(
                select(AgentRun)
                .where(AgentRun.version_id == version_id)
                .order_by(AgentRun.id.asc())
            ).all()
        ],
    }
