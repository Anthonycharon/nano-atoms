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
) -> str:
    scope_key = (scope or "full").strip().lower() or "full"
    hint = SCOPE_HINTS.get(scope_key, SCOPE_HINTS["full"])
    schema_summary = summarize_schema(last_schema_json)

    return (
        "You are improving an existing generated application.\n"
        f"Scoped iteration target: {scope_key}\n"
        f"Scope rule: {hint}\n"
        "Preserve unaffected areas unless the new request explicitly requires broader changes.\n"
        f"Current app summary:\n{schema_summary}\n\n"
        f"User change request:\n{user_prompt}"
    )


def summarize_schema(last_schema_json: str | None) -> str:
    if not last_schema_json:
        return "No previous schema is available."

    try:
        payload = json.loads(last_schema_json)
    except Exception:
        return "Previous schema exists but could not be parsed."

    if not isinstance(payload, dict):
        return "Previous schema exists but is not a valid object."

    pages = payload.get("pages")
    if not isinstance(pages, list) or not pages:
        return "Previous schema has no pages."

    lines = [
        f"Title: {payload.get('title') or 'Untitled App'}",
        f"App type: {payload.get('app_type') or 'unknown'}",
    ]

    for page in pages[:6]:
        if not isinstance(page, dict):
            continue
        components = page.get("components") if isinstance(page.get("components"), list) else []
        component_types = [
            str(component.get("type"))
            for component in components
            if isinstance(component, dict) and component.get("type")
        ]
        lines.append(
            "- "
            + " | ".join(
                [
                    f"Page: {page.get('name') or page.get('id') or 'Unnamed'}",
                    f"Route: {page.get('route') or '/'}",
                    f"Components: {', '.join(component_types[:10]) or 'none'}",
                ]
            )
        )

    return "\n".join(lines)
