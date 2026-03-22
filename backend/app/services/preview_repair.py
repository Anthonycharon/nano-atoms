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

    payload["pages"] = [_normalize_page(page, index, fixes) for index, page in enumerate(pages)]
    payload["navigation"] = _coerce_links(payload.get("navigation"), fixes, "navigation")

    data_models = payload.get("data_models")
    if not isinstance(data_models, list):
        if data_models is not None:
            fixes.append("data_models was not a list and was reset")
        payload["data_models"] = []

    payload["ui_theme"] = _normalize_theme(payload.get("ui_theme"), fixes)
    return payload


def _normalize_page(page: Any, index: int, fixes: list[str]) -> dict[str, Any]:
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

    if not isinstance(theme.get("component_styles"), dict):
        theme["component_styles"] = {}

    return theme
