"""Generate bespoke website code from product/design planning with schema as fallback only."""

from __future__ import annotations

import asyncio
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.utils import (
    build_app_context,
    build_content_language_instruction,
    extract_json,
    make_llm,
)
from app.core.config import settings


DEBUG_LOG_PATH = Path(__file__).resolve().parents[3] / ".codex-run" / "page-codegen-debug.jsonl"


STYLE_SYSTEM_PROMPT = """You are a creative frontend art director.
Return one JSON object only with this shape:
{
  "style_brief": "short summary of the visual direction",
  "global_css": "CSS string only. No <style> tag.",
  "enhancement_js": "optional plain browser JS string only. No <script> tag."
}

Rules:
- The site must feel custom, not like a repeated SaaS template.
- Respect the user's requested tone, color mood, and language.
- Treat the planning payload as strategy, not as a literal component tree to restyle.
- Write CSS that can style freeform semantic HTML sections, cards, lists, galleries, hero areas, editorial blocks, forms, product grids, and detail sections.
- Do not use external fonts, frameworks, or imports.
- Keep enhancement_js optional and lightweight. Only DOM-safe progressive enhancement. No imports.
- Never return markdown fences or commentary."""


PAGE_SYSTEM_PROMPT = """You are a senior web designer who writes expressive page markup.
Return raw HTML only. No JSON. No markdown fences. No commentary.

Rules:
- Return one complete <main>...</main> fragment for one page.
- Use varied compositions, visual rhythm, and richer content sections.
- Avoid generic boxed cards and uniform section stacks.
- Do not duplicate the same primary form, auth card, hero, or CTA block within a single page.
- If visual_assets are provided, use at least one relevant visual asset in the markup. Prefer hero images, section illustrations, or ambient background treatments.
- Prefer concise, high-signal markup over oversized decorative output.
- Inline <style> or lightweight <script> is allowed only when it materially improves the experience.
- Keep all user-facing copy in the required language.
- Navigation/CTA interactions must use data-route="/path".
- Forms should use data-form-id on the form element.

Nano UI Classes Available:
- Button: <button class="na-btn" data-route="/path">Label</button>
- Card: <div class="na-card">...</div>
- Input: <input class="na-input" />
- Form: <form class="na-form" data-form-id="f1">...</form>
- Table: <table class="na-table">...</table>
- Hero: <section class="na-section na-hero">...</section>
- Feature Grid: <div class="na-feature-grid na-cols-3">...</div>
- CTA: <section class="na-cta">...</section>
- Stats: <div class="na-stat-chip">...</div>
- Navbar: <nav class="na-navbar">...</nav>

Example:
<main>
  <section class="na-section na-hero">
    <h1 class="na-display">Title</h1>
    <div class="na-actions"><button class="na-btn" data-route="/cta">CTA</button></div>
  </section>
</main>
"""


PAGE_RETRY_SYSTEM_PROMPT = """You are a senior web designer.
Return raw HTML only. No JSON. No markdown fences. No commentary.

Rules:
- Return one complete <main>...</main> fragment for one page.
- Keep all visible copy in the required language.
- Use semantic HTML and varied section structure.
- Do not duplicate the same primary form, auth card, hero, or CTA block within a single page.
- If visual_assets are provided, use at least one relevant visual asset in the markup.
- Keep the HTML compact and implementation-ready.
- Inline <style> or lightweight <script> is allowed only when it materially improves the experience.
- CTA and navigation interactions must use data-route="/path".
- Forms must use data-form-id where relevant.

Nano UI Classes: na-btn, na-card, na-input, na-form, na-hero, na-feature-grid, na-cta, na-stat-chip
"""


def _safe_text(value: Any, limit: int = 180) -> str:
    return str(value or "").strip()[:limit]


def _append_debug_log(payload: dict[str, Any]) -> None:
    try:
        DEBUG_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "ts": datetime.now(timezone.utc).isoformat(),
            **payload,
        }
        with DEBUG_LOG_PATH.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:
        pass


def _normalize_route(value: Any) -> str:
    route = str(value or "").strip() or "/"
    return route if route.startswith("/") else f"/{route}"


def _trim_text_list(value: Any, limit: int, item_limit: int = 120) -> list[str]:
    if not isinstance(value, list):
        return []

    items: list[str] = []
    seen: set[str] = set()
    for raw in value:
        text = _safe_text(raw, item_limit)
        if not text or text in seen:
            continue
        seen.add(text)
        items.append(text)
        if len(items) >= limit:
            break
    return items


def _compact_prd_context(prd_json: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(prd_json, dict):
        return {}

    visual_preferences = (
        prd_json.get("visual_preferences")
        if isinstance(prd_json.get("visual_preferences"), dict)
        else {}
    )
    return {
        "app_title": _safe_text(prd_json.get("app_title"), 120),
        "pages": _trim_text_list(prd_json.get("pages"), 6, 60),
        "features": _trim_text_list(prd_json.get("features"), 8, 120),
        "user_flows": _trim_text_list(prd_json.get("user_flows"), 6, 140),
        "data_fields": _trim_text_list(prd_json.get("data_fields"), 12, 60),
        "visual_preferences": visual_preferences,
    }


def _compact_design_context(design_brief: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(design_brief, dict):
        return {}

    return {
        "experience_goal": _safe_text(design_brief.get("experience_goal"), 160),
        "visual_direction": _safe_text(design_brief.get("visual_direction"), 160),
        "theme_mode": _safe_text(design_brief.get("theme_mode"), 40),
        "color_story": _safe_text(design_brief.get("color_story"), 160),
        "layout_density": _safe_text(design_brief.get("layout_density"), 40),
        "tone_keywords": _trim_text_list(design_brief.get("tone_keywords"), 8, 40),
        "style_constraints": _trim_text_list(design_brief.get("style_constraints"), 8, 120),
        "avoid_patterns": _trim_text_list(design_brief.get("avoid_patterns"), 8, 120),
        "section_recommendations": _trim_text_list(design_brief.get("section_recommendations"), 8, 40),
        "quality_checklist": _trim_text_list(design_brief.get("quality_checklist"), 8, 120),
    }


def _summarize_component(node: dict[str, Any]) -> dict[str, Any]:
    props = node.get("props") if isinstance(node.get("props"), dict) else {}
    summary: dict[str, Any] = {"type": node.get("type")}
    for key in ("title", "text", "description", "label", "placeholder", "eyebrow"):
        if props.get(key):
            summary[key] = _safe_text(props.get(key), 140)
    if isinstance(props.get("items"), list):
        summary["items_count"] = len(props["items"])
    if isinstance(props.get("stats"), list):
        summary["stats_count"] = len(props["stats"])
    if isinstance(props.get("bullets"), list):
        summary["bullets"] = [_safe_text(item, 72) for item in props["bullets"][:5]]
    if props.get("image_src"):
        summary["image_src"] = _safe_text(props.get("image_src"), 240)
    return summary


def _page_outline(page: dict[str, Any], fallback_page: dict[str, Any] | None = None) -> dict[str, Any]:
    section_hints: list[dict[str, Any]] = []
    sections = page.get("key_sections") if isinstance(page.get("key_sections"), list) else []
    for section in sections[:8]:
        if not isinstance(section, dict):
            continue
        hint: dict[str, Any] = {"goal": _safe_text(section.get("goal"), 200)}
        suggested_pattern = _safe_text(section.get("type"), 40)
        if suggested_pattern and suggested_pattern not in {"card", "text"}:
            hint["suggested_pattern"] = suggested_pattern
        if hint["goal"] or hint.get("suggested_pattern"):
            section_hints.append(hint)

    if not section_hints and isinstance(fallback_page, dict):
        components = fallback_page.get("components") if isinstance(fallback_page.get("components"), list) else []
        for node in components[:8]:
            if not isinstance(node, dict):
                continue
            component_summary = _summarize_component(node)
            goal = (
                component_summary.get("title")
                or component_summary.get("description")
                or component_summary.get("text")
                or component_summary.get("label")
                or component_summary.get("placeholder")
                or f"{component_summary.get('type') or 'section'} area"
            )
            hint = {"goal": _safe_text(goal, 200)}
            suggested_pattern = _safe_text(component_summary.get("type"), 40)
            if suggested_pattern and suggested_pattern not in {"card", "text"}:
                hint["suggested_pattern"] = suggested_pattern
            section_hints.append(hint)

    return {
        "id": page.get("id") or (fallback_page or {}).get("id"),
        "name": page.get("name") or (fallback_page or {}).get("name"),
        "route": _normalize_route(page.get("route") or (fallback_page or {}).get("route")),
        "purpose": _safe_text(page.get("purpose") or (fallback_page or {}).get("purpose"), 220),
        "layout_direction": _safe_text(page.get("layout_archetype") or (fallback_page or {}).get("layout_archetype"), 40),
        "section_hints": section_hints,
    }


def _top_level_navigation(app_schema: dict[str, Any], site_plan: dict[str, Any] | None = None) -> list[dict[str, str]]:
    navigation_source = (
        site_plan.get("navigation")
        if isinstance(site_plan, dict) and isinstance(site_plan.get("navigation"), list)
        else app_schema.get("navigation")
    )
    navigation = navigation_source if isinstance(navigation_source, list) else []
    items: list[dict[str, str]] = []
    for item in navigation:
        if not isinstance(item, dict):
            continue
        route = _normalize_route(item.get("route"))
        items.append(
            {
                "label": _safe_text(item.get("label") or item.get("text") or "Link", 40),
                "route": route,
            }
        )
    return items


def _ordered_site_pages(app_schema: dict[str, Any], site_plan: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    page_source = (
        site_plan.get("pages")
        if isinstance(site_plan, dict) and isinstance(site_plan.get("pages"), list)
        else app_schema.get("pages")
    )
    pages = page_source if isinstance(page_source, list) else []
    normalized_pages = [page for page in pages if isinstance(page, dict)]

    def sort_key(page: dict[str, Any]) -> tuple[int, int, str]:
        route = _normalize_route(page.get("route"))
        return (
            0 if route == "/" else 1,
            route.count("/"),
            route,
        )

    return sorted(normalized_pages, key=sort_key)


def _safe_media_url(value: Any) -> str | None:
    candidate = str(value or "").strip()
    if not candidate:
        return None
    if candidate.startswith("data:"):
        return None
    if len(candidate) > 512:
        return None
    return candidate


def _collect_visual_asset_hints(app_schema: dict[str, Any]) -> list[dict[str, Any]]:
    assets: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str, str]] = set()
    src_keys = {"src", "image_src", "poster_src", "logo_src", "hero_image_src"}

    generated_assets = (
        app_schema.get("generated_visual_assets")
        if isinstance(app_schema.get("generated_visual_assets"), list)
        else []
    )
    for asset in generated_assets:
        if not isinstance(asset, dict):
            continue
        safe_url = _safe_media_url(asset.get("url"))
        label = _safe_text(asset.get("label") or asset.get("page_name") or asset.get("role") or "visual", 96)
        signature = (
            str(asset.get("route") or "/"),
            str(asset.get("role") or "generated"),
            str(safe_url or ""),
            label,
        )
        if signature in seen:
            continue
        seen.add(signature)
        entry = {
            "route": str(asset.get("route") or "/"),
            "component": str(asset.get("role") or "generated_visual"),
            "role": str(asset.get("role") or "visual"),
            "label": label,
            "source_kind": str(asset.get("source") or "generated"),
        }
        if safe_url:
            entry["url"] = safe_url
        assets.append(entry)

    reference_assets = (
        app_schema.get("reference_assets")
        if isinstance(app_schema.get("reference_assets"), list)
        else []
    )
    for asset in reference_assets:
        if not isinstance(asset, dict):
            continue
        safe_url = _safe_media_url(asset.get("url"))
        if not safe_url:
            continue
        label = _safe_text(asset.get("name") or asset.get("kind") or "reference visual", 96)
        signature = ("/", "reference_asset", safe_url, label)
        if signature in seen:
            continue
        seen.add(signature)
        assets.append(
            {
                "route": "/",
                "component": "reference_asset",
                "role": "reference_visual",
                "label": label,
                "url": safe_url,
                "source_kind": "uploaded",
            }
        )

    pages = app_schema.get("pages") if isinstance(app_schema.get("pages"), list) else []

    def visit(node: Any, current_route: str = "/", component_type: str = "") -> None:
        if isinstance(node, dict):
            next_component_type = str(node.get("type") or component_type or "").strip()
            props = node.get("props") if isinstance(node.get("props"), dict) else {}
            for key, value in props.items():
                if key not in src_keys or not isinstance(value, str):
                    continue
                raw_value = value.strip()
                safe_url = _safe_media_url(raw_value)
                asset = {
                    "route": current_route,
                    "component": next_component_type or "section",
                    "role": key,
                    "label": _safe_text(
                        props.get("alt")
                        or props.get("image_alt")
                        or props.get("title")
                        or props.get("label")
                        or props.get("eyebrow")
                        or next_component_type
                        or "visual",
                        96,
                    ),
                    "source_kind": "embedded" if raw_value.startswith("data:") else "url",
                }
                if safe_url:
                    asset["url"] = safe_url
                signature = (
                    asset["route"],
                    asset["component"],
                    asset["role"],
                    str(asset.get("url") or asset.get("label") or ""),
                )
                if signature in seen:
                    continue
                seen.add(signature)
                assets.append(asset)
            for key, value in node.items():
                if isinstance(value, (dict, list)):
                    visit(value, current_route=current_route, component_type=next_component_type)
        elif isinstance(node, list):
            for item in node:
                visit(item, current_route=current_route, component_type=component_type)

    if pages:
        for page in pages:
            if not isinstance(page, dict):
                continue
            visit(page, current_route=_normalize_route(page.get("route")))
    else:
        visit(app_schema)

    return assets[:12]


def _extract_html_fragment(text: str) -> str | None:
    raw = str(text or "").strip()
    if not raw:
        return None

    for pattern in (
        r"```html\s*([\s\S]*?)```",
        r"```htm\s*([\s\S]*?)```",
        r"```xml\s*([\s\S]*?)```",
        r"```\s*([\s\S]*?</main>)\s*```",
        r"```\s*([\s\S]*?)```",
    ):
        match = re.search(pattern, raw, re.IGNORECASE)
        if match:
            raw = match.group(1).strip()
            break

    main_match = re.search(r"(<main[\s\S]*?</main>)", raw, re.IGNORECASE)
    if main_match:
        return main_match.group(1).strip()

    body_match = re.search(r"<body[^>]*>([\s\S]*?)</body>", raw, re.IGNORECASE)
    if body_match:
        body_fragment = body_match.group(1).strip()
        nested_main = re.search(r"(<main[\s\S]*?</main>)", body_fragment, re.IGNORECASE)
        if nested_main:
            return nested_main.group(1).strip()
        if body_fragment:
            return f'<main class="na-page na-freeform-shell">{body_fragment}</main>'

    if re.search(r"<(section|div|article|header|nav|aside|footer|form|ul|ol|li|figure|blockquote|h1|h2)\b", raw, re.IGNORECASE):
        return f'<main class="na-page na-freeform-shell">{raw}</main>'

    return None


def _extract_json_string_field(raw: str, field_name: str) -> str | None:
    field_match = re.search(rf'"{re.escape(field_name)}"\s*:\s*"', raw)
    if not field_match:
        return None

    start = field_match.end() - 1
    try:
        value, _ = json.JSONDecoder().raw_decode(raw[start:])
    except Exception:
        return None
    return value if isinstance(value, str) else None


def _extract_escaped_body_html_field(raw: str) -> str | None:
    match = re.search(r'"body_html"\s*:\s*"(<main[\s\S]*?<\\\/main>)"', raw)
    if not match:
        return None
    literal = f'"{match.group(1)}"'
    try:
        value = json.loads(literal)
    except Exception:
        return None
    return value if isinstance(value, str) else None


def _extract_escaped_main_fragment(raw: str) -> str | None:
    escaped_end = raw.rfind("<\\/main>")
    if escaped_end != -1:
        start = raw.rfind("<main", 0, escaped_end)
        if start == -1 or escaped_end <= start:
            return None
        fragment = raw[start : escaped_end + len("<\\/main>")]
    else:
        start = raw.find("<main")
        end = raw.rfind("</main>")
        if start == -1 or end == -1 or end <= start:
            return None
        fragment = raw[start : end + len("</main>")]
    return (
        fragment.replace('\\"', '"')
        .replace("\\n", "\n")
        .replace("\\t", "\t")
        .replace("\\/", "/")
        .strip()
    )


def _normalize_body_html(raw_text: str) -> str | None:
    raw = str(raw_text or "").strip()
    if not raw:
        return None

    if "\"body_html\"" in raw or raw.lstrip().startswith("{") or raw.lstrip().startswith("```json"):
        escaped_body = _extract_escaped_body_html_field(raw)
        if escaped_body and escaped_body != raw:
            return _normalize_body_html(escaped_body)
        try:
            nested = extract_json(raw)
        except Exception:
            nested = None
        if isinstance(nested, dict):
            nested_body = str(nested.get("body_html") or "").strip()
            if nested_body and nested_body != raw:
                return _normalize_body_html(nested_body)
        escaped_fragment = _extract_escaped_main_fragment(raw)
        if escaped_fragment and escaped_fragment != raw:
            return _normalize_body_html(escaped_fragment)
        literal_body = _extract_json_string_field(raw, "body_html")
        if literal_body and literal_body != raw and "</" in literal_body:
            return _normalize_body_html(literal_body)

    html_fragment = _extract_html_fragment(raw)
    if html_fragment:
        return html_fragment

    if "<main" in raw:
        return raw
    return None


def _extract_page_title(body_html: str, fallback: str) -> str:
    heading_match = re.search(r"<h1[^>]*>(.*?)</h1>", body_html, re.IGNORECASE | re.DOTALL)
    if not heading_match:
        return fallback
    heading = re.sub(r"<[^>]+>", "", heading_match.group(1)).strip()
    return heading or fallback


def _parse_page_payload(raw_text: str, fallback_title: str) -> dict[str, Any] | None:
    try:
        payload = extract_json(raw_text)
        if isinstance(payload, dict):
            body_html = _normalize_body_html(str(payload.get("body_html") or "").strip())
            if body_html:
                title = str(payload.get("title") or "").strip() or _extract_page_title(body_html, fallback_title)
                return {
                    "title": title,
                    "body_html": body_html,
                }
    except Exception:
        pass

    body_html = _normalize_body_html(raw_text)
    if not body_html:
        return None
    return {
        "title": _extract_page_title(body_html, fallback_title),
        "body_html": body_html,
    }


async def _generate_style_pack(
    *,
    prompt: str,
    app_type: str,
    app_schema: dict[str, Any],
    site_plan: dict[str, Any] | None = None,
    prd_json: dict[str, Any] | None = None,
    design_brief: dict[str, Any] | None = None,
    ui_theme: dict[str, Any] | None = None,
) -> dict[str, Any]:
    llm = make_llm(temperature=0.6)
    language = str(
        (site_plan or {}).get("content_language")
        or (design_brief or {}).get("content_language")
        or app_schema.get("content_language")
        or (app_schema.get("design_brief") or {}).get("content_language")
        or "en-US"
    )
    site_context = {
        "title": (site_plan or {}).get("title") or app_schema.get("title"),
        "app_type": (site_plan or {}).get("app_type") or app_schema.get("app_type"),
        "navigation": _top_level_navigation(app_schema, site_plan),
        "site_map": [
            {
                "name": _safe_text(page.get("name"), 60),
                "route": _normalize_route(page.get("route")),
                "purpose": _safe_text(page.get("purpose"), 140),
            }
            for page in _ordered_site_pages(app_schema, site_plan)[:8]
        ],
        "prd": _compact_prd_context(prd_json),
        "design_brief": _compact_design_context(design_brief or app_schema.get("design_brief")),
        "ui_theme": ui_theme or app_schema.get("ui_theme") or {},
        "available_visual_assets": _collect_visual_asset_hints(app_schema),
    }
    response = await llm.ainvoke(
        [
            SystemMessage(content=STYLE_SYSTEM_PROMPT),
            HumanMessage(
                content=(
                    f"{build_app_context(app_type)}\n"
                    f"{build_content_language_instruction(language)}\n\n"
                    f"User prompt:\n{prompt}\n\n"
                    "Planning context:\n"
                    f"{json.dumps(site_context, ensure_ascii=False)}"
                )
            ),
        ]
    )
    raw_response = str(response.content)
    try:
        payload = extract_json(raw_response)
    except Exception as exc:
        _append_debug_log(
            {
                "kind": "style_pack",
                "status": "parse_error",
                "error": str(exc),
                "response": raw_response,
                "context": {
                    "title": site_context.get("title"),
                    "app_type": site_context.get("app_type"),
                    "site_map_count": len(site_context.get("site_map") or []),
                },
            }
        )
        raise
    _append_debug_log(
        {
            "kind": "style_pack",
            "status": "ok" if isinstance(payload, dict) else "invalid_payload",
            "response": raw_response,
            "parsed_keys": sorted(payload.keys()) if isinstance(payload, dict) else [],
            "context": {
                "title": site_context.get("title"),
                "app_type": site_context.get("app_type"),
                "site_map_count": len(site_context.get("site_map") or []),
            },
        }
    )
    if not isinstance(payload, dict):
        raise ValueError("Site codegen style pack must be a JSON object")
    return payload


async def _generate_page_markup(
    *,
    prompt: str,
    app_type: str,
    app_schema: dict[str, Any],
    page: dict[str, Any],
    style_brief: str,
    navigation: list[dict[str, str]],
    llm,
    site_plan: dict[str, Any] | None = None,
    prd_json: dict[str, Any] | None = None,
    design_brief: dict[str, Any] | None = None,
    ui_theme: dict[str, Any] | None = None,
    fallback_page: dict[str, Any] | None = None,
    minimal_context: bool = False,
) -> dict[str, Any] | None:
    language = str(
        (site_plan or {}).get("content_language")
        or (design_brief or {}).get("content_language")
        or app_schema.get("content_language")
        or (app_schema.get("design_brief") or {}).get("content_language")
        or "en-US"
    )
    fallback_title = str(page.get("name") or page.get("route") or (fallback_page or {}).get("name") or "Page")
    page_outline = _page_outline(page, fallback_page)
    route = _normalize_route(page.get("route"))
    all_visual_assets = _collect_visual_asset_hints(app_schema)
    visual_assets = [
        asset
        for asset in all_visual_assets
        if str(asset.get("route") or "").strip() in {"", "/", route}
    ][:6]
    page_context = {
        "site_title": (site_plan or {}).get("title") or app_schema.get("title"),
        "page_title": fallback_title,
        "page_route": route,
        "page_strategy": page_outline,
        "navigation": navigation,
        "style_brief": style_brief,
        "ui_theme": ui_theme or app_schema.get("ui_theme") or {},
        "design_brief": _compact_design_context(design_brief or app_schema.get("design_brief")),
        "visual_assets": visual_assets,
    }
    if not minimal_context:
        page_context["prd"] = _compact_prd_context(prd_json)

    _append_debug_log(
        {
            "kind": "page_codegen",
            "attempt": "primary" if not minimal_context else "retry",
            "route": route,
            "minimal_context": minimal_context,
            "status": "request_started",
            "page_strategy": page_outline,
            "context_keys": sorted(page_context.keys()),
        }
    )
    response = await llm.ainvoke(
        [
            SystemMessage(content=PAGE_RETRY_SYSTEM_PROMPT if minimal_context else PAGE_SYSTEM_PROMPT),
            HumanMessage(
                content=(
                    f"{build_app_context(app_type)}\n"
                    f"{build_content_language_instruction(language)}\n\n"
                    f"User prompt:\n{prompt}\n\n"
                    "Page generation context:\n"
                    f"{json.dumps(page_context, ensure_ascii=False)}"
                )
            ),
        ]
    )
    raw_response = str(response.content)
    parsed_payload = _parse_page_payload(raw_response, fallback_title)
    if not parsed_payload:
        _append_debug_log(
            {
                "kind": "page_codegen",
                "attempt": "primary" if not minimal_context else "retry",
                "route": route,
                "minimal_context": minimal_context,
                "status": "parse_failed",
                "response": raw_response,
                "page_strategy": page_outline,
            }
        )
        return None

    body_html = str(parsed_payload.get("body_html") or "").strip()
    parsed_title = str(parsed_payload.get("title") or "").strip() or _extract_page_title(body_html, fallback_title)
    _append_debug_log(
        {
            "kind": "page_codegen",
            "attempt": "primary" if not minimal_context else "retry",
            "route": route,
            "minimal_context": minimal_context,
            "status": "ok",
            "parsed_title": parsed_title,
            "body_length": len(body_html),
            "page_strategy": page_outline,
        }
    )
    return {
        "route": route,
        "title": parsed_title,
        "body_html": body_html,
    }


async def generate_freeform_site_pack(
    *,
    prompt: str,
    app_type: str,
    app_schema: dict[str, Any],
    code_bundle: dict[str, Any],
    prd_json: dict[str, Any] | None = None,
    design_brief: dict[str, Any] | None = None,
    site_plan: dict[str, Any] | None = None,
    ui_theme: dict[str, Any] | None = None,
    page_limit: int | None = None,
    page_routes: list[str] | None = None,
    style_pack: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    del code_bundle
    pages = _ordered_site_pages(app_schema, site_plan)
    if page_routes:
        wanted = {_normalize_route(route) for route in page_routes if str(route).strip()}
        pages = [page for page in pages if _normalize_route(page.get("route")) in wanted]
    if page_limit is not None:
        pages = pages[: max(0, page_limit)]
    if not pages:
        return None

    schema_pages_source = app_schema.get("pages") if isinstance(app_schema.get("pages"), list) else []
    schema_pages_by_route = {
        _normalize_route(page.get("route")): page
        for page in schema_pages_source
        if isinstance(page, dict)
    }

    if not isinstance(style_pack, dict):
        try:
            style_pack = await _generate_style_pack(
                prompt=prompt,
                app_type=app_type,
                app_schema=app_schema,
                site_plan=site_plan,
                prd_json=prd_json,
                design_brief=design_brief,
                ui_theme=ui_theme,
            )
        except Exception:
            style_pack = {}

    style_brief = str(style_pack.get("style_brief") or "").strip()
    global_css = str(style_pack.get("global_css") or "").strip()
    enhancement_js = str(
        style_pack.get("enhancement_js") or style_pack.get("runtime_js") or ""
    ).strip()
    navigation = _top_level_navigation(app_schema, site_plan)
    semaphore = asyncio.Semaphore(max(1, settings.SITE_CODEGEN_PAGE_CONCURRENCY))

    async def render_one(page: dict[str, Any]) -> dict[str, Any] | None:
        fallback_page = schema_pages_by_route.get(_normalize_route(page.get("route")))
        async with semaphore:
            try:
                return await asyncio.wait_for(
                    _generate_page_markup(
                        prompt=prompt,
                        app_type=app_type,
                        app_schema=app_schema,
                        page=page,
                        style_brief=style_brief,
                        navigation=navigation,
                        llm=make_llm(temperature=0.4),
                        site_plan=site_plan,
                        prd_json=prd_json,
                        design_brief=design_brief,
                        ui_theme=ui_theme,
                        fallback_page=fallback_page,
                    ),
                    timeout=settings.SITE_CODEGEN_INITIAL_TIMEOUT_SECONDS,
                )
            except asyncio.TimeoutError:
                _append_debug_log(
                    {
                        "kind": "page_codegen",
                        "attempt": "primary",
                        "route": _normalize_route(page.get("route")),
                        "minimal_context": False,
                        "status": "timeout",
                        "timeout_seconds": settings.SITE_CODEGEN_INITIAL_TIMEOUT_SECONDS,
                    }
                )
                return None
            except Exception as exc:
                _append_debug_log(
                    {
                        "kind": "page_codegen",
                        "attempt": "primary",
                        "route": _normalize_route(page.get("route")),
                        "minimal_context": False,
                        "status": "exception",
                        "error": str(exc),
                    }
                )
                return None

    generated_pages = [item for item in await asyncio.gather(*(render_one(page) for page in pages)) if item]
    generated_routes = {
        _normalize_route(item.get("route"))
        for item in generated_pages
        if isinstance(item, dict)
    }
    _append_debug_log(
        {
            "kind": "page_codegen_batch",
            "status": "primary_pass_done",
            "attempted_routes": [_normalize_route(page.get("route")) for page in pages],
            "generated_routes": sorted(generated_routes),
            "style_brief": style_brief,
        }
    )
    missing_pages = [page for page in pages if _normalize_route(page.get("route")) not in generated_routes]
    for page in missing_pages:
        try:
            result = await asyncio.wait_for(
                _generate_page_markup(
                    prompt=prompt,
                    app_type=app_type,
                    app_schema=app_schema,
                    page=page,
                    style_brief=style_brief,
                    navigation=navigation,
                    llm=make_llm(temperature=0.3),
                    site_plan=site_plan,
                    prd_json=prd_json,
                    design_brief=design_brief,
                    ui_theme=ui_theme,
                    fallback_page=schema_pages_by_route.get(_normalize_route(page.get("route"))),
                    minimal_context=True,
                ),
                timeout=settings.SITE_CODEGEN_RETRY_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError:
            _append_debug_log(
                {
                    "kind": "page_codegen",
                    "attempt": "retry",
                    "route": _normalize_route(page.get("route")),
                    "minimal_context": True,
                    "status": "timeout",
                    "timeout_seconds": settings.SITE_CODEGEN_RETRY_TIMEOUT_SECONDS,
                }
            )
            result = None
        except Exception as exc:
            _append_debug_log(
                {
                    "kind": "page_codegen",
                    "attempt": "retry",
                    "route": _normalize_route(page.get("route")),
                    "minimal_context": True,
                    "status": "exception",
                    "error": str(exc),
                }
            )
            result = None
        if result:
            generated_pages.append(result)

    if not generated_pages:
        _append_debug_log(
            {
                "kind": "page_codegen_batch",
                "status": "no_pages_generated",
                "attempted_routes": [_normalize_route(page.get("route")) for page in pages],
                "style_brief": style_brief,
            }
        )
        return None

    _append_debug_log(
        {
            "kind": "page_codegen_batch",
            "status": "ok",
            "attempted_routes": [_normalize_route(page.get("route")) for page in pages],
            "generated_routes": [_normalize_route(page.get("route")) for page in generated_pages if isinstance(page, dict)],
            "style_brief": style_brief,
        }
    )
    return {
        "style_brief": style_brief,
        "global_css": global_css,
        "runtime_js": enhancement_js,
        "attempted_pages": len(pages),
        "generated_pages": len(generated_pages),
        "pages": generated_pages,
    }


def merge_freeform_site_packs(
    base_pack: dict[str, Any] | None,
    extra_pack: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not isinstance(base_pack, dict) and not isinstance(extra_pack, dict):
        return None
    if not isinstance(base_pack, dict):
        return extra_pack
    if not isinstance(extra_pack, dict):
        return base_pack

    merged_pages: dict[str, dict[str, Any]] = {}
    for item in base_pack.get("pages", []) if isinstance(base_pack.get("pages"), list) else []:
        if isinstance(item, dict):
            route = str(item.get("route") or "").strip()
            if route:
                merged_pages[route] = item
    for item in extra_pack.get("pages", []) if isinstance(extra_pack.get("pages"), list) else []:
        if isinstance(item, dict):
            route = str(item.get("route") or "").strip()
            if route:
                merged_pages[route] = item

    return {
        "style_brief": str(
            extra_pack.get("style_brief")
            or base_pack.get("style_brief")
            or ""
        ).strip(),
        "global_css": str(
            extra_pack.get("global_css")
            or base_pack.get("global_css")
            or ""
        ).strip(),
        "runtime_js": str(
            extra_pack.get("runtime_js")
            or base_pack.get("runtime_js")
            or ""
        ).strip(),
        "attempted_pages": int(base_pack.get("attempted_pages") or 0)
        + int(extra_pack.get("attempted_pages") or 0),
        "generated_pages": len(merged_pages),
        "pages": list(merged_pages.values()),
    }
