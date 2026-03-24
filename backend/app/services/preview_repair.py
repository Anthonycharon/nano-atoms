"""Normalize generated payloads so the preview renderer can always consume them."""

from __future__ import annotations

import copy
import re
from urllib.parse import quote
from typing import Any


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

SUPPORTED_LAYOUT_ARCHETYPES = {
    "marketing",
    "editorial",
    "dashboard",
    "centered-auth",
    "workspace",
    "immersive",
}


def repair_preview_payload(
    app_schema: dict[str, Any] | None,
    code_bundle: dict[str, Any] | None,
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    fixes: list[str] = []
    normalized_schema = _normalize_schema(app_schema or {}, fixes)
    normalized_bundle = _normalize_code_bundle(code_bundle or {}, normalized_schema, fixes)
    return normalized_schema, normalized_bundle, fixes


def _build_image_placeholder_src(label: str) -> str:
    safe_label = (label or "Preview Image").strip()[:48] or "Preview Image"
    svg = f"""
<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="720" viewBox="0 0 1200 720" fill="none">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1200" y2="720" gradientUnits="userSpaceOnUse">
      <stop stop-color="#E0EAFF"/>
      <stop offset="1" stop-color="#F8FBFF"/>
    </linearGradient>
  </defs>
  <rect width="1200" height="720" rx="40" fill="url(#bg)"/>
  <rect x="120" y="120" width="960" height="480" rx="28" fill="#FFFFFF" stroke="#C7D8F7" stroke-width="4"/>
  <circle cx="330" cy="300" r="72" fill="#CFE0FF"/>
  <path d="M210 520L410 360L560 470L710 320L990 520H210Z" fill="#DCE8FF"/>
  <text x="600" y="592" text-anchor="middle" fill="#2D4C7C" font-size="36" font-family="Arial, sans-serif">{safe_label}</text>
</svg>
""".strip()
    return f"data:image/svg+xml;charset=UTF-8,{quote(svg)}"


def _normalize_schema(schema: dict[str, Any], fixes: list[str]) -> dict[str, Any]:
    payload = copy.deepcopy(schema) if isinstance(schema, dict) else {}
    if not isinstance(schema, dict):
        fixes.append("app_schema was not an object and was reset")

    payload["app_id"] = str(payload.get("app_id") or "generated-app")
    payload["title"] = str(payload.get("title") or "Generated App")
    payload["app_type"] = str(payload.get("app_type") or "app")

    pages = payload.get("pages")
    if not isinstance(pages, list):
        fixes.append("pages was not a list and was reset")
        pages = []

    payload["design_brief"] = _normalize_design_brief(payload.get("design_brief"))
    payload["layout_archetype"] = _normalize_layout_archetype(
        payload.get("layout_archetype"),
        payload.get("app_type"),
        payload["design_brief"],
    )
    payload["pages"] = [
        _normalize_page(page, index, fixes, payload["layout_archetype"])
        for index, page in enumerate(pages)
    ]
    payload["navigation"] = _coerce_links(payload.get("navigation"), fixes, "navigation")

    data_models = payload.get("data_models")
    if not isinstance(data_models, list):
        if data_models is not None:
            fixes.append("data_models was not a list and was reset")
        payload["data_models"] = []

    payload["ui_theme"] = _normalize_theme(payload.get("ui_theme"), fixes)
    return payload


def _normalize_page(
    page: Any,
    index: int,
    fixes: list[str],
    default_layout: str,
) -> dict[str, Any]:
    if not isinstance(page, dict):
        fixes.append(f"page[{index}] was not an object and was replaced")
        page = {}

    page_id = str(page.get("id") or f"page_{index + 1}")
    route = page.get("route")
    if not isinstance(route, str) or not route.startswith("/"):
        route = "/" if index == 0 else f"/{page_id}"
        fixes.append(f"{page_id} route was normalized")

    components = page.get("components")
    if not isinstance(components, list):
        fixes.append(f"{page_id} components was not a list and was reset")
        components = []

    normalized_components = [
        _normalize_component(component, page_id, item_index, fixes)
        for item_index, component in enumerate(components)
    ]

    if not normalized_components:
        normalized_components = [
            {
                "id": f"{page_id}_fallback",
                "type": "text",
                "props": {"text": "Content was auto-repaired. Adjust and regenerate if needed."},
                "children": [],
                "actions": [],
                "style": {},
            }
        ]
        fixes.append(f"{page_id} had no renderable components and received a fallback node")

    return {
        "id": page_id,
        "name": str(page.get("name") or page_id),
        "route": route,
        "layout_archetype": _normalize_page_layout_archetype(page, default_layout, normalized_components),
        "components": normalized_components,
    }


def _normalize_component(
    component: Any,
    page_id: str,
    index: int,
    fixes: list[str],
    parent_form_id: str | None = None,
) -> dict[str, Any]:
    if not isinstance(component, dict):
        fixes.append(f"{page_id}.components[{index}] was not an object and was replaced")
        component = {}

    component_id = str(component.get("id") or f"{page_id}_component_{index + 1}")
    raw_type = str(component.get("type") or "text")
    component_type = raw_type if raw_type in SUPPORTED_COMPONENT_TYPES else "text"
    if component_type != raw_type:
        fixes.append(f"{component_id} used unsupported type {raw_type} and was downgraded to text")

    props = component.get("props")
    if not isinstance(props, dict):
        props = {}
        fixes.append(f"{component_id} props was not an object and was reset")
    else:
        props = copy.deepcopy(props)

    style = component.get("style")
    if not isinstance(style, dict):
        style = {}

    current_form_id = component_id if component_type == "form" else parent_form_id

    if component_type in {"input", "select"} and current_form_id and not props.get("form_id"):
        props["form_id"] = current_form_id
        fixes.append(f"{component_id} inherited form_id {current_form_id}")

    if component_type == "select":
        props["options"] = _coerce_select_options(props.get("options"), props, fixes, component_id)

    if component_type == "table":
        props["columns"] = _coerce_columns(props.get("columns"), fixes, component_id)
        props["rows"] = _coerce_rows(props.get("rows"), fixes, component_id)

    if component_type == "navbar":
        props["links"] = _coerce_links(props.get("links"), fixes, component_id)

    if component_type == "image":
        props["src"] = _coerce_image_src(props.get("src"), props, fixes, component_id)
        props["alt"] = str(props.get("alt") or props.get("label") or "Preview image")

    if component_type == "hero":
        props["stats"] = _coerce_stat_items(props.get("stats"), fixes, component_id)
        props["image_src"] = _coerce_image_src(props.get("image_src"), props, fixes, component_id)
        props["image_alt"] = str(props.get("image_alt") or props.get("title") or "Hero image")

    if component_type == "feature-grid":
        props["items"] = _coerce_feature_items(props.get("items"), fixes, component_id)
        props["columns"] = _coerce_column_count(props.get("columns"))

    if component_type == "stats-band":
        props["items"] = _coerce_stat_items(props.get("items"), fixes, component_id)

    if component_type == "split-section":
        props["bullets"] = _coerce_string_items(props.get("bullets"))
        props["image_src"] = _coerce_image_src(props.get("image_src"), props, fixes, component_id)
        props["image_alt"] = str(props.get("image_alt") or props.get("title") or "Section image")
        props["reverse"] = bool(props.get("reverse"))

    if component_type == "cta-band":
        props["title"] = str(props.get("title") or props.get("heading") or "Ready to get started?")
        props["description"] = str(props.get("description") or "")

    if component_type == "auth-card":
        props["image_src"] = _coerce_image_src(props.get("image_src"), props, fixes, component_id)
        props["image_alt"] = str(props.get("image_alt") or props.get("title") or "Authentication visual")
        props["title"] = str(props.get("title") or "Welcome back")
        props["description"] = str(props.get("description") or "")

    raw_children = component.get("children")
    if not isinstance(raw_children, list):
        if raw_children is not None:
            fixes.append(f"{component_id} children was not a list and was reset")
        raw_children = []

    children = [
        _normalize_component(child, page_id, child_index, fixes, current_form_id)
        for child_index, child in enumerate(raw_children)
    ]
    actions = _normalize_actions(component.get("actions"), component_id, current_form_id, fixes)

    return {
        "id": component_id,
        "type": component_type,
        "props": props,
        "children": children,
        "actions": actions,
        "style": style,
    }


def _normalize_actions(
    raw_actions: Any,
    component_id: str,
    current_form_id: str | None,
    fixes: list[str],
) -> list[dict[str, Any]]:
    if not isinstance(raw_actions, list):
        if raw_actions is not None:
            fixes.append(f"{component_id} actions was not a list and was reset")
        return []

    actions: list[dict[str, Any]] = []
    for index, action in enumerate(raw_actions):
        if not isinstance(action, dict):
            fixes.append(f"{component_id}.actions[{index}] was not an object and was dropped")
            continue

        action_type = str(action.get("type") or "")
        if not action_type:
            fixes.append(f"{component_id}.actions[{index}] had no type and was dropped")
            continue

        payload = copy.deepcopy(action.get("payload")) if isinstance(action.get("payload"), dict) else {}

        if action_type == "navigate":
            route = payload.get("route") or action.get("route") or action.get("target")
            if route:
                payload["route"] = str(route)
        elif action_type == "submit_form":
            form_id = (
                payload.get("form_id")
                or action.get("form_id")
                or action.get("target")
                or current_form_id
            )
            if form_id:
                payload["form_id"] = str(form_id)
        elif action_type in {"open_modal", "close_modal"}:
            modal_id = payload.get("modal_id") or action.get("modal_id") or action.get("target")
            if modal_id:
                payload["modal_id"] = str(modal_id)
        elif action_type == "set_value":
            key = payload.get("key") or action.get("key") or action.get("field") or action.get("target")
            if key:
                payload["key"] = str(key)
            if "value" not in payload and "value" in action:
                payload["value"] = action.get("value")

        actions.append(
            {
                "trigger": str(action.get("trigger") or "click"),
                "type": action_type,
                "payload": payload,
            }
        )

    return actions


def _normalize_code_bundle(
    code_bundle: dict[str, Any],
    app_schema: dict[str, Any],
    fixes: list[str],
) -> dict[str, Any]:
    payload = copy.deepcopy(code_bundle) if isinstance(code_bundle, dict) else {}
    if not isinstance(code_bundle, dict):
        fixes.append("code_bundle was not an object and was reset")

    payload["form_handlers"] = _coerce_form_handlers(payload.get("form_handlers"), fixes)
    payload["data_bindings"] = _coerce_data_bindings(payload.get("data_bindings"), fixes)
    payload["initial_state"] = payload.get("initial_state") if isinstance(payload.get("initial_state"), dict) else {}
    if not isinstance(payload.get("page_transitions"), list):
        payload["page_transitions"] = []

    existing_form_ids = {handler["form_id"] for handler in payload["form_handlers"]}
    for form in _collect_forms(app_schema):
        if form["form_id"] in existing_form_ids:
            continue
        payload["form_handlers"].append(
            {
                "form_id": form["form_id"],
                "fields": form["fields"],
                "submit_action": "save_local",
                "validation": {},
            }
        )
        fixes.append(f"form handler for {form['form_id']} was auto-generated")

    return payload


def _collect_forms(app_schema: dict[str, Any]) -> list[dict[str, Any]]:
    forms: list[dict[str, Any]] = []

    def walk(node: dict[str, Any]) -> None:
        if node.get("type") == "form":
            fields: list[str] = []
            for child in node.get("children", []):
                if child.get("type") in {"input", "select"}:
                    fields.append(str(child.get("props", {}).get("name") or child.get("id")))
            forms.append({"form_id": str(node.get("id")), "fields": fields})

        for child in node.get("children", []) or []:
            if isinstance(child, dict):
                walk(child)

    for page in app_schema.get("pages", []):
        for component in page.get("components", []):
            if isinstance(component, dict):
                walk(component)

    return forms


def _coerce_form_handlers(raw_handlers: Any, fixes: list[str]) -> list[dict[str, Any]]:
    if not isinstance(raw_handlers, list):
        if raw_handlers is not None:
            fixes.append("form_handlers was not a list and was reset")
        return []

    handlers: list[dict[str, Any]] = []
    for index, handler in enumerate(raw_handlers):
        if not isinstance(handler, dict) or not handler.get("form_id"):
            fixes.append(f"form_handlers[{index}] was dropped because form_id was missing")
            continue
        fields = handler.get("fields")
        handlers.append(
            {
                "form_id": str(handler["form_id"]),
                "fields": [str(field) for field in fields] if isinstance(fields, list) else [],
                "submit_action": str(handler.get("submit_action") or "save_local"),
                "validation": handler.get("validation") if isinstance(handler.get("validation"), dict) else {},
            }
        )
    return handlers


def _coerce_data_bindings(raw_bindings: Any, fixes: list[str]) -> list[dict[str, Any]]:
    if not isinstance(raw_bindings, list):
        if raw_bindings is not None:
            fixes.append("data_bindings was not a list and was reset")
        return []

    bindings: list[dict[str, Any]] = []
    for index, binding in enumerate(raw_bindings):
        if not isinstance(binding, dict):
            fixes.append(f"data_bindings[{index}] was dropped because it was not an object")
            continue
        component_id = binding.get("component_id")
        if not component_id:
            fixes.append(f"data_bindings[{index}] was dropped because component_id was missing")
            continue
        bindings.append(
            {
                "component_id": str(component_id),
                "data_source": str(binding.get("data_source") or "local_state"),
                "field_path": str(binding.get("field_path") or ""),
            }
        )
    return bindings


def _coerce_select_options(
    raw_options: Any,
    props: dict[str, Any],
    fixes: list[str],
    component_id: str,
) -> list[str]:
    if isinstance(raw_options, list):
        return [str(option) for option in raw_options]

    if isinstance(raw_options, dict):
        fixes.append(f"{component_id} options object was converted to keys")
        return [str(key) for key in raw_options.keys()]

    if isinstance(raw_options, str):
        placeholder_match = re.fullmatch(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}", raw_options.strip())
        if placeholder_match:
            label = str(props.get("label") or props.get("name") or "Option")
            fixes.append(f"{component_id} placeholder options were replaced with demo values")
            return [f"{label} 1", f"{label} 2", f"{label} 3"]

        parts = [part.strip() for part in re.split(r"[,\n|/]+", raw_options) if part.strip()]
        if parts:
            fixes.append(f"{component_id} options string was converted to a list")
            return parts

    if raw_options is not None:
        fixes.append(f"{component_id} options was not renderable and was reset")
    return []


def _coerce_columns(raw_columns: Any, fixes: list[str], component_id: str) -> list[str]:
    if isinstance(raw_columns, list):
        return [str(column) for column in raw_columns]
    if isinstance(raw_columns, str):
        columns = [part.strip() for part in re.split(r"[,\n|/]+", raw_columns) if part.strip()]
        if columns:
            fixes.append(f"{component_id} columns string was converted to a list")
            return columns
    if raw_columns is not None:
        fixes.append(f"{component_id} columns was not renderable and was reset")
    return []


def _coerce_column_count(raw_columns: Any) -> int:
    try:
        value = int(raw_columns)
    except (TypeError, ValueError):
        return 3
    return max(1, min(value, 4))


def _coerce_rows(raw_rows: Any, fixes: list[str], component_id: str) -> list[dict[str, Any]]:
    if isinstance(raw_rows, list):
        rows: list[dict[str, Any]] = []
        for index, row in enumerate(raw_rows):
            if isinstance(row, dict):
                rows.append({str(key): value for key, value in row.items()})
            else:
                fixes.append(f"{component_id} rows[{index}] was dropped because it was not an object")
        return rows

    if isinstance(raw_rows, dict):
        fixes.append(f"{component_id} rows object was wrapped into a list")
        return [{str(key): value for key, value in raw_rows.items()}]

    if raw_rows is not None:
        fixes.append(f"{component_id} rows was not renderable and was reset")
    return []


def _coerce_string_items(raw_items: Any) -> list[str]:
    if isinstance(raw_items, list):
        return [str(item) for item in raw_items if str(item).strip()]
    if isinstance(raw_items, str):
        return [item.strip() for item in re.split(r"[,\n|/]+", raw_items) if item.strip()]
    return []


def _coerce_feature_items(raw_items: Any, fixes: list[str], component_id: str) -> list[dict[str, str]]:
    if not isinstance(raw_items, list):
        if raw_items is not None:
            fixes.append(f"{component_id} items was not a list and was reset")
        return []

    items: list[dict[str, str]] = []
    for index, item in enumerate(raw_items):
        if isinstance(item, dict):
            items.append(
                {
                    "title": str(item.get("title") or item.get("label") or f"Feature {index + 1}"),
                    "description": str(item.get("description") or item.get("text") or ""),
                    "badge": str(item.get("badge") or ""),
                    "icon": str(item.get("icon") or ""),
                }
            )
        elif isinstance(item, str):
            items.append({"title": item, "description": "", "badge": "", "icon": ""})
        else:
            fixes.append(f"{component_id} items[{index}] was dropped because it was not renderable")
    return items


def _coerce_stat_items(raw_items: Any, fixes: list[str], component_id: str) -> list[dict[str, str]]:
    if not isinstance(raw_items, list):
        if raw_items is not None:
            fixes.append(f"{component_id} stat items was not a list and was reset")
        return []

    items: list[dict[str, str]] = []
    for index, item in enumerate(raw_items):
        if not isinstance(item, dict):
            fixes.append(f"{component_id} stat items[{index}] was dropped because it was not an object")
            continue
        items.append(
            {
                "label": str(item.get("label") or f"Metric {index + 1}"),
                "value": str(item.get("value") or item.get("number") or "--"),
                "caption": str(item.get("caption") or item.get("change") or ""),
            }
        )
    return items


def _coerce_links(raw_links: Any, fixes: list[str], owner: str) -> list[dict[str, str]]:
    if not isinstance(raw_links, list):
        if raw_links is not None:
            fixes.append(f"{owner} links was not a list and was reset")
        return []

    links: list[dict[str, str]] = []
    for index, item in enumerate(raw_links):
        if isinstance(item, dict):
            label = (
                item.get("label")
                or item.get("text")
                or item.get("title")
                or item.get("route")
                or item.get("target")
            )
            route = item.get("route") or item.get("target") or "/"
            links.append({"label": str(label or f"Link {index + 1}"), "route": str(route)})
        elif isinstance(item, str):
            links.append({"label": item, "route": "/"})
        else:
            fixes.append(f"{owner} links[{index}] was dropped because it was not renderable")
    return links


def _coerce_image_src(
    raw_src: Any,
    props: dict[str, Any],
    fixes: list[str],
    component_id: str,
) -> str:
    if isinstance(raw_src, str):
        src = raw_src.strip()
        if src and not re.fullmatch(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}", src):
            return src

    label = str(props.get("alt") or props.get("label") or props.get("title") or "Preview image")
    fixes.append(f"{component_id} image source was replaced with a stable placeholder")
    return _build_image_placeholder_src(label)


def _normalize_theme(raw_theme: Any, fixes: list[str]) -> dict[str, Any]:
    theme = copy.deepcopy(raw_theme) if isinstance(raw_theme, dict) else {}
    if raw_theme is not None and not isinstance(raw_theme, dict):
        fixes.append("ui_theme was not an object and was reset")

    theme.setdefault("primary_color", "#6366f1")
    theme.setdefault("secondary_color", "#a5b4fc")
    theme.setdefault("background_color", "#ffffff")
    theme.setdefault("text_color", "#111827")
    theme.setdefault("font_family", "system-ui, sans-serif")
    theme.setdefault("border_radius", "12px")
    theme.setdefault("spacing_unit", 4)
    theme.setdefault("theme_mode", _infer_theme_mode(theme))
    theme.setdefault("canvas_mode", "contrast" if theme["theme_mode"] == "dark" else "soft")
    theme.setdefault("surface_mode", "layered")
    theme.setdefault("density", "balanced")
    theme.setdefault("accent_style", "gradient")
    theme.setdefault("shadow_strength", "soft")
    theme.setdefault("page_background", _default_page_background(theme))
    theme.setdefault("surface_color", _default_surface_color(theme))
    theme.setdefault("surface_text_color", _default_surface_text_color(theme))
    theme.setdefault("border_color", _default_border_color(theme))
    theme.setdefault("muted_text_color", _default_muted_text_color(theme))
    theme.setdefault("input_background", _default_input_background(theme))
    theme.setdefault("subtle_surface_color", _default_subtle_surface_color(theme))
    theme.setdefault("button_text_color", "#f8fafc" if theme["theme_mode"] == "dark" else "#ffffff")

    if not isinstance(theme.get("component_styles"), dict):
        theme["component_styles"] = {}

    return theme


def _normalize_design_brief(raw_brief: Any) -> dict[str, Any]:
    brief = copy.deepcopy(raw_brief) if isinstance(raw_brief, dict) else {}
    brief.setdefault("experience_goal", "")
    brief.setdefault("primary_user_mindset", "")
    brief.setdefault("visual_direction", "")
    brief.setdefault("layout_archetype", "auto")
    brief.setdefault("theme_mode", "auto")
    brief.setdefault("color_story", "")
    brief.setdefault("layout_density", "balanced")
    brief["tone_keywords"] = _coerce_string_items(brief.get("tone_keywords"))
    brief["style_constraints"] = _coerce_string_items(brief.get("style_constraints"))
    brief["section_recommendations"] = _coerce_string_items(brief.get("section_recommendations"))
    brief["quality_checklist"] = _coerce_string_items(brief.get("quality_checklist"))
    brief["avoid_patterns"] = _coerce_string_items(brief.get("avoid_patterns"))
    return brief


def _normalize_layout_archetype(raw_value: Any, app_type: Any, brief: dict[str, Any] | None) -> str:
    if isinstance(raw_value, str):
        normalized = raw_value.strip().lower()
        if normalized in SUPPORTED_LAYOUT_ARCHETYPES:
            return normalized
    return _infer_layout_archetype(app_type, brief)


def _normalize_page_layout_archetype(
    page: dict[str, Any],
    default_layout: str,
    normalized_components: list[dict[str, Any]],
) -> str:
    raw_value = page.get("layout_archetype")
    if isinstance(raw_value, str):
        normalized = raw_value.strip().lower()
        if normalized in SUPPORTED_LAYOUT_ARCHETYPES:
            return normalized

    page_name = str(page.get("name") or "")
    route = str(page.get("route") or "")
    component_types = {
        str(component.get("type"))
        for component in normalized_components
        if isinstance(component, dict) and component.get("type")
    }
    fingerprint = f"{page_name} {route} {' '.join(sorted(component_types))}".lower()

    if any(token in fingerprint for token in {"login", "sign-in", "signin", "signup", "register", "auth"}):
        return "centered-auth"
    if "auth-card" in component_types and len(component_types) <= 3:
        return "centered-auth"
    if any(token in fingerprint for token in {"blog", "editorial", "article", "journal", "story"}):
        return "editorial"
    if {"hero", "feature-grid", "split-section", "cta-band"} & component_types:
        return "marketing" if default_layout != "immersive" else default_layout
    if {"table", "stat-card"} & component_types:
        return "dashboard" if default_layout in {"dashboard", "workspace"} else "workspace"
    return default_layout


def _infer_theme_mode(theme: dict[str, Any]) -> str:
    raw_mode = str(theme.get("theme_mode") or "").strip().lower()
    if raw_mode in {"light", "dark", "mixed"}:
        return raw_mode
    if _looks_dark_color(str(theme.get("background_color") or "")):
        return "dark"
    return "light"


def _infer_layout_archetype(app_type: Any, brief: dict[str, Any] | None) -> str:
    brief = brief or {}
    raw_brief_layout = str(brief.get("layout_archetype") or "").strip().lower()
    if raw_brief_layout in SUPPORTED_LAYOUT_ARCHETYPES:
        return raw_brief_layout

    search_space = " ".join(
        [
            str(app_type or ""),
            str(brief.get("visual_direction") or ""),
            str(brief.get("experience_goal") or ""),
            str(brief.get("primary_user_mindset") or ""),
            " ".join(_coerce_string_items(brief.get("section_recommendations"))),
            " ".join(_coerce_string_items(brief.get("tone_keywords"))),
        ]
    ).lower()

    if any(token in search_space for token in {"login", "sign in", "signin", "signup", "register", "auth"}):
        return "centered-auth"
    if any(token in search_space for token in {"blog", "editorial", "journal", "article", "story", "content"}):
        return "editorial"
    if any(token in search_space for token in {"marketing", "landing", "campaign", "launch", "showcase", "promo"}):
        return "marketing"
    if any(token in search_space for token in {"immersive", "cinematic", "showcase", "storyworld", "experience"}):
        return "immersive"
    if any(token in search_space for token in {"dashboard", "analytics", "admin", "crm", "report", "monitor"}):
        return "dashboard"
    if any(token in search_space for token in {"workspace", "assistant", "tool", "internal", "studio", "copilot"}):
        return "workspace"
    return "workspace"


def _default_page_background(theme: dict[str, Any]) -> str:
    if isinstance(theme.get("page_background"), str) and theme["page_background"].strip():
        return theme["page_background"].strip()
    background = str(theme.get("background_color") or "#ffffff")
    if theme.get("theme_mode") == "dark":
        return f"radial-gradient(circle at top, {background} 0%, #0f172a 38%, #020617 100%)"
    return f"radial-gradient(circle at top, #eef4ff 0%, {background} 38%, #ffffff 100%)"


def _default_surface_color(theme: dict[str, Any]) -> str:
    if isinstance(theme.get("surface_color"), str) and theme["surface_color"].strip():
        return theme["surface_color"].strip()
    if theme.get("theme_mode") == "dark":
        return "rgba(15, 23, 42, 0.78)"
    return "rgba(255, 255, 255, 0.92)"


def _default_surface_text_color(theme: dict[str, Any]) -> str:
    if isinstance(theme.get("surface_text_color"), str) and theme["surface_text_color"].strip():
        return theme["surface_text_color"].strip()
    return "#f8fafc" if theme.get("theme_mode") == "dark" else str(theme.get("text_color") or "#111827")


def _default_border_color(theme: dict[str, Any]) -> str:
    if isinstance(theme.get("border_color"), str) and theme["border_color"].strip():
        return theme["border_color"].strip()
    if theme.get("theme_mode") == "dark":
        return "rgba(148, 163, 184, 0.18)"
    return "#dbe3f0"


def _default_muted_text_color(theme: dict[str, Any]) -> str:
    if isinstance(theme.get("muted_text_color"), str) and theme["muted_text_color"].strip():
        return theme["muted_text_color"].strip()
    if theme.get("theme_mode") == "dark":
        return "rgba(226, 232, 240, 0.72)"
    return "#64748b"


def _default_input_background(theme: dict[str, Any]) -> str:
    if isinstance(theme.get("input_background"), str) and theme["input_background"].strip():
        return theme["input_background"].strip()
    if theme.get("theme_mode") == "dark":
        return "rgba(15, 23, 42, 0.92)"
    return "#ffffff"


def _default_subtle_surface_color(theme: dict[str, Any]) -> str:
    if isinstance(theme.get("subtle_surface_color"), str) and theme["subtle_surface_color"].strip():
        return theme["subtle_surface_color"].strip()
    if theme.get("theme_mode") == "dark":
        return "rgba(30, 41, 59, 0.7)"
    return "rgba(248, 250, 252, 0.86)"


def _looks_dark_color(value: str) -> bool:
    rgb = _hex_to_rgb(value)
    if rgb is None:
        return False
    red, green, blue = rgb
    luminance = (0.2126 * red + 0.7152 * green + 0.0722 * blue) / 255
    return luminance < 0.45


def _hex_to_rgb(value: str) -> tuple[int, int, int] | None:
    text = value.strip()
    if not text.startswith("#"):
        return None
    hex_value = text[1:]
    if len(hex_value) == 3:
        hex_value = "".join(ch * 2 for ch in hex_value)
    if len(hex_value) != 6 or not re.fullmatch(r"[0-9a-fA-F]{6}", hex_value):
        return None
    return (
        int(hex_value[0:2], 16),
        int(hex_value[2:4], 16),
        int(hex_value[4:6], 16),
    )
