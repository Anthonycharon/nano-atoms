"""Build scoped iteration prompts from an existing generated schema."""

from __future__ import annotations

import json
from typing import Any


SCOPE_HINTS = {
    "full": "Rework the overall app as needed, but preserve the best parts of the current version.",
    "hero": "Only change the homepage hero area and immediate top-of-page messaging. Keep the rest of the app stable.",
    "landing": "Only change the homepage and marketing sections. Keep data flows and secondary pages stable.",
    "auth": "Only change the authentication experience, including login, register, and trust-building copy.",
    "data": "Only change dashboards, tables, CRUD flows, and data-heavy pages. Keep branding and homepage stable.",
    "style": "Only change the visual language, spacing, hierarchy, and component polish. Keep information architecture stable.",
}


def build_iteration_prompt(
    user_prompt: str,
    scope: str | None,
    last_schema_json: str | None,
    last_code_json: str | None,
) -> str:
    scope_key = (scope or "full").strip().lower() or "full"
    hint = SCOPE_HINTS.get(scope_key, SCOPE_HINTS["full"])
    context_summary = summarize_generation_context(last_schema_json, last_code_json)

    return (
        "You are improving an existing generated application.\n"
        f"Scoped iteration target: {scope_key}\n"
        f"Scope rule: {hint}\n"
        "Preserve unaffected areas unless the new request explicitly requires broader changes.\n"
        f"Current app summary:\n{context_summary}\n\n"
        f"User change request:\n{user_prompt}"
    )


def summarize_generation_context(
    last_schema_json: str | None,
    last_code_json: str | None,
) -> str:
    metadata_summary = summarize_generation_metadata(last_schema_json)
    artifact_summary = summarize_generated_artifact(last_code_json)
    return f"{metadata_summary}\n{artifact_summary}".strip()


def summarize_generation_metadata(last_schema_json: str | None) -> str:
    if not last_schema_json:
        return "No previous generation metadata is available."

    try:
        payload = json.loads(last_schema_json)
    except Exception:
        return "Previous generation metadata exists but could not be parsed."

    if not isinstance(payload, dict):
        return "Previous generation metadata exists but is not a valid object."

    site_plan = payload.get("site_plan") if isinstance(payload.get("site_plan"), dict) else {}
    pages = site_plan.get("pages") if isinstance(site_plan.get("pages"), list) else []
    lines = [
        f"Title: {payload.get('title') or 'Untitled App'}",
        f"App type: {payload.get('app_type') or 'unknown'}",
        f"Language: {payload.get('content_language') or 'unknown'}",
        f"Layout direction: {payload.get('layout_archetype') or 'unspecified'}",
    ]

    if not pages:
        return "\n".join(lines + ["No previous app structure summary is available."])

    for page in pages[:6]:
        if not isinstance(page, dict):
            continue
        section_hints = page.get("key_sections") if isinstance(page.get("key_sections"), list) else []
        section_types = [
            str(section.get("type"))
            for section in section_hints
            if isinstance(section, dict) and section.get("type")
        ]
        lines.append(
            "- "
            + " | ".join(
                [
                    f"Page: {page.get('name') or page.get('id') or 'Unnamed'}",
                    f"Route: {page.get('route') or '/'}",
                    f"Sections: {', '.join(section_types[:8]) or 'unspecified'}",
                ]
            )
        )

    return "\n".join(lines)


def summarize_generated_artifact(last_code_json: str | None) -> str:
    if not last_code_json:
        return "No previous generated artifact is available."

    try:
        payload = json.loads(last_code_json)
    except Exception:
        return "Previous generated artifact exists but could not be parsed."

    if not isinstance(payload, dict):
        return "Previous generated artifact exists but is not a valid object."

    files = payload.get("files") if isinstance(payload.get("files"), list) else []
    html_files = [
        str(item.get("path"))
        for item in files
        if isinstance(item, dict) and str(item.get("path") or "").endswith(".html")
    ]

    lines = [
        f"Artifact format: {payload.get('format') or 'unknown'}",
        f"Entry file: {payload.get('entry') or 'unknown'}",
        f"Generated file count: {len(files)}",
    ]

    if html_files:
        lines.append(f"Primary views: {', '.join(html_files[:8])}")
    else:
        lines.append("Primary views: none recorded")

    quality_report = payload.get("quality_report")
    if isinstance(quality_report, dict) and quality_report.get("summary"):
        lines.append(f"Last quality summary: {quality_report.get('summary')}")

    return "\n".join(lines)
