"""Orchestrate direct page generation and persist version artifacts."""

from __future__ import annotations

import asyncio
import json
import re
from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Session, select

from app.agents.orchestrator import compiled_graph
from app.api.ws import manager
from app.core.config import settings
from app.models import AgentRun, AppVersion, Conversation, Message, Project, ProjectAsset
from app.services.asset_storage import build_asset_prompt_context, inject_project_assets_into_schema
from app.services.code_export import build_project_artifact
from app.services.image_generation import enrich_schema_with_generated_images
from app.services.preview_repair import repair_preview_payload
from app.services.quality_guardian import run_quality_guardian
from app.services.site_codegen_service import generate_freeform_site_pack


ACTIVE_AGENTS = ["product", "design_director", "media", "page_codegen", "qa"]
SUPPORTED_LAYOUTS = {"marketing", "editorial", "dashboard", "centered-auth", "workspace", "immersive"}
SINGLE_PAGE_KEYWORDS = (
    "发布页",
    "落地页",
    "单页",
    "首页",
    "倒计时",
    "报名",
    "landing",
    "launch",
    "release page",
    "homepage",
    "home page",
    "signup",
    "register",
    "login page",
    "登录页",
    "注册页",
)
MULTI_PAGE_KEYWORDS = ("多页", "多个页面", "multi-page", "multiple pages")


def _has_renderable_schema(app_schema: object) -> bool:
    return (
        isinstance(app_schema, dict)
        and isinstance(app_schema.get("pages"), list)
        and len(app_schema.get("pages", [])) > 0
    )


def _normalized_route(value: object) -> str:
    route = str(value or "").strip() or "/"
    return route if route.startswith("/") else f"/{route}"


def _planned_site_routes(site_plan: object, app_schema: object) -> list[str]:
    pages_source = None
    if isinstance(site_plan, dict) and isinstance(site_plan.get("pages"), list):
        pages_source = site_plan.get("pages")
    elif isinstance(app_schema, dict) and isinstance(app_schema.get("pages"), list):
        pages_source = app_schema.get("pages")
    else:
        pages_source = []

    routes: list[str] = []
    seen: set[str] = set()
    for page in pages_source:
        if not isinstance(page, dict):
            continue
        route = _normalized_route(page.get("route"))
        if route in seen:
            continue
        seen.add(route)
        routes.append(route)
    return routes


def _get_critical_error(errors: list[str]) -> Optional[str]:
    critical_agents = ("product agent", "design director")
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
                if not run:
                    return

                run.status = status
                run.output_summary = summary
                if status == "running":
                    run.started_at = now
                    run.ended_at = None
                elif status in {"done", "error"}:
                    run.ended_at = now
                db.add(run)
                db.commit()
        except Exception:
            pass

    return callback


def _append_project_message(
    engine,
    project_id: int,
    role: str,
    content: str,
    *,
    agent_name: str | None = None,
) -> None:
    try:
        with Session(engine) as db:
            conversation = db.exec(
                select(Conversation).where(Conversation.project_id == project_id)
            ).first()
            if not conversation:
                return
            db.add(
                Message(
                    conversation_id=conversation.id,
                    role=role,
                    agent_name=agent_name,
                    content=content,
                )
            )
            db.commit()
    except Exception:
        pass


def _persist_version_payload(
    engine,
    *,
    project_id: int,
    version_id: int,
    app_schema_payload: dict,
    code_artifact: dict,
    status: str,
    update_latest_version: bool,
) -> None:
    with Session(engine) as db:
        version = db.get(AppVersion, version_id)
        if not version:
            return

        version.schema_json = json.dumps(
            _build_persisted_generation_metadata(app_schema_payload, code_artifact),
            ensure_ascii=False,
        )
        version.code_json = json.dumps(code_artifact, ensure_ascii=False)
        version.status = status
        db.add(version)

        if update_latest_version:
            project = db.get(Project, project_id)
            if project:
                project.latest_version_id = version_id
                project.updated_at = datetime.now(timezone.utc)
                db.add(project)

        db.commit()


def _build_persisted_generation_metadata(
    app_schema_payload: dict,
    code_artifact: dict,
) -> dict:
    navigation = (
        app_schema_payload.get("navigation")
        if isinstance(app_schema_payload.get("navigation"), list)
        else []
    )
    data_models = (
        app_schema_payload.get("data_models")
        if isinstance(app_schema_payload.get("data_models"), list)
        else []
    )
    site_plan = app_schema_payload.get("site_plan") if isinstance(app_schema_payload.get("site_plan"), dict) else {}
    design_brief = (
        app_schema_payload.get("design_brief")
        if isinstance(app_schema_payload.get("design_brief"), dict)
        else {}
    )
    ui_theme = (
        app_schema_payload.get("ui_theme")
        if isinstance(app_schema_payload.get("ui_theme"), dict)
        else {}
    )
    quality_report = (
        code_artifact.get("quality_report")
        if isinstance(code_artifact.get("quality_report"), dict)
        else app_schema_payload.get("quality_report")
        if isinstance(app_schema_payload.get("quality_report"), dict)
        else None
    )
    generated_files = [
        str(item.get("path"))
        for item in code_artifact.get("files", [])
        if isinstance(item, dict) and item.get("path")
    ]
    html_entries = [path for path in generated_files if path.endswith(".html")]

    return {
        "kind": "generation_metadata_v1",
        "app_id": str(app_schema_payload.get("app_id") or ""),
        "title": str(app_schema_payload.get("title") or "Generated App"),
        "app_type": str(app_schema_payload.get("app_type") or "auto"),
        "content_language": str(app_schema_payload.get("content_language") or "en-US"),
        "layout_archetype": str(app_schema_payload.get("layout_archetype") or ""),
        "navigation": navigation,
        "data_models": data_models,
        "design_brief": design_brief,
        "site_plan": site_plan,
        "ui_theme": ui_theme,
        "quality_report": quality_report,
        "artifact_summary": {
            "format": str(code_artifact.get("format") or ""),
            "entry": str(code_artifact.get("entry") or ""),
            "file_count": len(generated_files),
            "html_entries": html_entries[:12],
        },
    }


async def _init_agent_runs(version_id: int, engine) -> None:
    with Session(engine) as db:
        for agent_name in ACTIVE_AGENTS:
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


def _slugify(value: object, fallback: str) -> str:
    text = re.sub(r"[^a-zA-Z0-9]+", "-", str(value or "").strip().lower()).strip("-")
    return text or fallback


def _is_chinese_language(language: str) -> bool:
    return language.lower() == "zh-cn"


def _localized(language: str, zh: str, en: str) -> str:
    return zh if _is_chinese_language(language) else en


def _infer_content_language(prd_json: dict, design_brief: dict | None) -> str:
    return str(
        prd_json.get("content_language")
        or (design_brief or {}).get("content_language")
        or "en-US"
    ).strip() or "en-US"


def _infer_layout(design_brief: dict | None, app_type: str) -> str:
    layout = str((design_brief or {}).get("layout_archetype") or "").strip().lower()
    if layout in SUPPORTED_LAYOUTS:
        return layout

    lowered_type = str(app_type or "").lower()
    if re.search(r"login|signin|signup|register|auth", lowered_type):
        return "centered-auth"
    if re.search(r"landing|marketing|launch|release|campaign|showcase", lowered_type):
        return "immersive"
    if re.search(r"dashboard|analytics|admin|crm|internal", lowered_type):
        return "dashboard"
    return "workspace"


def _derive_ui_theme(design_brief: dict | None) -> dict:
    brief = design_brief or {}
    theme_mode = str(brief.get("theme_mode") or "light").strip().lower()
    color_story = str(brief.get("color_story") or "").lower()
    is_dark = theme_mode == "dark" or "dark" in color_story or "black" in color_story or "暗" in color_story
    return {
        "theme_mode": "dark" if is_dark else "light",
        "primary_color": "#8b5cf6" if is_dark else "#2563eb",
        "secondary_color": "#22d3ee" if is_dark else "#7c3aed",
        "background_color": "#050816" if is_dark else "#f8fafc",
        "surface_color": "#0f172a" if is_dark else "#ffffff",
        "text_color": "#e2e8f0" if is_dark else "#0f172a",
        "muted_text_color": "#94a3b8" if is_dark else "#475569",
    }


def _should_force_single_page(prompt: str, prd_json: dict, design_brief: dict | None) -> bool:
    text = " ".join(
        [
            str(prompt or ""),
            str(prd_json.get("app_title") or ""),
            " ".join(str(item or "") for item in prd_json.get("features", []) if isinstance(item, str)),
            " ".join(str(item or "") for item in prd_json.get("pages", []) if isinstance(item, str)),
            str((design_brief or {}).get("visual_direction") or ""),
            str((design_brief or {}).get("experience_goal") or ""),
        ]
    ).lower()
    if any(keyword in text for keyword in MULTI_PAGE_KEYWORDS):
        return False
    return any(keyword in text for keyword in SINGLE_PAGE_KEYWORDS)


def _direct_page_names(prompt: str, prd_json: dict, design_brief: dict | None, language: str) -> list[str]:
    raw_pages = [str(item or "").strip() for item in prd_json.get("pages", []) if str(item or "").strip()]
    if _should_force_single_page(prompt, prd_json, design_brief):
        if re.search(r"login|signin|登录", prompt, re.IGNORECASE):
            return [_localized(language, "登录页", "Login")]
        if re.search(r"register|signup|注册", prompt, re.IGNORECASE):
            return [_localized(language, "注册页", "Register")]
        return [_localized(language, "首页", "Home")]

    unique: list[str] = []
    seen: set[str] = set()
    for item in raw_pages:
        if item in seen:
            continue
        seen.add(item)
        unique.append(item)
        if len(unique) >= 4:
            break
    return unique or [_localized(language, "首页", "Home")]


def _section_type(pattern: str) -> str:
    text = str(pattern or "").strip().lower()
    if text in {"hero", "feature-grid", "stats-band", "split-section", "cta-band", "auth-card"}:
        return text
    if any(keyword in text for keyword in ("countdown", "timer", "stats")):
        return "stats-band"
    if any(keyword in text for keyword in ("feature", "highlight", "benefit")):
        return "feature-grid"
    if any(keyword in text for keyword in ("signup", "register", "form", "contact", "cta")):
        return "cta-band"
    if any(keyword in text for keyword in ("auth", "login", "signin")):
        return "auth-card"
    return "split-section"


def _build_key_sections(prd_json: dict, design_brief: dict | None, title: str, language: str) -> list[dict]:
    recommendations = [
        str(item or "").strip()
        for item in (design_brief or {}).get("section_recommendations", [])
        if str(item or "").strip()
    ]
    features = [
        str(item or "").strip()
        for item in prd_json.get("features", [])
        if str(item or "").strip()
    ]

    source_patterns = recommendations[:6] or ["hero", "feature-grid", "cta-band"]
    sections: list[dict] = []
    for index, pattern in enumerate(source_patterns):
        goal = features[index] if index < len(features) else _localized(
            language,
            f"突出 {title} 的核心体验与下一步转化",
            f"Present {title}'s core experience and next conversion step",
        )
        sections.append(
            {
                "id": f"section-{index + 1}",
                "type": _section_type(pattern),
                "goal": goal,
            }
        )
    return sections


def _build_direct_generation_payload(
    *,
    prompt: str,
    app_type: str,
    prd_json: dict,
    design_brief: dict | None,
) -> tuple[dict, dict, dict, dict]:
    title = str(prd_json.get("app_title") or "Generated App").strip() or "Generated App"
    language = _infer_content_language(prd_json, design_brief)
    layout = _infer_layout(design_brief, app_type or str(prd_json.get("app_type") or ""))
    ui_theme = _derive_ui_theme(design_brief)
    page_names = _direct_page_names(prompt, prd_json, design_brief, language)
    shared_sections = _build_key_sections(prd_json, design_brief, title, language)

    pages: list[dict] = []
    for index, name in enumerate(page_names):
        route = "/" if index == 0 else f"/{_slugify(name, f'page-{index + 1}')}"
        pages.append(
            {
                "id": _slugify(name, f"page-{index + 1}"),
                "name": name,
                "route": route,
                "purpose": _localized(language, f"{name} 的核心体验页", f"Primary experience for {name}"),
                "layout_archetype": layout,
                "key_sections": json.loads(json.dumps(shared_sections, ensure_ascii=False)),
            }
        )

    navigation = [{"label": page["name"], "route": page["route"]} for page in pages]
    site_plan = {
        "app_id": _slugify(title, "generated-app"),
        "title": title,
        "app_type": app_type or str(prd_json.get("app_type") or "auto"),
        "content_language": language,
        "layout_archetype": layout,
        "navigation": navigation,
        "data_models": [],
        "pages": pages,
    }
    app_schema = {
        "app_id": site_plan["app_id"],
        "title": title,
        "app_type": site_plan["app_type"],
        "content_language": language,
        "layout_archetype": layout,
        "navigation": navigation,
        "data_models": [],
        "pages": [
            {
                "id": page["id"],
                "name": page["name"],
                "route": page["route"],
                "layout_archetype": layout,
                "components": [],
            }
            for page in pages
        ],
    }
    code_bundle = {
        "form_handlers": [],
        "data_bindings": [],
        "initial_state": {},
        "page_transitions": [],
    }
    return site_plan, app_schema, code_bundle, ui_theme


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
    _append_project_message(
        engine,
        project_id,
        "assistant",
        "已进入自动生成流程，正在依次执行 Product、Design Director、Media、应用生成引擎、QA 五个步骤。",
    )

    try:
        project_assets = _get_project_assets(project_id, engine)
        generation_prompt = prompt
        asset_context = build_asset_prompt_context(project_assets)
        if asset_context:
            generation_prompt = f"{prompt}\n\n{asset_context}"

        final_state = await compiled_graph.ainvoke(
            {
                "project_id": project_id,
                "version_id": version_id,
                "prompt": generation_prompt,
                "app_type": app_type,
                "prd_json": None,
                "design_brief": None,
                "site_plan": None,
                "app_schema": None,
                "ui_theme": None,
                "code_bundle": None,
                "qa_result": None,
                "qa_retry_count": 0,
                "errors": [],
                "ws_callback": ws_callback,
            }
        )

        errors = final_state.get("errors", [])
        prd_json = final_state.get("prd_json")
        design_brief = final_state.get("design_brief")
        critical_error = _get_critical_error(errors)

        if not isinstance(prd_json, dict) or not prd_json:
            raise ValueError(critical_error or "Generation failed: missing product brief")

        site_plan, app_schema, code_bundle, ui_theme = _build_direct_generation_payload(
            prompt=prompt,
            app_type=app_type,
            prd_json=prd_json,
            design_brief=design_brief if isinstance(design_brief, dict) else None,
        )

        if not _has_renderable_schema(app_schema):
            raise ValueError(critical_error or "Generation failed: missing direct site payload")

        raw_schema = dict(app_schema)
        raw_schema["prd_json"] = prd_json
        if isinstance(design_brief, dict) and design_brief:
            raw_schema["design_brief"] = design_brief
        raw_schema["site_plan"] = site_plan
        raw_schema["ui_theme"] = ui_theme

        repaired_schema, repaired_bundle, preview_fixes = repair_preview_payload(
            raw_schema,
            code_bundle,
        )

        await ws_callback("media", "running", "Generating supporting image assets")
        repaired_schema, image_result = await enrich_schema_with_generated_images(
            repaired_schema,
            prompt,
        )
        await ws_callback("media", "done", image_result.get("summary"))

        if project_assets:
            repaired_schema = inject_project_assets_into_schema(repaired_schema, project_assets)

        await ws_callback("page_codegen", "running", "Generating final site pages")

        site_codegen_timeout = settings.SITE_CODEGEN_FULL_TIMEOUT_SECONDS
        try:
            full_site_pack = await asyncio.wait_for(
                generate_freeform_site_pack(
                    prompt=generation_prompt,
                    app_type=app_type,
                    app_schema=repaired_schema,
                    code_bundle=repaired_bundle,
                    prd_json=prd_json,
                    design_brief=design_brief if isinstance(design_brief, dict) else None,
                    site_plan=site_plan,
                    ui_theme=ui_theme,
                ),
                timeout=site_codegen_timeout,
            )
        except asyncio.TimeoutError:
            await ws_callback(
                "page_codegen",
                "error",
                f"Application code generation timed out after {site_codegen_timeout}s",
            )
            raise ValueError(f"应用代码生成超时，等待超过 {site_codegen_timeout}s")

        expected_routes = _planned_site_routes(site_plan, repaired_schema)
        generated_routes = {
            _normalized_route(item.get("route"))
            for item in (full_site_pack or {}).get("pages", [])
            if isinstance(item, dict)
        }
        missing_routes = [route for route in expected_routes if route not in generated_routes]
        if not full_site_pack or missing_routes:
            if missing_routes:
                missing_text = ", ".join(missing_routes[:5])
                await ws_callback(
                    "page_codegen",
                    "error",
                    f"Application output incomplete; missing routes: {missing_text}",
                )
                raise ValueError(
                    f"应用生成不完整，缺少关键界面：{missing_text}"
                )
            await ws_callback("page_codegen", "error", "Application code generation returned no usable output")
            raise ValueError("应用代码生成失败，未产出可用结果")

        await ws_callback("page_codegen", "done", "应用代码与预览内容已生成")

        await ws_callback("qa", "running", "Validating generated application and packaging preview")
        code_artifact = build_project_artifact(
            prompt,
            repaired_schema,
            repaired_bundle,
            freeform_site=full_site_pack,
        )
        app_schema_payload, code_artifact, quality_report = run_quality_guardian(
            repaired_schema,
            repaired_bundle,
            code_artifact,
            preview_fixes=preview_fixes,
            image_result=image_result,
        )
        await ws_callback(
            "qa",
            "done",
            quality_report.get("summary") if isinstance(quality_report, dict) else "应用代码与预览已生成",
        )

        _persist_version_payload(
            engine,
            project_id=project_id,
            version_id=version_id,
            app_schema_payload=app_schema_payload,
            code_artifact=code_artifact,
            status="completed",
            update_latest_version=True,
        )

        await manager.broadcast(
            project_id,
            {
                "type": "generation_status",
                "status": "completed",
                "version_id": version_id,
            },
        )
        _append_project_message(
            engine,
            project_id,
            "assistant",
            "应用生成完成，可以在右侧预览和查看文件。",
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
        _append_project_message(
            engine,
            project_id,
            "assistant",
            f"应用生成失败：{str(exc)}",
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
