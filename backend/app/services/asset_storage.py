"""Project asset storage and generation-time asset injection helpers."""

from __future__ import annotations

import shutil
import uuid
from pathlib import Path
from typing import Any

from fastapi import UploadFile

from app.core.config import settings
from app.models import ProjectAsset


DOCUMENT_MEDIA_TYPES = {
    "application/pdf",
    "text/plain",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
DATA_MEDIA_TYPES = {
    "text/csv",
    "application/json",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


def get_upload_root() -> Path:
    root = Path(settings.UPLOAD_DIR).expanduser()
    if not root.is_absolute():
      root = Path(__file__).resolve().parents[2] / root
    root.mkdir(parents=True, exist_ok=True)
    return root


def ensure_project_asset_dir(project_id: int) -> Path:
    directory = get_upload_root() / f"project_{project_id}"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


async def save_project_asset(project_id: int, file: UploadFile) -> dict[str, Any]:
    original_name = file.filename or "asset"
    suffix = Path(original_name).suffix.lower()
    stored_name = f"{uuid.uuid4().hex}{suffix}"
    project_dir = ensure_project_asset_dir(project_id)
    file_path = project_dir / stored_name

    with file_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    size = file_path.stat().st_size
    relative_path = file_path.relative_to(get_upload_root()).as_posix()
    media_type = file.content_type or "application/octet-stream"
    kind = _classify_asset_kind(media_type, suffix)
    public_url = f"{settings.PUBLIC_BACKEND_URL.rstrip('/')}/uploads/{relative_path}"

    return {
        "original_name": original_name,
        "stored_name": stored_name,
        "relative_path": relative_path,
        "public_url": public_url,
        "media_type": media_type,
        "file_size": size,
        "kind": kind,
    }


def delete_project_asset_file(asset: ProjectAsset) -> None:
    file_path = get_upload_root() / asset.relative_path
    if file_path.exists():
        file_path.unlink()


def build_asset_prompt_context(assets: list[ProjectAsset]) -> str:
    if not assets:
        return ""

    lines = [
        "Reference assets available for this project:",
    ]
    for asset in assets[:8]:
        lines.append(
            f"- {asset.original_name} ({asset.kind}, {asset.media_type}) -> {asset.public_url}"
        )

    lines.append(
        "Use uploaded images as primary visuals when suitable. Use document/data files as business context, naming hints, and content references."
    )
    return "\n".join(lines)


def inject_project_assets_into_schema(
    app_schema: dict[str, Any],
    assets: list[ProjectAsset],
) -> dict[str, Any]:
    image_assets = [asset for asset in assets if asset.kind == "image"]
    if not image_assets:
        return app_schema

    targets = _collect_visual_targets(app_schema)
    for asset, target in zip(image_assets, targets):
        target["props"][target["prop_key"]] = asset.public_url
        if target["prop_key"] == "src":
            target["props"].setdefault("alt", asset.original_name)
        else:
            target["props"].setdefault("image_alt", asset.original_name)

    app_schema["reference_assets"] = [
        {
            "id": asset.id,
            "name": asset.original_name,
            "kind": asset.kind,
            "url": asset.public_url,
        }
        for asset in assets[:8]
    ]
    return app_schema


def _classify_asset_kind(media_type: str, suffix: str) -> str:
    if media_type.startswith("image/"):
        return "image"
    if media_type in DOCUMENT_MEDIA_TYPES or suffix in {".pdf", ".txt", ".md", ".doc", ".docx"}:
        return "document"
    if media_type in DATA_MEDIA_TYPES or suffix in {".csv", ".json", ".xlsx", ".xls"}:
        return "data"
    return "other"


def _collect_visual_targets(app_schema: dict[str, Any]) -> list[dict[str, Any]]:
    targets: list[dict[str, Any]] = []

    def walk(node: dict[str, Any]) -> None:
        props = node.get("props", {})
        if not isinstance(props, dict):
            return

        if node.get("type") == "image":
            targets.append({"props": props, "prop_key": "src"})
        elif node.get("type") in {"hero", "split-section", "auth-card"}:
            targets.append({"props": props, "prop_key": "image_src"})

        for child in node.get("children", []) or []:
            if isinstance(child, dict):
                walk(child)

    for page in app_schema.get("pages", []) or []:
        if not isinstance(page, dict):
            continue
        for component in page.get("components", []) or []:
            if isinstance(component, dict):
                walk(component)

    return targets
