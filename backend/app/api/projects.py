from datetime import datetime, timezone
from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlmodel import Session, select

from app.api.auth import get_current_user
from app.core.database import get_session
from app.models import AgentRun, AppVersion, Conversation, Message, Project, ProjectAsset, PublishedApp, User
from app.schemas.project import (
    ConversationMessageResponse,
    ProjectCreate,
    ProjectResponse,
    ProjectUpdate,
)
from app.services.asset_storage import delete_project_asset_file

router = APIRouter(prefix="/api/projects", tags=["projects"])


def _to_response(project: Project) -> ProjectResponse:
    return ProjectResponse(
        id=project.id,
        name=project.name,
        app_type=project.app_type,
        description=project.description,
        latest_version_id=project.latest_version_id,
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


@router.get("", response_model=List[ProjectResponse])
def list_projects(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
):
    projects = session.exec(
        select(Project)
        .where(Project.user_id == current_user.id)
        .order_by(Project.updated_at.desc())
    ).all()
    return [_to_response(project) for project in projects]


@router.post("", response_model=ProjectResponse, status_code=201)
def create_project(
    body: ProjectCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
):
    project = Project(
        user_id=current_user.id,
        name=body.name,
        app_type=body.app_type or "auto",
        description=body.description,
    )
    session.add(project)
    session.flush()

    conversation = Conversation(project_id=project.id)
    session.add(conversation)
    session.commit()
    session.refresh(project)
    return _to_response(project)


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
):
    project = session.get(Project, project_id)
    if not project or project.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    return _to_response(project)


@router.get("/{project_id}/messages", response_model=List[ConversationMessageResponse])
def list_project_messages(
    project_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
):
    project = session.get(Project, project_id)
    if not project or project.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")

    conversation = session.exec(
        select(Conversation).where(Conversation.project_id == project_id)
    ).first()
    if not conversation:
        return []

    messages = session.exec(
        select(Message)
        .where(Message.conversation_id == conversation.id)
        .order_by(Message.created_at.asc(), Message.id.asc())
    ).all()
    return [
        ConversationMessageResponse(
            id=message.id,
            role=message.role,
            content=message.content,
            agent_name=message.agent_name,
            created_at=message.created_at,
        )
        for message in messages
    ]


@router.patch("/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: int,
    body: ProjectUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
):
    project = session.get(Project, project_id)
    if not project or project.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")

    if body.name is not None:
        project.name = body.name
    if body.description is not None:
        project.description = body.description
    project.updated_at = datetime.now(timezone.utc)

    session.add(project)
    session.commit()
    session.refresh(project)
    return _to_response(project)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
):
    project = session.get(Project, project_id)
    if not project or project.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")

    conversations = list(
        session.exec(select(Conversation).where(Conversation.project_id == project_id)).all()
    )
    conversation_ids = [conversation.id for conversation in conversations if conversation.id is not None]

    versions = list(session.exec(select(AppVersion).where(AppVersion.project_id == project_id)).all())
    version_ids = [version.id for version in versions if version.id is not None]

    assets = list(session.exec(select(ProjectAsset).where(ProjectAsset.project_id == project_id)).all())
    published = list(session.exec(select(PublishedApp).where(PublishedApp.project_id == project_id)).all())

    if conversation_ids:
        messages = list(
            session.exec(select(Message).where(Message.conversation_id.in_(conversation_ids))).all()
        )
        for message in messages:
            session.delete(message)

    if version_ids:
        agent_runs = list(
            session.exec(select(AgentRun).where(AgentRun.version_id.in_(version_ids))).all()
        )
        for run in agent_runs:
            session.delete(run)

    for published_app in published:
        session.delete(published_app)

    for asset in assets:
        delete_project_asset_file(asset)
        session.delete(asset)

    for version in versions:
        session.delete(version)

    for conversation in conversations:
        session.delete(conversation)

    session.delete(project)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
