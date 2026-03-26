"""Orchestrate generation runs and persist version artifacts."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Session, select

from app.agents.orchestrator import compiled_graph
from app.api.ws import manager
from app.models import AgentRun, AppVersion, Project, ProjectAsset
from app.services.asset_storage import build_asset_prompt_context, inject_project_assets_into_schema
from app.services.code_export import build_project_artifact
from app.services.image_generation import enrich_schema_with_generated_images
from app.services.preview_repair import repair_preview_payload
from app.services.quality_guardian import run_quality_guardian
from app.services.site_codegen_service import generate_freeform_site_pack


def _has_renderable_schema(app_schema: object) -> bool:
    return (
        isinstance(app_schema, dict)
        and isinstance(app_schema.get("pages"), list)
        and len(app_schema.get("pages", [])) > 0
    )


def _has_code_bundle(code_bundle: object) -> bool:
    return isinstance(code_bundle, dict)


def _get_critical_error(errors: list[str]) -> Optional[str]:
    critical_agents = ("product agent", "architect agent", "code agent")
    for error in errors:
        lowered = error.lower()
        if any(agent in lowered for agent in critical_agents):
            return error
    return errors[0] if errors else None


async def _make_ws_callback(project_id: int, version_id: int, session_factory):
    async def callback(agent_name: str, status: str, summary: Optional[str]) -> None:
        now = datetime.now(timezone.utc)

        await manager.broadcast(
            project_id,
            {
                "type": "agent_status",
                "agent": agent_name,
                "status": status,
                "summary": summary,
                "timestamp": now.isoformat(),
            },
        )

        try:
            with Session(session_factory) as db:
                run = db.exec(
                    select(AgentRun)
                    .where(AgentRun.version_id == version_id)
                    .where(AgentRun.agent_name == agent_name)
                ).first()

                if run:
                    run.status = status
                    run.output_summary = summary
                    if status == "running":
                        run.started_at = now
                    elif status in ("done", "error"):
                        run.ended_at = now
                    db.add(run)
                    db.commit()
        except Exception:
            pass

    return callback


async def _init_agent_runs(version_id: int, engine) -> None:
    agents = ["product", "design_director", "architect", "ui_builder", "code", "media", "qa"]
    with Session(engine) as db:
        for agent_name in agents:
            db.add(AgentRun(version_id=version_id, agent_name=agent_name))
        db.commit()


def _get_project_assets(project_id: int, engine) -> list[ProjectAsset]:
    with Session(engine) as db:
        return list(
            db.exec(
                select(ProjectAsset)
                .where(ProjectAsset.project_id == project_id)
                .order_by(ProjectAsset.created_at.asc())
            ).all()
        )


async def run_generation(
    project_id: int,
    version_id: int,
    prompt: str,
    app_type: str,
    engine,
) -> None:
    await _init_agent_runs(version_id, engine)
    ws_callback = await _make_ws_callback(project_id, version_id, engine)

    try:
        with Session(engine) as db:
            version = db.get(AppVersion, version_id)
            if version:
                version.status = "running"
                db.add(version)
                db.commit()
    except Exception:
        pass

    await manager.broadcast(
        project_id,
        {
            "type": "generation_status",
            "status": "running",
            "version_id": version_id,
        },
    )

    try:
        project_assets = _get_project_assets(project_id, engine)
        generation_prompt = prompt
        asset_context = build_asset_prompt_context(project_assets)
        if asset_context:
            generation_prompt = f"{prompt}\n\n{asset_context}"

        initial_state = {
            "project_id": project_id,
            "version_id": version_id,
            "prompt": generation_prompt,
            "app_type": app_type,
            "prd_json": None,
            "design_brief": None,
            "app_schema": None,
            "ui_theme": None,
            "code_bundle": None,
            "qa_result": None,
            "qa_retry_count": 0,
            "errors": [],
            "ws_callback": ws_callback,
        }

        final_state = await compiled_graph.ainvoke(initial_state)
        errors = final_state.get("errors", [])
        app_schema = final_state.get("app_schema")
        code_bundle = final_state.get("code_bundle")
        ui_theme = final_state.get("ui_theme")
        design_brief = final_state.get("design_brief")
        critical_error = _get_critical_error(errors)

        if not _has_renderable_schema(app_schema):
            raise ValueError(critical_error or "Generation failed: missing app schema")

        raw_schema = dict(app_schema)
        if isinstance(design_brief, dict) and design_brief:
            raw_schema["design_brief"] = design_brief
        if isinstance(ui_theme, dict) and ui_theme:
            raw_schema["ui_theme"] = ui_theme

        repaired_schema, repaired_bundle, preview_fixes = repair_preview_payload(
            raw_schema,
            code_bundle if isinstance(code_bundle, dict) else None,
        )

        if not _has_code_bundle(repaired_bundle):
            raise ValueError(critical_error or "Generation failed: missing code bundle")

        await ws_callback("media", "running", "Generating supporting image assets")
        repaired_schema, image_result = await enrich_schema_with_generated_images(
            repaired_schema,
            prompt,
        )
        await ws_callback("media", "done", image_result.get("summary"))

        if project_assets:
            repaired_schema = inject_project_assets_into_schema(repaired_schema, project_assets)

        freeform_site_pack = await generate_freeform_site_pack(
            prompt=prompt,
            app_type=app_type,
            app_schema=repaired_schema,
            code_bundle=repaired_bundle,
        )
        code_artifact = build_project_artifact(
            prompt,
            repaired_schema,
            repaired_bundle,
            freeform_site=freeform_site_pack,
        )
        app_schema_payload, code_artifact, quality_report = run_quality_guardian(
            repaired_schema,
            repaired_bundle,
            code_artifact,
            preview_fixes=preview_fixes,
            image_result=image_result,
        )
        await ws_callback("qa", "done", quality_report.get("summary"))

        with Session(engine) as db:
            version = db.get(AppVersion, version_id)
            if version:
                version.schema_json = json.dumps(app_schema_payload, ensure_ascii=False)
                version.code_json = json.dumps(code_artifact, ensure_ascii=False)
                version.status = "completed"
                db.add(version)

                project = db.get(Project, project_id)
                if project:
                    project.latest_version_id = version_id
                    project.updated_at = datetime.now(timezone.utc)
                    db.add(project)

                db.commit()

        await manager.broadcast(
            project_id,
            {
                "type": "generation_status",
                "status": "completed",
                "version_id": version_id,
            },
        )
    except Exception as exc:
        try:
            with Session(engine) as db:
                version = db.get(AppVersion, version_id)
                if version:
                    version.status = "failed"
                    db.add(version)
                    db.commit()
        except Exception:
            pass

        await manager.broadcast(
            project_id,
            {
                "type": "generation_status",
                "status": "failed",
                "version_id": version_id,
                "error": str(exc),
            },
        )


async def run_race_lite(
    project_id: int,
    version_id_a: int,
    version_id_b: int,
    prompt: str,
    app_type: str,
    engine,
) -> None:
    await asyncio.gather(
        run_generation(project_id, version_id_a, prompt, app_type, engine),
        run_generation(project_id, version_id_b, prompt, app_type, engine),
    )
