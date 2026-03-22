"""Generation endpoints for creating and iterating app versions."""

from typing import Annotated, List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlmodel import Session, select

from app.api.auth import get_current_user
from app.core.database import engine, get_session
from app.models import AppVersion, Conversation, Message, Project, User
from app.schemas.generation import GenerateRequest, IterateRequest
from app.schemas.project import VersionResponse
from app.services.generation_service import run_generation, run_race_lite

router = APIRouter(prefix="/api/projects", tags=["generation"])


def _version_to_response(version: AppVersion) -> VersionResponse:
    return VersionResponse(
        id=version.id,
        project_id=version.project_id,
        version_no=version.version_no,
        status=version.status,
        prompt_snapshot=version.prompt_snapshot,
        schema_json=version.schema_json,
        code_json=version.code_json,
        created_at=version.created_at,
    )


@router.post("/{project_id}/generate", status_code=202)
async def generate(
    project_id: int,
    body: GenerateRequest,
    background_tasks: BackgroundTasks,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
):
    project = session.get(Project, project_id)
    if not project or project.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")

    last_version = session.exec(
        select(AppVersion)
        .where(AppVersion.project_id == project_id)
        .order_by(AppVersion.version_no.desc())
    ).first()
    next_version_no = (last_version.version_no + 1) if last_version else 1

    conversation = session.exec(
        select(Conversation).where(Conversation.project_id == project_id)
    ).first()
    if conversation:
        session.add(
            Message(
                conversation_id=conversation.id,
                role="user",
                content=body.prompt,
            )
        )

    app_type = project.app_type or "auto"

    if body.mode == "race_lite":
        version_a = AppVersion(
            project_id=project_id,
            version_no=next_version_no,
            prompt_snapshot=body.prompt,
            status="queued",
            race_pair_id=f"race_{project_id}_{next_version_no}",
        )
        version_b = AppVersion(
            project_id=project_id,
            version_no=next_version_no + 1,
            prompt_snapshot=body.prompt,
            status="queued",
            race_pair_id=f"race_{project_id}_{next_version_no}",
        )
        session.add(version_a)
        session.add(version_b)
        session.flush()
        session.commit()
        session.refresh(version_a)
        session.refresh(version_b)

        background_tasks.add_task(
            run_race_lite,
            project_id,
            version_a.id,
            version_b.id,
            body.prompt,
            app_type,
            engine,
        )
        return {"version_ids": [version_a.id, version_b.id], "mode": "race_lite"}

    version = AppVersion(
        project_id=project_id,
        version_no=next_version_no,
        prompt_snapshot=body.prompt,
        status="queued",
    )
    session.add(version)
    session.flush()
    session.commit()
    session.refresh(version)

    background_tasks.add_task(
        run_generation,
        project_id,
        version.id,
        body.prompt,
        app_type,
        engine,
    )
    return {"version_id": version.id, "mode": "standard"}


@router.post("/{project_id}/iterate", status_code=202)
async def iterate(
    project_id: int,
    body: IterateRequest,
    background_tasks: BackgroundTasks,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
):
    project = session.get(Project, project_id)
    if not project or project.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")

    last_version = session.exec(
        select(AppVersion)
        .where(AppVersion.project_id == project_id)
        .order_by(AppVersion.version_no.desc())
    ).first()
    if not last_version:
        raise HTTPException(status_code=400, detail="No existing version to iterate from")

    context_prompt = body.prompt
    if last_version.schema_json:
        context_prompt = f"基于现有应用，修改需求：{body.prompt}"

    conversation = session.exec(
        select(Conversation).where(Conversation.project_id == project_id)
    ).first()
    if conversation:
        session.add(
            Message(
                conversation_id=conversation.id,
                role="user",
                content=body.prompt,
            )
        )

    new_version = AppVersion(
        project_id=project_id,
        version_no=last_version.version_no + 1,
        prompt_snapshot=body.prompt,
        status="queued",
    )
    session.add(new_version)
    session.flush()
    session.commit()
    session.refresh(new_version)

    background_tasks.add_task(
        run_generation,
        project_id,
        new_version.id,
        context_prompt,
        project.app_type or "auto",
        engine,
    )
    return {"version_id": new_version.id}


@router.get("/{project_id}/versions", response_model=List[VersionResponse])
def list_versions(
    project_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
):
    project = session.get(Project, project_id)
    if not project or project.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")

    versions = session.exec(
        select(AppVersion)
        .where(AppVersion.project_id == project_id)
        .order_by(AppVersion.version_no.desc())
    ).all()
    return [_version_to_response(version) for version in versions]
