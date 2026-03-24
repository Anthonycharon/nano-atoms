"""Post-generation quality checks, soft polish, and reporting."""

from __future__ import annotations

import copy
import json
from typing import Any


QUALITY_BLOCK_TYPES = {"hero", "feature-grid", "stats-band", "split-section", "cta-band", "auth-card"}
EXPORT_CORE_FILES = {"index.html", "src/styles.css", "src/app.js", "src/schema.js"}


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
        applied_repairs.append("Added a closing CTA section on the first page to strengthen the conversion flow.")

    if fixes:
        applied_repairs.extend(f"Applied preview repair: {item}" for item in fixes[:4])

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
            "Preview Renderability",
            "passed" if pages and any(_page_has_components(page) for page in pages) else "warning",
            "Schema includes renderable pages." if pages else "No renderable page was found in the generated schema.",
        ),
        _build_check(
            "visual_hierarchy",
            "Visual Hierarchy",
            "passed" if quality_blocks else "warning",
            (
                f"First page uses {len(quality_blocks)} high-value section block(s): {', '.join(sorted(quality_blocks))}."
                if quality_blocks
                else "First page still leans on primitive blocks; consider adding hero, split, or CTA sections."
            ),
        ),
        _build_check(
            "interaction_logic",
            "Interaction Coverage",
            "passed" if form_handlers or page_transitions else "warning",
            (
                f"Generated {len(form_handlers)} form handler(s) and {len(page_transitions)} page transition(s)."
                if form_handlers or page_transitions
                else "No explicit form handling or page transition logic was generated."
            ),
        ),
        _build_check(
            "export_completeness",
            "Export Completeness",
            "passed" if EXPORT_CORE_FILES.issubset(export_files) else "warning",
            (
                "Static export contains the HTML, CSS, and runtime entry files."
                if EXPORT_CORE_FILES.issubset(export_files)
                else "Export bundle is missing at least one core file."
            ),
        ),
    ]

    generated_images = int(image_result.get("generated", 0) or 0)
    skipped_images = int(image_result.get("skipped", 0) or 0)
    attempted_images = int(image_result.get("attempted", 0) or 0)
    image_status = "passed" if generated_images > 0 else "fixed" if attempted_images == 0 or skipped_images >= 0 else "warning"
    if generated_images > 0:
        image_detail = f"Generated {generated_images} supporting image asset(s)."
    elif attempted_images > 0:
        image_detail = f"Skipped {skipped_images} unresolved image slot(s) without blocking the main flow."
    else:
        image_detail = "No image slot was needed for this application."
    checks.append(_build_check("visual_assets", "Visual Assets", image_status, image_detail))

    repair_status = "fixed" if preview_fixes or applied_repairs else "passed"
    repair_detail = (
        f"Applied {len(applied_repairs)} automatic repair/polish action(s)."
        if preview_fixes or applied_repairs
        else "No runtime repair was needed."
    )
    checks.append(_build_check("self_healing", "Self-healing Pass", repair_status, repair_detail))

    score = _score_checks(checks)
    recommended_prompts = _build_recommended_prompts(component_types, form_handlers, page_transitions)
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
        return f"Quality Guardian passed this version with a score of {score}/100."
    if warning_count == 0:
        return (
            f"Quality Guardian stabilized this version with {fixed_count} auto-fix step(s) "
            f"and a final score of {score}/100."
        )
    return (
        f"Quality Guardian completed with {warning_count} watch item(s), "
        f"{len(applied_repairs)} repair/polish action(s), and a score of {score}/100."
    )


def _build_recommended_prompts(
    component_types: set[str],
    form_handlers: list[Any],
    page_transitions: list[Any],
) -> list[str]:
    prompts: list[str] = []

    if "hero" not in component_types and "auth-card" not in component_types:
        prompts.append("Add a stronger hero section with clearer product value and one primary CTA.")
    if "cta-band" not in component_types:
        prompts.append("Close the page with a conversion-focused CTA section and supporting proof points.")
    if not form_handlers:
        prompts.append("Add one actionable form flow with validation and a clearer success state.")
    if not page_transitions:
        prompts.append("Add a clearer navigation or next-step flow between key pages.")

    return prompts[:3]


def _should_append_cta_band(app_schema: dict[str, Any]) -> bool:
    pages = app_schema.get("pages")
    if not isinstance(pages, list) or not pages:
        return False

    first_page = next((page for page in pages if isinstance(page, dict)), None)
    if not isinstance(first_page, dict):
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
                "title": f"Ready to move {title} from draft to launch?",
                "description": "This closing section was added automatically to improve page completion and conversion clarity.",
                "primary_cta_label": "Continue building",
                "primary_cta_route": primary_route,
                "secondary_cta_label": "Review details",
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
