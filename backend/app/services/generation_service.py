"""
生成服务：编排 LangGraph 多智能体执行，通过 WebSocket 推送状态。
"""
import asyncio
import json
from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Session, select

from app.agents.orchestrator import compiled_graph
from app.api.ws import manager
from app.core.database import get_session
from app.models import AgentRun, AppVersion, Conversation, Message, Project
from app.services.code_export import build_project_artifact
from app.services.image_generation import enrich_schema_with_generated_images
from app.services.preview_repair import repair_preview_payload


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
    """生成 WebSocket 回调函数，同时更新数据库中的 AgentRun 记录。"""
    async def callback(agent_name: str, status: str, summary: Optional[str]) -> None:
        now = datetime.now(timezone.utc)

        # 推送 WebSocket 消息
        await manager.broadcast(project_id, {
            "type": "agent_status",
            "agent": agent_name,
            "status": status,
            "summary": summary,
            "timestamp": now.isoformat(),
        })

        # 更新数据库 AgentRun
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
            pass  # 数据库更新失败不阻断主流程

    return callback


async def _init_agent_runs(version_id: int, engine) -> None:
    """预创建所有 Agent 的 pending 状态记录。"""
    agents = ["product", "design_director", "architect", "ui_builder", "code", "media", "qa"]
    with Session(engine) as db:
        for agent_name in agents:
            run = AgentRun(version_id=version_id, agent_name=agent_name)
            db.add(run)
        db.commit()


async def run_generation(
    project_id: int,
    version_id: int,
    prompt: str,
    app_type: str,
    engine,
) -> None:
    """
    异步后台任务：运行完整 Agent 链路，生成应用产物。
    由 asyncio.create_task 调用，不阻塞 HTTP 响应。
    """
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

    # 通知开始
    await manager.broadcast(project_id, {
        "type": "generation_status",
        "status": "running",
        "version_id": version_id,
    })

    try:
        initial_state = {
            "project_id": project_id,
            "version_id": version_id,
            "prompt": prompt,
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

        app_schema_payload = dict(repaired_schema)

        if preview_fixes:
            await ws_callback(
                "qa",
                "done",
                f"自动修复 {len(preview_fixes)} 处预览兼容问题",
            )

        # 保存产物到数据库
        with Session(engine) as db:
            version = db.get(AppVersion, version_id)
            if version:
                code_artifact = build_project_artifact(
                    prompt,
                    app_schema_payload,
                    repaired_bundle,
                )

                version.schema_json = json.dumps(app_schema_payload, ensure_ascii=False)
                version.code_json = json.dumps(code_artifact, ensure_ascii=False)
                version.status = "completed"
                db.add(version)

                # 更新项目 latest_version_id
                project = db.get(Project, project_id)
                if project:
                    project.latest_version_id = version_id
                    project.updated_at = datetime.now(timezone.utc)
                    db.add(project)

                db.commit()

        await manager.broadcast(project_id, {
            "type": "generation_status",
            "status": "completed",
            "version_id": version_id,
        })

    except Exception as e:
        # 标记版本失败
        try:
            with Session(engine) as db:
                version = db.get(AppVersion, version_id)
                if version:
                    version.status = "failed"
                    db.add(version)
                    db.commit()
        except Exception:
            pass

        await manager.broadcast(project_id, {
            "type": "generation_status",
            "status": "failed",
            "version_id": version_id,
            "error": str(e),
        })


async def run_race_lite(
    project_id: int,
    version_id_a: int,
    version_id_b: int,
    prompt: str,
    app_type: str,
    engine,
) -> None:
    """Race Lite：并行运行两个生成任务。"""
    await asyncio.gather(
        run_generation(project_id, version_id_a, prompt, app_type, engine),
        run_generation(project_id, version_id_b, prompt, app_type, engine),
    )
