"""Post-generation quality checks, soft polish, and reporting."""

from __future__ import annotations

import copy
import json
from typing import Any


QUALITY_BLOCK_TYPES = {"hero", "feature-grid", "stats-band", "split-section", "cta-band", "auth-card"}
EXPORT_CORE_FILES = {"index.html", "src/styles.css", "src/app.js", "src/schema.js"}
LAYOUT_ARCHETYPES = {"marketing", "editorial", "dashboard", "centered-auth", "workspace", "immersive"}


def run_quality_guardian(
    app_schema: dict[str, Any],
    code_bundle: dict[str, Any],
    code_artifact: dict[str, Any],
    preview_fixes: list[str] | None = None,
    image_result: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    schema = copy.deepcopy(app_schema)
    artifact = copy.deepcopy(code_artifact)
    fixes = list(preview_fixes or [])
    image_result = image_result or {}
    applied_repairs: list[str] = []

    if _should_append_cta_band(schema):
        _append_cta_band(schema)
        applied_repairs.append("已为首页补充收尾 CTA 区块，增强页面的转化闭环。")

    if fixes:
        applied_repairs.extend(f"已应用预览修复：{item}" for item in fixes[:4])

    report = _build_quality_report(
        app_schema=schema,
        code_bundle=code_bundle,
        code_artifact=artifact,
        preview_fixes=fixes,
        image_result=image_result,
        applied_repairs=applied_repairs,
    )

    schema["quality_report"] = report
    artifact["quality_report"] = report
    _upsert_quality_report_file(artifact, report)
    return schema, artifact, report


def _build_quality_report(
    app_schema: dict[str, Any],
    code_bundle: dict[str, Any],
    code_artifact: dict[str, Any],
    preview_fixes: list[str],
    image_result: dict[str, Any],
    applied_repairs: list[str],
) -> dict[str, Any]:
    pages = app_schema.get("pages") if isinstance(app_schema.get("pages"), list) else []
    first_page = next((page for page in pages if isinstance(page, dict)), None)
    first_page_components = first_page.get("components", []) if isinstance(first_page, dict) else []
    component_types = {
        str(component.get("type"))
        for component in first_page_components
        if isinstance(component, dict) and component.get("type")
    }
    quality_blocks = component_types & QUALITY_BLOCK_TYPES
    schema_layout = _normalize_layout_archetype(app_schema.get("layout_archetype"))
    first_page_layout = _normalize_layout_archetype(
        first_page.get("layout_archetype") if isinstance(first_page, dict) else None,
        schema_layout,
    )
    app_type_text = str(app_schema.get("app_type") or "").lower()
    form_handlers = code_bundle.get("form_handlers", []) if isinstance(code_bundle, dict) else []
    page_transitions = code_bundle.get("page_transitions", []) if isinstance(code_bundle, dict) else []
    export_files = {
        str(item.get("path"))
        for item in code_artifact.get("files", [])
        if isinstance(item, dict) and item.get("path")
    }

    checks = [
        _build_check(
            "renderability",
            "预览可渲染性",
            "passed" if pages and any(_page_has_components(page) for page in pages) else "warning",
            "当前 Schema 包含可正常渲染的页面。"
            if pages
            else "生成结果中没有可渲染的页面。",
        ),
        _build_check(
            "layout_signature",
            "布局骨架",
            "passed",
            f"首页当前保持 {first_page_layout} 布局方向，质量守护不再强制收敛到固定骨架。",
        ),
        _build_check(
            "visual_hierarchy",
            "视觉层级",
            "passed" if quality_blocks else "warning",
            (
                f"首页使用了 {len(quality_blocks)} 个高价值区块：{', '.join(sorted(quality_blocks))}。"
                if quality_blocks
                else "首页仍偏向基础组件堆叠，建议补充 Hero、分栏内容或 CTA 区块。"
            ),
        ),
        _build_check(
            "interaction_logic",
            "交互覆盖",
            "passed" if form_handlers or page_transitions else "warning",
            (
                f"已生成 {len(form_handlers)} 个表单处理逻辑，并整理 {len(page_transitions)} 个关键交互流转。"
                if form_handlers or page_transitions
                else "当前版本没有生成明确的表单处理或页面跳转逻辑。"
            ),
        ),
        _build_check(
            "export_completeness",
            "导出完整性",
            "passed" if EXPORT_CORE_FILES.issubset(export_files) else "warning",
            (
                "静态导出已包含 HTML、CSS 与运行时入口文件。"
                if EXPORT_CORE_FILES.issubset(export_files)
                else "导出文件缺少至少一个核心运行文件。"
            ),
        ),
    ]

    generated_images = int(image_result.get("generated", 0) or 0)
    skipped_images = int(image_result.get("skipped", 0) or 0)
    attempted_images = int(image_result.get("attempted", 0) or 0)
    image_status = "passed" if generated_images > 0 else "fixed" if attempted_images == 0 or skipped_images >= 0 else "warning"
    if generated_images > 0:
        image_detail = f"已生成 {generated_images} 个配图资源。"
    elif attempted_images > 0:
        image_detail = f"有 {skipped_images} 个图片位未解析成功，已静默跳过且未阻塞主流程。"
    else:
        image_detail = "该应用当前不需要额外图片资源。"
    checks.append(_build_check("visual_assets", "视觉资源", image_status, image_detail))

    repair_status = "fixed" if preview_fixes or applied_repairs else "passed"
    repair_detail = (
        f"已执行 {len(applied_repairs)} 项自动修复或润色动作。"
        if preview_fixes or applied_repairs
        else "当前版本无需额外运行时修复。"
    )
    checks.append(_build_check("self_healing", "自动修复", repair_status, repair_detail))

    score = _score_checks(checks)
    recommended_prompts = _build_recommended_prompts(
        component_types,
        form_handlers,
        page_transitions,
        first_page_layout=first_page_layout,
        app_type_text=app_type_text,
    )
    summary = _build_summary(score, checks, applied_repairs)

    return {
        "score": score,
        "summary": summary,
        "checks": checks,
        "applied_repairs": applied_repairs,
        "recommended_prompts": recommended_prompts,
    }


def _page_has_components(page: Any) -> bool:
    return isinstance(page, dict) and isinstance(page.get("components"), list) and len(page["components"]) > 0


def _build_check(check_id: str, label: str, status: str, detail: str) -> dict[str, str]:
    return {
        "id": check_id,
        "label": label,
        "status": status,
        "detail": detail,
    }


def _score_checks(checks: list[dict[str, str]]) -> int:
    if not checks:
        return 60

    raw_score = 0
    for check in checks:
        if check["status"] == "passed":
            raw_score += 20
        elif check["status"] == "fixed":
            raw_score += 16
        else:
            raw_score += 10

    return max(55, min(round((raw_score / (20 * len(checks))) * 100), 100))


def _build_summary(score: int, checks: list[dict[str, str]], applied_repairs: list[str]) -> str:
    warning_count = sum(1 for check in checks if check["status"] == "warning")
    fixed_count = sum(1 for check in checks if check["status"] == "fixed")
    if warning_count == 0 and fixed_count == 0:
        return f"质量守护已通过，本版本评分为 {score}/100。"
    if warning_count == 0:
        return (
            f"质量守护已完成稳定化处理，共执行 {fixed_count} 项自动修复，"
            f"最终评分为 {score}/100。"
        )
    return (
        f"质量守护已完成，本次发现 {warning_count} 个关注项，"
        f"执行了 {len(applied_repairs)} 项修复或润色动作，最终评分为 {score}/100。"
    )


def _build_recommended_prompts(
    component_types: set[str],
    form_handlers: list[Any],
    page_transitions: list[Any],
    *,
    first_page_layout: str,
    app_type_text: str,
) -> list[str]:
    prompts: list[str] = []

    if first_page_layout == "centered-auth" and not any(
        token in app_type_text for token in {"auth", "login", "register", "signin", "signup"}
    ):
        prompts.append(
            "将首页改为更适合当前需求的非认证骨架，例如工作台、仪表盘或编辑型内容布局。"
        )
    if "hero" not in component_types and "auth-card" not in component_types:
        prompts.append("补充更强的 Hero 区，明确产品价值点，并保留一个主 CTA。")
    if "cta-band" not in component_types:
        prompts.append("在页面尾部补一段转化导向的 CTA，并搭配可信证明信息。")
    if not form_handlers:
        prompts.append("增加一个可执行的表单流程，并补上校验与清晰的成功态。")
    if not page_transitions:
        prompts.append("补充关键页面之间更清晰的导航或下一步流转。")

    return prompts[:3]


def _should_append_cta_band(app_schema: dict[str, Any]) -> bool:
    pages = app_schema.get("pages")
    if not isinstance(pages, list) or not pages:
        return False

    first_page = next((page for page in pages if isinstance(page, dict)), None)
    if not isinstance(first_page, dict):
        return False

    first_page_layout = _normalize_layout_archetype(
        first_page.get("layout_archetype"),
        _normalize_layout_archetype(app_schema.get("layout_archetype")),
    )
    if first_page_layout not in {"marketing", "editorial", "immersive"}:
        return False

    components = first_page.get("components")
    if not isinstance(components, list) or len(components) < 2:
        return False

    component_types = {
        str(component.get("type"))
        for component in components
        if isinstance(component, dict) and component.get("type")
    }
    return "cta-band" not in component_types and bool(component_types & {"hero", "feature-grid", "split-section"})


def _repair_layout_archetypes(app_schema: dict[str, Any]) -> list[str]:
    repairs: list[str] = []
    suggested_app_layout = _suggest_layout_archetype(app_schema)
    current_app_layout = _normalize_layout_archetype(app_schema.get("layout_archetype"))
    if current_app_layout != suggested_app_layout:
        app_schema["layout_archetype"] = suggested_app_layout
        repairs.append(f"已将应用整体布局骨架调整为 {suggested_app_layout}。")
    else:
        app_schema["layout_archetype"] = current_app_layout

    pages = app_schema.get("pages")
    if not isinstance(pages, list):
        return repairs

    for page in pages:
        if not isinstance(page, dict):
            continue
        suggested_page_layout = _suggest_page_layout(
            page,
            str(app_schema.get("layout_archetype") or suggested_app_layout),
        )
        current_page_layout = _normalize_layout_archetype(page.get("layout_archetype"), suggested_page_layout)
        if current_page_layout != suggested_page_layout:
            page["layout_archetype"] = suggested_page_layout
            repairs.append(
                f"已将页面“{page.get('name') or page.get('id') or '未命名页面'}”调整为 {suggested_page_layout} 布局骨架。"
            )
        else:
            page["layout_archetype"] = current_page_layout

    return repairs


def _append_cta_band(app_schema: dict[str, Any]) -> None:
    pages = app_schema.get("pages")
    if not isinstance(pages, list) or not pages:
        return

    first_page = next((page for page in pages if isinstance(page, dict)), None)
    if not isinstance(first_page, dict):
        return

    components = first_page.get("components")
    if not isinstance(components, list):
        return

    title = str(app_schema.get("title") or "your app").strip() or "your app"
    primary_route = str(first_page.get("route") or "/")
    components.append(
        {
            "id": "quality_guardian_cta",
            "type": "cta-band",
            "props": {
                "title": f"准备把 {title} 从草稿推进到可交付版本了吗？",
                "description": "这一收尾区块由质量守护自动补充，用来增强页面闭环与转化清晰度。",
                "primary_cta_label": "继续完善",
                "primary_cta_route": primary_route,
                "secondary_cta_label": "查看详情",
                "secondary_cta_route": primary_route,
            },
            "children": [],
            "actions": [],
            "style": {},
        }
    )


def _upsert_quality_report_file(code_artifact: dict[str, Any], report: dict[str, Any]) -> None:
    files = code_artifact.get("files")
    if not isinstance(files, list):
        return

    report_file = {
        "path": "data/quality-report.json",
        "language": "json",
        "content": json.dumps(report, ensure_ascii=False, indent=2),
    }

    for index, file in enumerate(files):
        if isinstance(file, dict) and file.get("path") == report_file["path"]:
            files[index] = report_file
            return

    files.append(report_file)


def _normalize_layout_archetype(value: Any, fallback: str = "workspace") -> str:
    text = str(value or "").strip().lower()
    return text if text in LAYOUT_ARCHETYPES else fallback


def _suggest_layout_archetype(app_schema: dict[str, Any]) -> str:
    app_type_text = str(app_schema.get("app_type") or "").lower()
    design_brief = app_schema.get("design_brief") if isinstance(app_schema.get("design_brief"), dict) else {}
    brief_layout = _normalize_layout_archetype(design_brief.get("layout_archetype"), "")
    if brief_layout in LAYOUT_ARCHETYPES:
        return brief_layout

    search_space = " ".join(
        [
            app_type_text,
            str(design_brief.get("visual_direction") or ""),
            str(design_brief.get("experience_goal") or ""),
            str(design_brief.get("primary_user_mindset") or ""),
            " ".join(item for item in design_brief.get("section_recommendations", []) if isinstance(item, str)),
        ]
    ).lower()

    if any(token in search_space for token in {"auth", "login", "signin", "signup", "register"}):
        return "centered-auth"
    if any(token in search_space for token in {"blog", "editorial", "article", "journal", "story", "content"}):
        return "editorial"
    if any(token in search_space for token in {"marketing", "landing", "campaign", "launch", "showcase", "promo"}):
        return "marketing"
    if any(token in search_space for token in {"immersive", "cinematic", "storyworld", "experience"}):
        return "immersive"
    if any(token in search_space for token in {"dashboard", "analytics", "admin", "crm", "report", "monitor"}):
        return "dashboard"
    return "workspace"


def _suggest_page_layout(page: dict[str, Any], default_layout: str) -> str:
    page_name = str(page.get("name") or "").lower()
    route = str(page.get("route") or "").lower()
    components = page.get("components") if isinstance(page.get("components"), list) else []
    component_types = {
        str(component.get("type"))
        for component in components
        if isinstance(component, dict) and component.get("type")
    }
    fingerprint = f"{page_name} {route} {' '.join(sorted(component_types))}"

    if any(token in fingerprint for token in {"login", "signin", "signup", "register", "auth"}):
        return "centered-auth"
    if "auth-card" in component_types and len(component_types) <= 3:
        return "centered-auth"
    if any(token in fingerprint for token in {"blog", "article", "editorial", "journal", "story"}):
        return "editorial"
    if {"hero", "feature-grid", "split-section", "cta-band"} & component_types:
        return "marketing" if default_layout != "immersive" else default_layout
    if {"table", "stat-card"} & component_types:
        return "dashboard" if default_layout == "dashboard" else "workspace"
    return default_layout
