"""Architect agent: plan pages first, then compose each page schema separately."""

from __future__ import annotations

import asyncio
import json
import re
from copy import deepcopy
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.core.config import settings

from .utils import build_app_context, build_content_language_instruction, extract_json, make_llm, notify_agent


PAGE_PLAN_SYSTEM_PROMPT = """You are a senior application architect.
Return one JSON object only, with no markdown or commentary.

Output format:
{
  "app_id": "unique_app_id",
  "title": "Application title",
  "app_type": "application shape such as dashboard, tool, admin, internal, landing, marketing, blog, ecommerce, auth",
  "content_language": "zh-CN | en-US | ja-JP | ko-KR",
  "layout_archetype": "marketing | editorial | dashboard | centered-auth | workspace | immersive",
  "navigation": [{"label": "Link label", "route": "/route"}],
  "data_models": [{"name": "ModelName", "fields": ["field names"]}],
  "pages": [
    {
      "id": "page_id",
      "name": "Page name",
      "route": "/route",
      "purpose": "what this page is responsible for",
      "layout_archetype": "marketing | editorial | dashboard | centered-auth | workspace | immersive",
      "key_sections": [
        {
          "id": "section_id",
          "type": "supported component type",
          "goal": "what this section should achieve"
        }
      ]
    }
  ]
}

Rules:
- Design the first usable release only.
- Return at most 5 pages unless the user explicitly asks for more.
- Prefer 4-8 strong sections per page, not exhaustive trees.
- Plan one coherent website or application shell, not a pile of disconnected screens.
- Keep the top-level navigation focused on primary pages and shared across the experience.
- Do not place dynamic detail routes like /item/:id in the main navigation unless the user explicitly asks for it.
- Keep all page names, navigation labels, headlines, descriptions, CTA labels, placeholders, and other user-facing copy in the requested content language.
- Use only supported component types:
  text, heading, image, button, input, select, table, card, form, modal, tag, navbar, stat-card,
  hero, feature-grid, stats-band, split-section, cta-band, auth-card.
- Only use centered-auth for true sign-in or sign-up pages.
- Blogs and reading products should lean editorial.
- Marketing and launch pages should lean marketing or immersive.
- Dashboards, admin, analytics, and CRM should lean dashboard.
- Tools, assistants, operators, and workflow apps should lean workspace.
"""


PAGE_COMPOSER_SYSTEM_PROMPT = """You are a senior application architect composing one page at a time.
Return one JSON object only, with no markdown or commentary.

Output format:
{
  "id": "page_id",
  "name": "Page name",
  "route": "/route",
  "layout_archetype": "marketing | editorial | dashboard | centered-auth | workspace | immersive",
  "components": [
    {
      "id": "component_id",
      "type": "component type",
      "props": {"key": "value"},
      "children": [],
      "actions": [],
      "style": {}
    }
  ]
}

Supported component types:
- Primitive: text, heading, image, button, input, select, table, card, form, modal, tag, navbar, stat-card
- Composite: hero, feature-grid, stats-band, split-section, cta-band, auth-card

Rules:
- Compose only this page, not the whole app.
- Keep 4-8 strong top-level components unless the page is truly simple.
- This page belongs to one coherent multi-page website or application.
- Preserve the shared title, shared navigation, and shared shell conventions from the global plan.
- If the app has shared navigation and this page is not a true auth page, include a navbar near the top.
- Keep every user-facing string in the requested content language.
- Make copy specific, believable, and product-like.
- Reuse the page plan's key_sections, but turn them into renderable components with realistic props.
- Use form/input/button combinations for application, intake, search, filtering, and contact flows when relevant.
- Use table/stat-card combinations for dashboard or operator pages when relevant.
- Do not invent unsupported component types.
- Return children, actions, and style on every component, even if they are empty.
"""


SUPPORTED_LAYOUTS = {
    "marketing",
    "editorial",
    "dashboard",
    "centered-auth",
    "workspace",
    "immersive",
}

SUPPORTED_COMPONENT_TYPES = {
    "text",
    "heading",
    "image",
    "button",
    "input",
    "select",
    "table",
    "card",
    "form",
    "modal",
    "tag",
    "navbar",
    "stat-card",
    "hero",
    "feature-grid",
    "stats-band",
    "split-section",
    "cta-band",
    "auth-card",
}


def _is_chinese_language(language: object) -> bool:
    return str(language or "").strip().lower() == "zh-cn"


def _localized_text(language: object, zh: str, en: str) -> str:
    return zh if _is_chinese_language(language) else en


def _slugify(value: str, fallback: str) -> str:
    text = re.sub(r"[^a-zA-Z0-9]+", "-", str(value or "").strip().lower())
    text = text.strip("-")
    return text or fallback


def _limit_unique_list(value: object, limit: int) -> list[Any]:
    if not isinstance(value, list):
        return []

    seen: set[str] = set()
    result: list[Any] = []
    for item in value:
        key = json.dumps(item, ensure_ascii=False, sort_keys=True) if isinstance(item, (dict, list)) else str(item)
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
        if len(result) >= limit:
            break
    return result


def _compact_prd_payload(prd_json: dict[str, Any]) -> dict[str, Any]:
    compacted = dict(prd_json)
    compacted["pages"] = _limit_unique_list(prd_json.get("pages"), 5)
    compacted["features"] = _limit_unique_list(prd_json.get("features"), 8)
    compacted["user_flows"] = _limit_unique_list(prd_json.get("user_flows"), 6)
    compacted["data_fields"] = _limit_unique_list(prd_json.get("data_fields"), 12)
    return compacted


def _normalize_layout(value: object, fallback: str = "workspace") -> str:
    text = str(value or "").strip().lower()
    return text if text in SUPPORTED_LAYOUTS else fallback


def _normalize_route(name: str, route: object, index: int) -> str:
    if isinstance(route, str) and route.strip():
        normalized = route.strip()
        return normalized if normalized.startswith("/") else f"/{normalized}"
    if index == 0:
        return "/"
    return f"/{_slugify(name, f'page-{index + 1}')}"


def _ensure_component(node: dict[str, Any], fallback_prefix: str, index: int) -> dict[str, Any]:
    component_type = str(node.get("type") or "card").strip()
    if component_type not in SUPPORTED_COMPONENT_TYPES:
        component_type = "card"

    props = node.get("props") if isinstance(node.get("props"), dict) else {}
    children = [
        _ensure_component(child, f"{fallback_prefix}-child", child_index)
        for child_index, child in enumerate(node.get("children", []) or [])
        if isinstance(child, dict)
    ]
    actions = node.get("actions") if isinstance(node.get("actions"), list) else []
    style = node.get("style") if isinstance(node.get("style"), dict) else {}

    return {
        "id": str(node.get("id") or f"{fallback_prefix}-{index + 1}"),
        "type": component_type,
        "props": props,
        "children": children,
        "actions": actions,
        "style": style,
    }


def _normalize_page(page: dict[str, Any], fallback: dict[str, Any], index: int) -> dict[str, Any]:
    components = [
        _ensure_component(component, str(page.get("id") or fallback.get("id") or "page"), component_index)
        for component_index, component in enumerate(page.get("components", []) or [])
        if isinstance(component, dict)
    ]

    if not components:
        return _build_fallback_page(fallback, fallback.get("_global", {}))

    return {
        "id": str(page.get("id") or fallback.get("id") or f"page-{index + 1}"),
        "name": str(page.get("name") or fallback.get("name") or f"Page {index + 1}"),
        "route": _normalize_route(
            str(page.get("name") or fallback.get("name") or f"Page {index + 1}"),
            page.get("route") or fallback.get("route"),
            index,
        ),
        "layout_archetype": _normalize_layout(
            page.get("layout_archetype") or fallback.get("layout_archetype"),
            _normalize_layout(fallback.get("layout_archetype"), "workspace"),
        ),
        "components": components,
    }


def _build_fallback_page_plan(prd_json: dict[str, Any], design_brief: dict[str, Any] | None) -> dict[str, Any]:
    title = str(prd_json.get("app_title") or "Generated App")
    app_id = _slugify(title, "generated-app")
    layout = _normalize_layout((design_brief or {}).get("layout_archetype"), "workspace")
    content_language = str(
        prd_json.get("content_language")
        or (design_brief or {}).get("content_language")
        or "en-US"
    )
    page_names = _limit_unique_list(prd_json.get("pages"), 3) or ["Home"]

    pages: list[dict[str, Any]] = []
    for index, item in enumerate(page_names):
        name = str(item or f"Page {index + 1}")
        route = "/" if index == 0 else f"/{_slugify(name, f'page-{index + 1}')}"
        purpose = _localized_text(content_language, f"{name} 的核心体验页", f"Primary experience for {name}")
        key_sections = [
            {
                "id": f"{_slugify(name, 'page')}-hero",
                "type": "hero",
                "goal": _localized_text(content_language, f"介绍 {title} 的核心价值", f"Introduce {title}"),
            },
            {
                "id": f"{_slugify(name, 'page')}-features",
                "type": "feature-grid",
                "goal": _localized_text(content_language, "解释核心体验与主要卖点", "Explain the core experience"),
            },
            {
                "id": f"{_slugify(name, 'page')}-cta",
                "type": "cta-band",
                "goal": _localized_text(content_language, "引导用户进入下一步", "Guide the main next step"),
            },
        ]
        pages.append(
            {
                "id": _slugify(name, f"page-{index + 1}"),
                "name": name,
                "route": route,
                "purpose": purpose,
                "layout_archetype": layout,
                "key_sections": key_sections,
            }
        )

    navigation = [{"label": page["name"], "route": page["route"]} for page in pages]
    data_fields = [str(field) for field in _limit_unique_list(prd_json.get("data_fields"), 8) if str(field).strip()]
    data_models = [{"name": "PrimaryRecord", "fields": data_fields}] if data_fields else []

    return {
        "app_id": app_id,
        "title": title,
        "app_type": "auto",
        "content_language": content_language,
        "layout_archetype": layout,
        "navigation": navigation,
        "data_models": data_models,
        "pages": pages,
    }


def _normalize_page_plan(plan: dict[str, Any], prd_json: dict[str, Any], design_brief: dict[str, Any] | None) -> dict[str, Any]:
    fallback = _build_fallback_page_plan(prd_json, design_brief)

    pages: list[dict[str, Any]] = []
    raw_pages = plan.get("pages")
    if isinstance(raw_pages, list):
        for index, page in enumerate(raw_pages[:5]):
            if not isinstance(page, dict):
                continue
            name = str(page.get("name") or f"Page {index + 1}")
            normalized_page = {
                "id": str(page.get("id") or _slugify(name, f"page-{index + 1}")),
                "name": name,
                "route": _normalize_route(name, page.get("route"), index),
                "purpose": str(page.get("purpose") or f"Primary experience for {name}"),
                "layout_archetype": _normalize_layout(
                    page.get("layout_archetype"),
                    _normalize_layout(plan.get("layout_archetype"), fallback["layout_archetype"]),
                ),
                "key_sections": [],
            }

            sections = page.get("key_sections")
            if isinstance(sections, list):
                for section_index, section in enumerate(sections[:8]):
                    if not isinstance(section, dict):
                        continue
                    section_type = str(section.get("type") or "card").strip()
                    if section_type not in SUPPORTED_COMPONENT_TYPES:
                        section_type = "card"
                    normalized_page["key_sections"].append(
                        {
                            "id": str(section.get("id") or f"{normalized_page['id']}-section-{section_index + 1}"),
                            "type": section_type,
                            "goal": str(section.get("goal") or f"{section_type} section for {name}"),
                        }
                    )

            if not normalized_page["key_sections"]:
                normalized_page["key_sections"] = deepcopy(fallback["pages"][min(index, len(fallback["pages"]) - 1)]["key_sections"])

            pages.append(normalized_page)

    if not pages:
        pages = fallback["pages"]

    navigation = _normalize_navigation(plan.get("navigation"), pages)

    data_models = plan.get("data_models")
    if not isinstance(data_models, list):
        data_models = fallback["data_models"]

    return {
        "app_id": str(plan.get("app_id") or fallback["app_id"]),
        "title": str(plan.get("title") or fallback["title"]),
        "app_type": str(plan.get("app_type") or fallback["app_type"]),
        "content_language": str(plan.get("content_language") or fallback["content_language"]),
        "layout_archetype": _normalize_layout(plan.get("layout_archetype"), fallback["layout_archetype"]),
        "navigation": navigation,
        "data_models": data_models,
        "pages": pages,
    }


def _is_primary_route(route: object) -> bool:
    return isinstance(route, str) and route.startswith("/") and ":" not in route and "*" not in route


def _normalize_navigation(raw_navigation: object, pages: list[dict[str, Any]]) -> list[dict[str, str]]:
    primary_pages = [page for page in pages if _is_primary_route(page.get("route"))]
    page_lookup = {
        str(page.get("route")): str(page.get("name") or page.get("route") or "Page")
        for page in primary_pages
    }

    navigation: list[dict[str, str]] = []
    seen_routes: set[str] = set()
    if isinstance(raw_navigation, list):
        for item in raw_navigation:
            if not isinstance(item, dict):
                continue
            route = str(item.get("route") or "").strip()
            if route not in page_lookup or route in seen_routes:
                continue
            label = str(item.get("label") or page_lookup[route]).strip() or page_lookup[route]
            navigation.append({"label": label, "route": route})
            seen_routes.add(route)

    if navigation:
        return navigation

    for page in primary_pages[:5]:
        route = str(page.get("route"))
        if route in seen_routes:
            continue
        navigation.append({"label": str(page.get("name") or route), "route": route})
        seen_routes.add(route)
    return navigation


def _page_has_component_type(page: dict[str, Any], component_type: str) -> bool:
    components = page.get("components")
    if not isinstance(components, list):
        return False
    return any(isinstance(component, dict) and component.get("type") == component_type for component in components)


def _is_site_like_app(app_schema: dict[str, Any]) -> bool:
    pages = app_schema.get("pages")
    if not isinstance(pages, list) or len(pages) < 2:
        return False

    layouts = {
        _normalize_layout(page.get("layout_archetype"), _normalize_layout(app_schema.get("layout_archetype"), "workspace"))
        for page in pages
        if isinstance(page, dict)
    }
    if layouts and layouts.issubset({"centered-auth"}):
        return False

    navigation = app_schema.get("navigation")
    if isinstance(navigation, list) and len(navigation) >= 2:
        return True

    return any(layout in {"marketing", "editorial", "immersive", "workspace", "dashboard"} for layout in layouts)


def _synchronize_site_shell(app_schema: dict[str, Any]) -> int:
    if not _is_site_like_app(app_schema):
        return 0

    pages = app_schema.get("pages")
    if not isinstance(pages, list):
        return 0

    navigation = _normalize_navigation(app_schema.get("navigation"), [page for page in pages if isinstance(page, dict)])
    app_schema["navigation"] = navigation
    if not navigation:
        return 0

    title = str(app_schema.get("title") or "Generated App")
    sync_count = 0
    for page in pages:
        if not isinstance(page, dict):
            continue
        layout = _normalize_layout(page.get("layout_archetype"), _normalize_layout(app_schema.get("layout_archetype"), "workspace"))
        if layout == "centered-auth":
            continue

        components = page.get("components")
        if not isinstance(components, list):
            continue

        navbar_found = False
        for component in components:
            if not isinstance(component, dict) or component.get("type") != "navbar":
                continue
            props = component.get("props") if isinstance(component.get("props"), dict) else {}
            props["title"] = title
            props["links"] = deepcopy(navigation)
            component["props"] = props
            navbar_found = True

        if navbar_found:
            continue

        components.insert(
            0,
            {
                "id": f"{page.get('id') or 'page'}-nav",
                "type": "navbar",
                "props": {"title": title, "links": deepcopy(navigation)},
                "children": [],
                "actions": [],
                "style": {},
            },
        )
        sync_count += 1

    return sync_count


def _feature_items(goal: str, title: str, language: object) -> list[dict[str, str]]:
    if _is_chinese_language(language):
        return [
            {"title": f"{title} 智能匹配", "description": f"{goal}，并给出更清晰的引导与推荐。"},
            {"title": "可信信息展示", "description": "把流程、证明材料与亮点信息清楚地呈现出来。"},
            {"title": "明确下一步", "description": "让访问者快速理解下一步该做什么并立即行动。"},
        ]
    return [
        {"title": f"{title} Match", "description": f"{goal} with curated recommendations."},
        {"title": "Trust Signals", "description": "Show proof, reviews, and care standards clearly."},
        {"title": "Clear Next Step", "description": "Guide the visitor toward an application or inquiry."},
    ]


def _stat_items(title: str, language: object) -> list[dict[str, str]]:
    if _is_chinese_language(language):
        return [
            {"label": "当前条目", "value": "120+", "caption": f"{title} 相关内容实时更新"},
            {"label": "平均响应", "value": "<24h", "caption": "关键咨询与申请平均响应时间"},
            {"label": "完成率", "value": "93%", "caption": "用户可顺畅完成主要流程"},
        ]
    return [
        {"label": "Profiles", "value": "120+", "caption": f"Active {title.lower()} listings"},
        {"label": "Response", "value": "<24h", "caption": "Average shelter reply time"},
        {"label": "Success Rate", "value": "93%", "caption": "Qualified applications completed"},
    ]


def _section_to_component(section: dict[str, Any], page: dict[str, Any], global_meta: dict[str, Any], index: int) -> dict[str, Any]:
    section_id = str(section.get("id") or f"{page['id']}-section-{index + 1}")
    section_type = str(section.get("type") or "card")
    goal = str(section.get("goal") or "")
    title = str(global_meta.get("title") or "Generated App")
    page_name = str(page.get("name") or "Page")
    language = global_meta.get("content_language")

    if section_type == "hero":
        return {
            "id": section_id,
            "type": "hero",
            "props": {
                "eyebrow": page_name,
                "title": _localized_text(language, f"用 {title} 更顺畅地完成关键体验", f"Find the right next step with {title}"),
                "description": goal or _localized_text(language, f"快速进入 {title} 的核心体验，清楚了解亮点、流程与下一步。", f"Explore a polished first experience for {title}."),
                "primary_cta_label": _localized_text(language, "立即开始", "Start now"),
                "primary_cta_route": page.get("route", "/"),
                "secondary_cta_label": _localized_text(language, "了解更多", "Learn more"),
                "secondary_cta_route": page.get("route", "/"),
                "image_alt": f"{title} hero visual",
                "stats": _stat_items(title, language),
            },
            "children": [],
            "actions": [],
            "style": {},
        }

    if section_type == "feature-grid":
        return {
            "id": section_id,
            "type": "feature-grid",
            "props": {
                "title": page_name,
                "description": goal or _localized_text(language, f"{title} 的核心能力与使用亮点。", f"Key capabilities for {title}."),
                "columns": 3,
                "items": _feature_items(goal or page_name, title, language),
            },
            "children": [],
            "actions": [],
            "style": {},
        }

    if section_type == "stats-band":
        return {
            "id": section_id,
            "type": "stats-band",
            "props": {"items": _stat_items(title, language)},
            "children": [],
            "actions": [],
            "style": {},
        }

    if section_type == "split-section":
        return {
            "id": section_id,
            "type": "split-section",
            "props": {
                "eyebrow": page_name,
                "title": goal or _localized_text(language, f"为什么 {title} 更值得信任", f"Why {title} feels trustworthy"),
                "description": _localized_text(language, f"通过更清晰的结构、可信信息和明确动作，让 {title} 更容易被理解和使用。", f"Make the page actionable, human, and easy to scan for {title}."),
                "bullets": [
                    _localized_text(language, "流程更清楚", "Clear application steps"),
                    _localized_text(language, "证明信息更可信", "Trust-building copy and proof"),
                    _localized_text(language, "转化动作更聚焦", "Focused calls to action"),
                ],
                "image_alt": f"{page_name} supporting visual",
                "primary_cta_label": _localized_text(language, "继续查看", "Continue"),
                "primary_cta_route": page.get("route", "/"),
                "secondary_cta_label": _localized_text(language, "查看详情", "See details"),
                "secondary_cta_route": page.get("route", "/"),
            },
            "children": [],
            "actions": [],
            "style": {},
        }

    if section_type == "cta-band":
        return {
            "id": section_id,
            "type": "cta-band",
            "props": {
                "title": _localized_text(language, f"准备好继续体验 {title} 了吗？", f"Ready to continue with {title}?"),
                "description": goal or _localized_text(language, "把访问者引导到最重要的下一步动作。", "Move the visitor toward the most important action."),
                "primary_cta_label": _localized_text(language, "立即开始", "Get started"),
                "primary_cta_route": page.get("route", "/"),
                "secondary_cta_label": _localized_text(language, "联系我们", "Contact us"),
                "secondary_cta_route": page.get("route", "/"),
            },
            "children": [],
            "actions": [],
            "style": {},
        }

    if section_type == "auth-card":
        return {
            "id": section_id,
            "type": "auth-card",
            "props": {
                "title": _localized_text(language, f"继续进入 {title}", f"Continue with {title}"),
                "description": goal or _localized_text(language, "提供一个简单、可信且不打扰的登录入口。", "Use a simple, trustworthy entry experience."),
                "image_alt": f"{title} account visual",
                "footer_text": _localized_text(language, "需要帮助？请联系支持团队。", "Need help? Contact support."),
            },
            "children": [
                {
                    "id": f"{section_id}-form",
                    "type": "form",
                    "props": {"form_id": f"{section_id}-form"},
                    "children": [
                        {
                            "id": f"{section_id}-email",
                            "type": "input",
                            "props": {
                                "name": "email",
                                "label": _localized_text(language, "邮箱", "Email"),
                                "placeholder": "you@example.com",
                                "type": "email",
                            },
                            "children": [],
                            "actions": [],
                            "style": {},
                        },
                        {
                            "id": f"{section_id}-submit",
                            "type": "button",
                            "props": {"label": _localized_text(language, "继续", "Continue")},
                            "children": [],
                            "actions": [{"trigger": "click", "type": "submit_form", "payload": {"form_id": f"{section_id}-form"}}],
                            "style": {},
                        },
                    ],
                    "actions": [],
                    "style": {},
                }
            ],
            "actions": [],
            "style": {},
        }

    return {
        "id": section_id,
        "type": "card",
        "props": {
            "title": goal or page_name,
            "content": _localized_text(language, f"这是为 {title} 定制的重点内容区块。", f"Focused section for {title}."),
        },
        "children": [],
        "actions": [],
        "style": {},
    }


def _build_fallback_page(page_spec: dict[str, Any], global_meta: dict[str, Any]) -> dict[str, Any]:
    page = {
        "id": str(page_spec.get("id") or "page"),
        "name": str(page_spec.get("name") or "Page"),
        "route": str(page_spec.get("route") or "/"),
        "layout_archetype": _normalize_layout(page_spec.get("layout_archetype"), "workspace"),
        "components": [],
    }

    components: list[dict[str, Any]] = []
    if page["layout_archetype"] != "centered-auth":
        components.append(
            {
                "id": f"{page['id']}-nav",
                "type": "navbar",
                "props": {
                    "title": str(global_meta.get("title") or "Generated App"),
                    "links": global_meta.get("navigation") or [{"label": page["name"], "route": page["route"]}],
                },
                "children": [],
                "actions": [],
                "style": {},
            }
        )

    key_sections = page_spec.get("key_sections") if isinstance(page_spec.get("key_sections"), list) else []
    for index, section in enumerate(key_sections[:6]):
        if isinstance(section, dict):
            components.append(_section_to_component(section, page, global_meta, index))

    if not components:
        components.append(
            {
                "id": f"{page['id']}-hero",
                "type": "hero",
                "props": {
                    "eyebrow": page["name"],
                    "title": str(global_meta.get("title") or page["name"]),
                    "description": str(
                        page_spec.get("purpose")
                        or _localized_text(global_meta.get("content_language"), "当前页面的核心体验入口。", "Primary page experience.")
                    ),
                    "primary_cta_label": _localized_text(global_meta.get("content_language"), "立即查看", "Explore"),
                    "primary_cta_route": page["route"],
                    "secondary_cta_label": _localized_text(global_meta.get("content_language"), "了解详情", "Details"),
                    "secondary_cta_route": page["route"],
                    "image_alt": f"{page['name']} visual",
                    "stats": _stat_items(str(global_meta.get("title") or page["name"]), global_meta.get("content_language")),
                },
                "children": [],
                "actions": [],
                "style": {},
            }
        )

    page["components"] = components
    return page


async def _generate_page_plan(
    llm,
    app_context: str,
    prd_json: dict[str, Any],
    design_brief: dict[str, Any] | None,
) -> dict[str, Any]:
    response = await llm.ainvoke(
        [
            SystemMessage(content=PAGE_PLAN_SYSTEM_PROMPT),
            HumanMessage(
                content=(
                    f"{app_context}\n"
                    f"{build_content_language_instruction(prd_json.get('content_language'))}\n"
                    f"PRD JSON:\n{json.dumps(prd_json, ensure_ascii=False)}\n\n"
                    f"Design brief:\n{json.dumps(design_brief or {}, ensure_ascii=False)}"
                )
            ),
        ]
    )
    payload = extract_json(response.content)
    if not isinstance(payload, dict):
        raise ValueError("page plan must be a JSON object")
    return payload


async def _compose_page(
    llm,
    app_context: str,
    global_plan: dict[str, Any],
    page_spec: dict[str, Any],
    prd_json: dict[str, Any],
    design_brief: dict[str, Any] | None,
) -> dict[str, Any]:
    global_summary = {
        "title": global_plan.get("title"),
        "app_type": global_plan.get("app_type"),
        "layout_archetype": global_plan.get("layout_archetype"),
        "navigation": global_plan.get("navigation"),
        "data_models": global_plan.get("data_models"),
    }
    response = await llm.ainvoke(
        [
            SystemMessage(content=PAGE_COMPOSER_SYSTEM_PROMPT),
            HumanMessage(
                content=(
                    f"{app_context}\n"
                    f"{build_content_language_instruction(global_plan.get('content_language'))}\n"
                    f"Global app summary:\n{json.dumps(global_summary, ensure_ascii=False)}\n\n"
                    f"PRD JSON:\n{json.dumps(prd_json, ensure_ascii=False)}\n\n"
                    f"Design brief:\n{json.dumps(design_brief or {}, ensure_ascii=False)}\n\n"
                    f"Page plan:\n{json.dumps(page_spec, ensure_ascii=False)}"
                )
            ),
        ]
    )
    payload = extract_json(response.content)
    if not isinstance(payload, dict):
        raise ValueError("page composer must return a JSON object")
    return payload


async def run_architect_agent(state: dict) -> dict:
    cb = state.get("ws_callback")
    await notify_agent(cb, "architect", "running")

    try:
        prd_json = state.get("prd_json")
        if not isinstance(prd_json, dict) or not prd_json:
            raise ValueError("Architect Agent requires a valid PRD payload")

        compact_prd = _compact_prd_payload(prd_json)
        design_brief = state.get("design_brief")
        app_context = build_app_context(state.get("app_type"))
        llm = make_llm(temperature=0.2)

        plan_errors: list[str] = []
        try:
            raw_plan = await _generate_page_plan(llm, app_context, compact_prd, design_brief)
        except Exception as exc:
            raw_plan = _build_fallback_page_plan(compact_prd, design_brief if isinstance(design_brief, dict) else None)
            plan_errors.append(f"Planner fallback used: {exc}")

        normalized_plan = _normalize_page_plan(
            raw_plan,
            compact_prd,
            design_brief if isinstance(design_brief, dict) else None,
        )

        planned_pages = normalized_plan.get("pages", [])
        await notify_agent(
            cb,
            "architect",
            "running",
            f"Planned {len(planned_pages)} page(s); composing page schemas",
        )

        global_meta = {
            "title": normalized_plan.get("title"),
            "navigation": normalized_plan.get("navigation"),
            "content_language": normalized_plan.get("content_language"),
        }
        composed_pages: list[dict[str, Any] | None] = [None] * len(planned_pages)
        page_errors: list[str] = []
        page_concurrency = max(1, min(settings.ARCHITECT_PAGE_CONCURRENCY, len(planned_pages) or 1))
        semaphore = asyncio.Semaphore(page_concurrency)

        async def compose_page_with_fallback(index: int, page_spec: dict[str, Any]) -> tuple[int, dict[str, Any], str | None]:
            fallback_page = dict(page_spec)
            fallback_page["_global"] = global_meta

            async with semaphore:
                try:
                    page_payload = await _compose_page(
                        llm,
                        app_context,
                        normalized_plan,
                        page_spec,
                        compact_prd,
                        design_brief if isinstance(design_brief, dict) else None,
                    )
                    return index, _normalize_page(page_payload, fallback_page, index), None
                except Exception as exc:
                    page_name = page_spec.get("name") or page_spec.get("id") or f"page-{index + 1}"
                    return index, _build_fallback_page(fallback_page, global_meta), f"{page_name}: {exc}"

        tasks = [
            asyncio.create_task(compose_page_with_fallback(index, page_spec))
            for index, page_spec in enumerate(planned_pages)
        ]

        completed_pages = 0
        for task in asyncio.as_completed(tasks):
            index, page_payload, page_error = await task
            composed_pages[index] = page_payload
            if page_error:
                page_errors.append(page_error)
            completed_pages += 1
            await notify_agent(
                cb,
                "architect",
                "running",
                f"Composed {completed_pages}/{len(planned_pages)} page(s)",
            )

        app_schema = {
            "app_id": normalized_plan.get("app_id"),
            "title": normalized_plan.get("title"),
            "app_type": normalized_plan.get("app_type"),
            "content_language": normalized_plan.get("content_language"),
            "layout_archetype": normalized_plan.get("layout_archetype"),
            "pages": [page for page in composed_pages if isinstance(page, dict)],
            "navigation": normalized_plan.get("navigation", []),
            "data_models": normalized_plan.get("data_models", []),
        }
        synced_site_pages = _synchronize_site_shell(app_schema)

        page_count = len(app_schema.get("pages", []))
        component_count = sum(
            len(page.get("components", []))
            for page in app_schema.get("pages", [])
            if isinstance(page, dict)
        )
        fallback_count = len(plan_errors) + len(page_errors)
        summary = f"Planned {page_count} page(s) and assembled {component_count} component(s)"
        if fallback_count:
            summary += f"; used {fallback_count} fallback step(s)"
        if synced_site_pages:
            summary += f"; synchronized shared site navigation on {synced_site_pages} page(s)"

        next_state = {**state, "app_schema": app_schema}
        if plan_errors or page_errors:
            next_state["errors"] = state.get("errors", []) + plan_errors + page_errors

        await notify_agent(cb, "architect", "done", summary)
        return next_state

    except Exception as exc:
        message = f"Architect Agent failed: {exc}"
        await notify_agent(cb, "architect", "error", message)
        return {**state, "errors": state.get("errors", []) + [message]}
