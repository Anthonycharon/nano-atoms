"""Project asset upload and management endpoints."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlmodel import Session, select

from app.api.auth import get_current_user
from app.core.database import get_session
from app.models import Project, ProjectAsset, User
from app.schemas.project import ProjectAssetResponse
from app.services.asset_storage import delete_project_asset_file, save_project_asset

router = APIRouter(prefix="/api/projects", tags=["assets"])


def _asset_to_response(asset: ProjectAsset) -> ProjectAssetResponse:
    return ProjectAssetResponse(
        id=asset.id,
        project_id=asset.project_id,
        original_name=asset.original_name,
        public_url=asset.public_url,
        media_type=asset.media_type,
        file_size=asset.file_size,
        kind=asset.kind,
        created_at=asset.created_at,
    )


def _get_owned_project(project_id: int, user_id: int, session: Session) -> Project:
    project = session.get(Project, project_id)
    if not project or project.user_id != user_id:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.get("/{project_id}/assets", response_model=List[ProjectAssetResponse])
def list_assets(
    project_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
):
    _get_owned_project(project_id, current_user.id, session)
    assets = session.exec(
        select(ProjectAsset)
        .where(ProjectAsset.project_id == project_id)
        .order_by(ProjectAsset.created_at.desc())
    ).all()
    return [_asset_to_response(asset) for asset in assets]


@router.post("/{project_id}/assets", response_model=List[ProjectAssetResponse], status_code=201)
async def upload_assets(
    project_id: int,
    files: Annotated[list[UploadFile], File(...)],
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
):
    project = _get_owned_project(project_id, current_user.id, session)
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")

    created: list[ProjectAsset] = []
    for file in files[:8]:
        payload = await save_project_asset(project_id, file)
        asset = ProjectAsset(project_id=project_id, **payload)
        session.add(asset)
        created.append(asset)

    project.updated_at = datetime.now(timezone.utc)
    session.add(project)
    session.commit()

    for asset in created:
        session.refresh(asset)
    return [_asset_to_response(asset) for asset in created]


@router.delete("/{project_id}/assets/{asset_id}", status_code=204)
def delete_asset(
    project_id: int,
    asset_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
):
    project = _get_owned_project(project_id, current_user.id, session)
    asset = session.get(ProjectAsset, asset_id)
    if not asset or asset.project_id != project_id:
        raise HTTPException(status_code=404, detail="Asset not found")

    delete_project_asset_file(asset)
    session.delete(asset)
    project.updated_at = datetime.now(timezone.utc)
    session.add(project)
    session.commit()
