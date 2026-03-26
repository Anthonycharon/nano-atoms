"""Best-effort freeform website code generation on top of schema planning."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.utils import (
    build_app_context,
    build_content_language_instruction,
    extract_json,
    make_llm,
)
from app.core.config import settings


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
- Write CSS that can style freeform semantic HTML sections, cards, lists, galleries, hero areas, editorial blocks, forms, product grids, and detail sections.
- Do not use external fonts, frameworks, or imports.
- Keep enhancement_js optional and lightweight. Only DOM-safe progressive enhancement. No imports.
- Never return markdown fences or commentary."""


PAGE_SYSTEM_PROMPT = """You are a senior web designer who writes expressive page markup.
Return one JSON object only:
{
  "title": "page title",
  "body_html": "<main>...</main>"
}

Rules:
- body_html must be a complete semantic body fragment for one page only.
- Do not include <html>, <head>, <body>, <script>, or <style>.
- Use varied compositions, asymmetry, visual rhythm, editorial sections, product showcases, comparison blocks, testimonials, FAQ, filters, category rails, and richer content where relevant.
- Avoid turning every request into generic boxed cards and uniform section stacks.
- Keep all user-facing copy in the required language.
- Navigation links or CTA jumps must use data-route=\"/path\".
- Forms should use data-form-id on the form element when relevant.
- Use only safe semantic HTML and class names.
- Reuse available image URLs when present. If none exist, create visual sections that still look complete without external images.
- Never mention JSON, schema, or implementation details in the page copy."""


def _safe_text(value: Any, limit: int = 180) -> str:
    return str(value or "").strip()[:limit]


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


def _page_outline(page: dict[str, Any]) -> dict[str, Any]:
    components = page.get("components") if isinstance(page.get("components"), list) else []
    return {
        "id": page.get("id"),
        "name": page.get("name"),
        "route": page.get("route"),
        "layout_archetype": page.get("layout_archetype"),
        "components": [
            _summarize_component(node)
            for node in components
            if isinstance(node, dict)
        ],
    }


def _top_level_navigation(app_schema: dict[str, Any]) -> list[dict[str, str]]:
    navigation = app_schema.get("navigation") if isinstance(app_schema.get("navigation"), list) else []
    items: list[dict[str, str]] = []
    for item in navigation:
        if not isinstance(item, dict):
            continue
        route = str(item.get("route") or "").strip() or "/"
        items.append(
            {
                "label": _safe_text(item.get("label") or item.get("text") or "Link", 40),
                "route": route if route.startswith("/") else f"/{route}",
            }
        )
    return items


async def _generate_style_pack(
    *,
    prompt: str,
    app_type: str,
    app_schema: dict[str, Any],
) -> dict[str, Any]:
    llm = make_llm(temperature=0.6)
    language = str(app_schema.get("content_language") or (app_schema.get("design_brief") or {}).get("content_language") or "en-US")
    response = await llm.ainvoke(
        [
            SystemMessage(content=STYLE_SYSTEM_PROMPT),
            HumanMessage(
                content=(
                    f"{build_app_context(app_type)}\n"
                    f"{build_content_language_instruction(language)}\n\n"
                    f"User prompt:\n{prompt}\n\n"
                    "App context:\n"
                    f"{json.dumps({'title': app_schema.get('title'), 'app_type': app_schema.get('app_type'), 'design_brief': app_schema.get('design_brief') or {}, 'ui_theme': app_schema.get('ui_theme') or {}, 'navigation': _top_level_navigation(app_schema)}, ensure_ascii=False)}"
                )
            ),
        ]
    )
    payload = extract_json(response.content)
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
) -> dict[str, Any] | None:
    language = str(app_schema.get("content_language") or (app_schema.get("design_brief") or {}).get("content_language") or "en-US")
    response = await llm.ainvoke(
        [
            SystemMessage(content=PAGE_SYSTEM_PROMPT),
            HumanMessage(
                content=(
                    f"{build_app_context(app_type)}\n"
                    f"{build_content_language_instruction(language)}\n\n"
                    f"User prompt:\n{prompt}\n\n"
                    f"Style brief:\n{style_brief}\n\n"
                    "Global site context:\n"
                    f"{json.dumps({'site_title': app_schema.get('title'), 'navigation': navigation, 'ui_theme': app_schema.get('ui_theme') or {}}, ensure_ascii=False)}\n\n"
                    "Page outline:\n"
                    f"{json.dumps(_page_outline(page), ensure_ascii=False)}"
                )
            ),
        ]
    )
    payload = extract_json(response.content)
    if not isinstance(payload, dict):
        return None
    body_html = str(payload.get("body_html") or "").strip()
    if not body_html:
        return None
    return {
        "route": page.get("route"),
        "title": str(payload.get("title") or page.get("name") or ""),
        "body_html": body_html,
    }


async def generate_freeform_site_pack(
    *,
    prompt: str,
    app_type: str,
    app_schema: dict[str, Any],
    code_bundle: dict[str, Any],
) -> dict[str, Any] | None:
    del code_bundle
    pages = app_schema.get("pages") if isinstance(app_schema.get("pages"), list) else []
    pages = [page for page in pages if isinstance(page, dict)]
    if not pages:
        return None

    try:
        style_pack = await _generate_style_pack(
            prompt=prompt,
            app_type=app_type,
            app_schema=app_schema,
        )
    except Exception:
        style_pack = {}

    style_brief = str(style_pack.get("style_brief") or "").strip()
    global_css = str(style_pack.get("global_css") or "").strip()
    enhancement_js = str(style_pack.get("enhancement_js") or "").strip()
    navigation = _top_level_navigation(app_schema)
    llm = make_llm(temperature=0.45)
    semaphore = asyncio.Semaphore(max(1, min(settings.ARCHITECT_PAGE_CONCURRENCY, 3)))

    async def render_one(page: dict[str, Any]) -> dict[str, Any] | None:
        async with semaphore:
            try:
                return await _generate_page_markup(
                    prompt=prompt,
                    app_type=app_type,
                    app_schema=app_schema,
                    page=page,
                    style_brief=style_brief,
                    navigation=navigation,
                    llm=llm,
                )
            except Exception:
                return None

    generated_pages = [item for item in await asyncio.gather(*(render_one(page) for page in pages)) if item]
    if not generated_pages and not global_css and not enhancement_js:
        return None

    return {
        "style_brief": style_brief,
        "global_css": global_css,
        "runtime_js": enhancement_js,
        "pages": generated_pages,
    }
