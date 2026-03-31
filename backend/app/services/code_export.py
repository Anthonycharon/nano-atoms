"""Build a richer multi-page static website export from schema + code bundle."""

from __future__ import annotations

import json
import re
from html import escape
from pathlib import Path
from typing import Any
from urllib.parse import quote

from app.agents.utils import extract_json

# Nano UI 组件库路径
NANO_UI_PATH = Path(__file__).parent.parent / "assets" / "nano-ui.js"


SUPPORTED_LAYOUTS = {"marketing", "editorial", "dashboard", "centered-auth", "workspace", "immersive"}


def _slugify(value: str) -> str:
    text = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower())
    return text.strip("-") or "nano-atoms-app"


def _safe_id(value: str) -> str:
    text = re.sub(r"[^a-zA-Z0-9_-]+", "-", value.strip())
    return text.strip("-") or "block"


def _json_text(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


def _json_script(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False).replace("</", "<\\/")


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


def _sanitize_freeform_markup(raw_text: Any) -> str:
    raw = str(raw_text or "").strip()
    if not raw:
        return ""

    if "\"body_html\"" in raw or raw.lstrip().startswith("{") or raw.lstrip().startswith("```json"):
        escaped_body = _extract_escaped_body_html_field(raw)
        if escaped_body and escaped_body != raw:
            return _sanitize_freeform_markup(escaped_body)
        try:
            payload = extract_json(raw)
        except Exception:
            payload = None
        if isinstance(payload, dict):
            nested_body = str(payload.get("body_html") or "").strip()
            if nested_body and nested_body != raw:
                return _sanitize_freeform_markup(nested_body)
        escaped_fragment = _extract_escaped_main_fragment(raw)
        if escaped_fragment and escaped_fragment != raw:
            return _sanitize_freeform_markup(escaped_fragment)
        literal_body = _extract_json_string_field(raw, "body_html")
        if literal_body and literal_body != raw and "</" in literal_body:
            return _sanitize_freeform_markup(literal_body)

    for pattern in (
        r"```html\s*([\s\S]*?)```",
        r"```json\s*([\s\S]*?)```",
    ):
        match = re.search(pattern, raw, re.IGNORECASE)
        if match:
            candidate = match.group(1).strip()
            if candidate != raw:
                return _sanitize_freeform_markup(candidate)

    main_match = re.search(r"(<main[\s\S]*?</main>)", raw, re.IGNORECASE)
    if main_match:
        return main_match.group(1).strip()

    if any(tag in raw for tag in ("<section", "<div", "<article")):
        return f'<main class="na-page na-freeform-shell">{raw}</main>'

    return raw


def _escape_text(value: Any) -> str:
    return escape(str(value or ""))


def _escape_attr(value: Any) -> str:
    return escape(str(value or ""), quote=True)


def _hex_to_rgb(value: str | None) -> tuple[int, int, int] | None:
    if not isinstance(value, str):
        return None
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


def _hex_to_rgba(value: str | None, alpha: float, fallback: str) -> str:
    rgb = _hex_to_rgb(value)
    if rgb is None:
        return fallback
    return f"rgba({rgb[0]}, {rgb[1]}, {rgb[2]}, {alpha})"


def _infer_theme_mode(theme: dict[str, Any]) -> str:
    raw_mode = str(theme.get("theme_mode") or "").strip().lower()
    if raw_mode in {"light", "dark", "mixed"}:
        return raw_mode
    rgb = _hex_to_rgb(theme.get("background_color"))
    if rgb is None:
        return "light"
    luminance = (0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]) / 255
    return "dark" if luminance < 0.45 else "light"


def _infer_layout_archetype(app_schema: dict[str, Any], page: dict[str, Any] | None = None) -> str:
    raw = str((page or {}).get("layout_archetype") or app_schema.get("layout_archetype") or "").strip().lower()
    if raw in SUPPORTED_LAYOUTS:
        return raw

    design_brief = app_schema.get("design_brief") if isinstance(app_schema.get("design_brief"), dict) else {}
    brief_layout = str(design_brief.get("layout_archetype") or "").strip().lower()
    if brief_layout in SUPPORTED_LAYOUTS:
        return brief_layout

    app_type = str(app_schema.get("app_type") or "").lower()
    if re.search(r"auth|login|register|signup|signin", app_type):
        return "centered-auth"
    if re.search(r"blog|editorial|article|journal|content", app_type):
        return "editorial"
    if re.search(r"landing|marketing|campaign|launch|showcase|promo", app_type):
        return "marketing"
    if re.search(r"dashboard|analytics|admin|crm|report|monitor", app_type):
        return "dashboard"
    if re.search(r"immersive|cinematic|experience", app_type):
        return "immersive"
    return "workspace"


def _content_language(app_schema: dict[str, Any]) -> str:
    language = str(
        app_schema.get("content_language")
        or (app_schema.get("design_brief") or {}).get("content_language")
        or ""
    ).strip()
    return language or "en-US"


def _is_chinese(language: str) -> bool:
    return language.lower() == "zh-cn"


def _localized(language: str, zh: str, en: str) -> str:
    return zh if _is_chinese(language) else en


def _image_placeholder_data_uri(label: str = "Preview Image") -> str:
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
  <text x="600" y="592" text-anchor="middle" fill="#2D4C7C" font-size="36" font-family="Arial, sans-serif">{escape(safe_label)}</text>
</svg>
""".strip()
    return f"data:image/svg+xml;charset=UTF-8,{quote(svg)}"


def _infer_language(path: str) -> str:
    if path.endswith(".html"):
        return "html"
    if path.endswith(".css"):
        return "css"
    if path.endswith(".js"):
        return "javascript"
    if path.endswith(".json"):
        return "json"
    if path.endswith(".md"):
        return "markdown"
    return "text"


def _theme_tokens(app_schema: dict[str, Any]) -> dict[str, str]:
    theme = app_schema.get("ui_theme") if isinstance(app_schema.get("ui_theme"), dict) else {}
    mode = _infer_theme_mode(theme)
    primary = str(theme.get("primary_color") or "#4f46e5")
    secondary = str(theme.get("secondary_color") or "#22c55e")
    background = str(theme.get("background_color") or ("#020617" if mode == "dark" else "#f8fafc"))
    text = str(theme.get("text_color") or ("#f8fafc" if mode == "dark" else "#0f172a"))
    surface = str(theme.get("surface_color") or ("rgba(15,23,42,0.78)" if mode == "dark" else "rgba(255,255,255,0.88)"))
    surface_text = str(theme.get("surface_text_color") or text)
    border = str(theme.get("border_color") or ("rgba(148,163,184,0.18)" if mode == "dark" else "rgba(148,163,184,0.18)"))
    muted = str(theme.get("muted_text_color") or ("rgba(226,232,240,0.74)" if mode == "dark" else "#475569"))
    subtle = str(theme.get("subtle_surface_color") or ("rgba(30,41,59,0.7)" if mode == "dark" else "rgba(255,255,255,0.62)"))
    accent_soft = _hex_to_rgba(primary, 0.2 if mode == "dark" else 0.12, "rgba(79,70,229,0.12)")
    secondary_soft = _hex_to_rgba(secondary, 0.22 if mode == "dark" else 0.14, "rgba(34,197,94,0.14)")
    shadow = "0 24px 80px rgba(2,6,23,0.36)" if mode == "dark" else "0 24px 80px rgba(15,23,42,0.12)"
    font_family = str(theme.get("font_family") or '"Plus Jakarta Sans", "PingFang SC", "Microsoft YaHei", system-ui, sans-serif')
    radius = str(theme.get("border_radius") or "20px")
    page_background = str(
        theme.get("page_background")
        or (
            f"radial-gradient(circle at top, #0f172a 0%, {background} 36%, #020617 100%)"
            if mode == "dark"
            else f"radial-gradient(circle at top, #eff6ff 0%, {background} 38%, #ffffff 100%)"
        )
    )
    return {
        "mode": mode,
        "primary": primary,
        "secondary": secondary,
        "background": background,
        "text": text,
        "surface": surface,
        "surface_text": surface_text,
        "border": border,
        "muted": muted,
        "subtle": subtle,
        "accent_soft": accent_soft,
        "secondary_soft": secondary_soft,
        "shadow": shadow,
        "font_family": font_family,
        "radius": radius,
        "page_background": page_background,
    }


def _page_file_name(route: str, index: int) -> str:
    normalized = route.strip() or "/"
    if normalized == "/":
        return "home.html"
    slug = _slugify(normalized.strip("/").replace("/", "-"))
    return f"{slug or f'page-{index + 1}'}.html"


def _nav_target(route: str) -> str:
    return route if route.startswith("/") else f"/{route}"


def _action_route(node: dict[str, Any]) -> str | None:
    actions = node.get("actions") if isinstance(node.get("actions"), list) else []
    for action in actions:
        if not isinstance(action, dict):
            continue
        if action.get("type") == "navigate":
            payload = action.get("payload") if isinstance(action.get("payload"), dict) else {}
            route = payload.get("route")
            if isinstance(route, str) and route.strip():
                return _nav_target(route.strip())
    return None


def _render_children(children: list[Any], app_schema: dict[str, Any], page: dict[str, Any]) -> str:
    return "".join(_render_component(child, app_schema, page) for child in children if isinstance(child, dict))


def _render_button(label: str, route: str | None, variant: str = "primary") -> str:
    button_class = "na-btn" if variant == "primary" else "na-btn na-btn-secondary"
    if route:
        return f'<button type="button" class="{button_class}" data-route="{_escape_attr(route)}">{_escape_text(label)}</button>'
    return f'<button type="button" class="{button_class}">{_escape_text(label)}</button>'


def _render_component(node: dict[str, Any], app_schema: dict[str, Any], page: dict[str, Any]) -> str:
    component_type = str(node.get("type") or "text")
    props = node.get("props") if isinstance(node.get("props"), dict) else {}
    children = node.get("children") if isinstance(node.get("children"), list) else []
    route = _action_route(node)
    component_id = _safe_id(str(node.get("id") or component_type))
    language = _content_language(app_schema)
    image_fallback = _image_placeholder_data_uri(str(props.get("alt") or props.get("image_alt") or props.get("title") or "Preview image"))

    if component_type == "heading":
        return f'<section class="na-section na-copy"><h2 id="{component_id}" class="na-heading">{_escape_text(props.get("text") or props.get("children") or _localized(language, "标题", "Heading"))}</h2></section>'

    if component_type == "text":
        return f'<section class="na-section na-copy"><p id="{component_id}" class="na-text">{_escape_text(props.get("text") or props.get("children") or "")}</p></section>'

    if component_type == "button":
        return f'<section class="na-section na-copy">{_render_button(str(props.get("label") or props.get("text") or _localized(language, "按钮", "Button")), route, "primary")}</section>'

    if component_type == "input":
        return (
            '<div class="na-field">'
            f'<label class="na-label" for="{component_id}">{_escape_text(props.get("label") or props.get("name") or _localized(language, "字段", "Field"))}</label>'
            f'<input id="{component_id}" class="na-input" type="{_escape_attr(props.get("type") or "text")}" placeholder="{_escape_attr(props.get("placeholder") or "")}" />'
            "</div>"
        )

    if component_type == "select":
        options = props.get("options") if isinstance(props.get("options"), list) else []
        options_markup = "".join(
            f'<option value="{_escape_attr(item)}">{_escape_text(item)}</option>' for item in options
        )
        return (
            '<div class="na-field">'
            f'<label class="na-label" for="{component_id}">{_escape_text(props.get("label") or props.get("name") or _localized(language, "选项", "Option"))}</label>'
            f'<select id="{component_id}" class="na-input"><option value="">{_escape_text(props.get("placeholder") or _localized(language, "请选择", "Select an option"))}</option>{options_markup}</select>'
            "</div>"
        )

    if component_type == "form":
        return (
            f'<section class="na-section"><form class="na-form na-panel" data-form-id="{_escape_attr(node.get("id") or component_id)}">'
            f"{_render_children(children, app_schema, page)}"
            f'<button type="submit" class="na-btn">{_localized(language, "提交", "Submit")}</button>'
            "</form></section>"
        )

    if component_type == "card":
        title = props.get("title")
        content = props.get("content")
        body = _render_children(children, app_schema, page) or f'<p class="na-text">{_escape_text(content or _localized(language, "内容待补充", "Content pending"))}</p>'
        title_markup = f'<h3 class="na-card-title">{_escape_text(title)}</h3>' if title else ""
        return f'<section class="na-section"><div class="na-panel na-card">{title_markup}{body}</div></section>'

    if component_type == "stat-card":
        return (
            '<section class="na-section"><div class="na-panel na-stat">'
            f'<div class="na-stat-label">{_escape_text(props.get("label") or _localized(language, "指标", "Metric"))}</div>'
            f'<div class="na-stat-value">{_escape_text(props.get("value") or "--")}</div>'
            f'<div class="na-stat-caption">{_escape_text(props.get("change") or "")}</div>'
            "</div></section>"
        )

    if component_type == "table":
        columns = props.get("columns") if isinstance(props.get("columns"), list) else []
        rows = props.get("rows") if isinstance(props.get("rows"), list) else []
        head = "".join(f"<th>{_escape_text(col)}</th>" for col in columns)
        body_rows = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            body_rows.append("<tr>" + "".join(f"<td>{_escape_text(row.get(col) or '')}</td>" for col in columns) + "</tr>")
        if not body_rows:
            body_rows.append(f'<tr><td colspan="{max(len(columns), 1)}" class="na-empty-row">{_localized(language, "暂无数据", "No data yet")}</td></tr>')
        return f'<section class="na-section"><div class="na-panel na-table-wrap"><table class="na-table"><thead><tr>{head}</tr></thead><tbody>{"".join(body_rows)}</tbody></table></div></section>'

    if component_type == "navbar":
        title = str(props.get("title") or app_schema.get("title") or "App")
        links = props.get("links") if isinstance(props.get("links"), list) else []
        links_markup = []
        current_route = _nav_target(str(page.get("route") or "/"))
        for item in links:
            if not isinstance(item, dict):
                continue
            target_route = _nav_target(str(item.get("route") or "/"))
            active = " is-active" if target_route == current_route else ""
            links_markup.append(
                f'<button type="button" class="na-nav-link{active}" data-route="{_escape_attr(target_route)}">{_escape_text(item.get("label") or item.get("text") or "Link")}</button>'
            )
        return f'<header class="na-header-shell"><div class="na-header-backdrop"></div><nav class="na-navbar"><button type="button" class="na-brand" data-route="/">{_escape_text(title)}</button><div class="na-nav-links">{"".join(links_markup)}</div></nav></header>'

    if component_type == "tag":
        return f'<span class="na-tag">{_escape_text(props.get("text") or props.get("label") or _localized(language, "标签", "Tag"))}</span>'

    if component_type == "image":
        src = str(props.get("src") or image_fallback)
        alt = str(props.get("alt") or props.get("title") or _localized(language, "预览图", "Preview image"))
        return f'<section class="na-section"><figure class="na-image-frame"><img src="{_escape_attr(src)}" alt="{_escape_attr(alt)}" onerror="this.src=\'{_escape_attr(image_fallback)}\'" /></figure></section>'

    if component_type == "hero":
        stats = props.get("stats") if isinstance(props.get("stats"), list) else []
        stats_markup = "".join(
            (
                '<div class="na-hero-metric">'
                f'<div class="na-hero-metric-value">{_escape_text(item.get("value") or "--")}</div>'
                f'<div class="na-hero-metric-label">{_escape_text(item.get("label") or "")}</div>'
                f'<div class="na-hero-metric-caption">{_escape_text(item.get("caption") or "")}</div>'
                "</div>"
            )
            for item in stats
            if isinstance(item, dict)
        )
        image_src = str(props.get("image_src") or image_fallback)
        image_alt = str(props.get("image_alt") or props.get("title") or _localized(language, "主视觉", "Hero visual"))
        actions = "".join(
            [
                _render_button(str(props.get("primary_cta_label") or _localized(language, "立即开始", "Get started")), str(props.get("primary_cta_route") or page.get("route") or "/"), "primary") if props.get("primary_cta_label") or props.get("primary_cta_route") else "",
                _render_button(str(props.get("secondary_cta_label") or _localized(language, "了解更多", "Learn more")), str(props.get("secondary_cta_route") or page.get("route") or "/"), "secondary") if props.get("secondary_cta_label") or props.get("secondary_cta_route") else "",
            ]
        )
        return f'<section class="na-section na-hero-section"><div class="na-hero-grid"><div class="na-hero-copy"><div class="na-kicker">{_escape_text(props.get("eyebrow") or page.get("name") or "")}</div><h1 class="na-display">{_escape_text(props.get("title") or app_schema.get("title") or _localized(language, "网站标题", "Website title"))}</h1><p class="na-hero-description">{_escape_text(props.get("description") or "")}</p><div class="na-actions">{actions}</div><div class="na-hero-metrics">{stats_markup}</div></div><div class="na-hero-visual"><img src="{_escape_attr(image_src)}" alt="{_escape_attr(image_alt)}" onerror="this.src=\'{_escape_attr(image_fallback)}\'" /></div></div></section>'

    if component_type == "feature-grid":
        items = props.get("items") if isinstance(props.get("items"), list) else []
        columns = max(1, min(int(props.get("columns") or 3), 4))
        items_markup = "".join(
            (
                '<article class="na-feature-item">'
                f'<div class="na-feature-badge">{_escape_text(item.get("badge") or item.get("icon") or "")}</div>'
                f'<h3 class="na-feature-title">{_escape_text(item.get("title") or "")}</h3>'
                f'<p class="na-feature-description">{_escape_text(item.get("description") or "")}</p>'
                '</article>'
            )
            for item in items
            if isinstance(item, dict)
        )
        return f'<section class="na-section"><div class="na-copy-block"><div class="na-kicker">{_escape_text(page.get("name") or "")}</div><h2 class="na-section-title">{_escape_text(props.get("title") or _localized(language, "核心亮点", "Highlights"))}</h2><p class="na-section-description">{_escape_text(props.get("description") or "")}</p></div><div class="na-feature-grid na-cols-{columns}">{items_markup}</div></section>'

    if component_type == "stats-band":
        items = props.get("items") if isinstance(props.get("items"), list) else []
        items_markup = "".join(
            (
                '<div class="na-stat-chip">'
                f'<div class="na-stat-chip-value">{_escape_text(item.get("value") or "--")}</div>'
                f'<div class="na-stat-chip-label">{_escape_text(item.get("label") or "")}</div>'
                f'<div class="na-stat-chip-caption">{_escape_text(item.get("caption") or "")}</div>'
                '</div>'
            )
            for item in items
            if isinstance(item, dict)
        )
        return f'<section class="na-section"><div class="na-stat-band">{items_markup}</div></section>'

    if component_type == "split-section":
        bullets = props.get("bullets") if isinstance(props.get("bullets"), list) else []
        bullets_markup = "".join(f"<li>{_escape_text(item)}</li>" for item in bullets)
        reverse_class = " is-reverse" if props.get("reverse") else ""
        image_src = str(props.get("image_src") or image_fallback)
        image_alt = str(props.get("image_alt") or props.get("title") or _localized(language, "内容配图", "Section visual"))
        actions = "".join(
            [
                _render_button(str(props.get("primary_cta_label") or _localized(language, "继续查看", "Continue")), str(props.get("primary_cta_route") or page.get("route") or "/"), "primary") if props.get("primary_cta_label") or props.get("primary_cta_route") else "",
                _render_button(str(props.get("secondary_cta_label") or _localized(language, "查看详情", "See details")), str(props.get("secondary_cta_route") or page.get("route") or "/"), "secondary") if props.get("secondary_cta_label") or props.get("secondary_cta_route") else "",
            ]
        )
        return f'<section class="na-section"><div class="na-split{reverse_class}"><div class="na-split-copy"><div class="na-kicker">{_escape_text(props.get("eyebrow") or page.get("name") or "")}</div><h2 class="na-section-title">{_escape_text(props.get("title") or _localized(language, "重点内容", "Key content"))}</h2><p class="na-section-description">{_escape_text(props.get("description") or "")}</p><ul class="na-bullets">{bullets_markup}</ul><div class="na-actions">{actions}</div></div><div class="na-split-visual"><img src="{_escape_attr(image_src)}" alt="{_escape_attr(image_alt)}" onerror="this.src=\'{_escape_attr(image_fallback)}\'" /></div></div></section>'

    if component_type == "cta-band":
        actions = "".join(
            [
                _render_button(str(props.get("primary_cta_label") or _localized(language, "立即开始", "Get started")), str(props.get("primary_cta_route") or page.get("route") or "/"), "primary") if props.get("primary_cta_label") or props.get("primary_cta_route") else "",
                _render_button(str(props.get("secondary_cta_label") or _localized(language, "联系我们", "Contact us")), str(props.get("secondary_cta_route") or page.get("route") or "/"), "secondary") if props.get("secondary_cta_label") or props.get("secondary_cta_route") else "",
            ]
        )
        return f'<section class="na-section"><div class="na-cta"><h2 class="na-cta-title">{_escape_text(props.get("title") or _localized(language, "准备继续了吗？", "Ready to continue?"))}</h2><p class="na-cta-description">{_escape_text(props.get("description") or "")}</p><div class="na-actions">{actions}</div></div></section>'

    if component_type == "auth-card":
        image_src = str(props.get("image_src") or image_fallback)
        image_alt = str(props.get("image_alt") or props.get("title") or _localized(language, "账户视觉图", "Authentication visual"))
        footer = ""
        if props.get("footer_text"):
            footer_text = _escape_text(props.get("footer_text"))
            if props.get("footer_link_label") and props.get("footer_link_route"):
                footer = f'<div class="na-auth-footer">{footer_text} <button type="button" class="na-inline-link" data-route="{_escape_attr(props.get("footer_link_route"))}">{_escape_text(props.get("footer_link_label"))}</button></div>'
            else:
                footer = f'<div class="na-auth-footer">{footer_text}</div>'
        return f'<section class="na-section"><div class="na-auth-shell"><div class="na-auth-visual"><img src="{_escape_attr(image_src)}" alt="{_escape_attr(image_alt)}" onerror="this.src=\'{_escape_attr(image_fallback)}\'" /></div><div class="na-auth-body"><h2 class="na-section-title">{_escape_text(props.get("title") or _localized(language, "欢迎回来", "Welcome back"))}</h2><p class="na-section-description">{_escape_text(props.get("description") or "")}</p>{_render_children(children, app_schema, page)}{footer}</div></div></section>'

    if component_type == "modal":
        return f'<section class="na-section"><div class="na-panel na-card"><div class="na-kicker">{_localized(language, "弹窗内容", "Modal content")}</div>{_render_children(children, app_schema, page)}</div></section>'

    return f'<section class="na-section na-copy"><p class="na-text">{_escape_text(props.get("text") or props.get("title") or "")}</p></section>'


def _render_page_markup(app_schema: dict[str, Any], page: dict[str, Any]) -> str:
    layout = _infer_layout_archetype(app_schema, page)
    components = page.get("components") if isinstance(page.get("components"), list) else []
    content = "".join(_render_component(node, app_schema, page) for node in components if isinstance(node, dict))
    return f'<main class="na-page na-layout-{_escape_attr(layout)}" data-page-route="{_escape_attr(page.get("route") or "/")}">{content}</main>'


def _build_styles_css(app_schema: dict[str, Any]) -> str:
    tokens = _theme_tokens(app_schema)
    return f""":root {{
  --na-primary: {tokens["primary"]};
  --na-secondary: {tokens["secondary"]};
  --na-bg: {tokens["background"]};
  --na-text: {tokens["text"]};
  --na-surface: {tokens["surface"]};
  --na-surface-text: {tokens["surface_text"]};
  --na-border: {tokens["border"]};
  --na-muted: {tokens["muted"]};
  --na-subtle: {tokens["subtle"]};
  --na-accent-soft: {tokens["accent_soft"]};
  --na-secondary-soft: {tokens["secondary_soft"]};
  --na-shadow: {tokens["shadow"]};
  --na-radius: {tokens["radius"]};
  --na-page-bg: {tokens["page_background"]};
  --na-font: {tokens["font_family"]};
}}
* {{ box-sizing: border-box; }}
html, body {{ margin: 0; min-height: 100%; }}
body {{
  background: var(--na-page-bg);
  color: var(--na-text);
  font-family: var(--na-font);
}}
button, input, select {{ font: inherit; }}
.na-site-shell {{ min-height: 100vh; padding: 0 0 5rem; }}
.na-page {{ width: min(100%, 1320px); margin: 0 auto; padding: 2rem 1.25rem; }}
.na-layout-marketing, .na-layout-immersive {{ width: min(100%, 1440px); }}
.na-layout-editorial {{ width: min(100%, 900px); }}
.na-layout-centered-auth {{
  width: min(100%, 980px);
  min-height: calc(100vh - 4rem);
  display: flex;
  flex-direction: column;
  justify-content: center;
}}
.na-section {{ margin-top: 1.25rem; }}
.na-copy {{ width: min(100%, 840px); }}
.na-panel,
.na-navbar,
.na-hero-grid,
.na-feature-item,
.na-stat-chip,
.na-split,
.na-cta,
.na-auth-shell,
.na-image-frame {{
  background: var(--na-surface);
  color: var(--na-surface-text);
  border: 1px solid var(--na-border);
  border-radius: var(--na-radius);
  box-shadow: var(--na-shadow);
}}
.na-panel,
.na-navbar,
.na-split,
.na-cta,
.na-auth-shell {{ padding: 1.5rem; }}
.na-heading,
.na-display,
.na-section-title,
.na-cta-title {{ margin: 0; color: var(--na-surface-text); }}
.na-heading {{ font-size: clamp(1.8rem, 4vw, 2.6rem); }}
.na-display {{
  font-size: clamp(2.8rem, 8vw, 5.5rem);
  line-height: 0.96;
  letter-spacing: -0.04em;
}}
.na-text,
.na-hero-description,
.na-section-description,
.na-cta-description,
.na-auth-footer,
.na-hero-metric-caption,
.na-stat-chip-caption {{
  margin: 0;
  color: var(--na-muted);
  line-height: 1.75;
}}
.na-btn,
.na-btn-secondary,
.na-inline-link,
.na-brand,
.na-nav-link {{ border: 0; background: none; cursor: pointer; }}
.na-btn,
.na-btn-secondary {{
  padding: 0.85rem 1.2rem;
  border-radius: 999px;
  font-weight: 700;
}}
.na-btn {{ background: linear-gradient(135deg, var(--na-primary), var(--na-secondary)); color: #fff; }}
.na-btn-secondary {{ background: var(--na-accent-soft); color: var(--na-surface-text); }}
.na-label {{
  display: block;
  margin-bottom: 0.4rem;
  color: var(--na-muted);
  font-size: 0.94rem;
}}
.na-field + .na-field {{ margin-top: 1rem; }}
.na-input {{
  width: 100%;
  padding: 0.9rem 1rem;
  border-radius: calc(var(--na-radius) - 6px);
  border: 1px solid var(--na-border);
  background: rgba(255,255,255,0.02);
  color: var(--na-surface-text);
}}
.na-form {{ display: flex; flex-direction: column; gap: 1rem; }}
.na-card-title, .na-feature-title {{ margin: 0; font-size: 1.1rem; font-weight: 800; }}
.na-stat-value, .na-stat-chip-value, .na-hero-metric-value {{
  font-size: clamp(1.8rem, 4vw, 2.8rem);
  font-weight: 900;
}}
.na-stat-label, .na-stat-chip-label, .na-hero-metric-label {{
  margin-top: 0.35rem;
  font-size: 0.92rem;
  color: var(--na-muted);
}}
.na-table-wrap {{ overflow: hidden; }}
.na-table {{ width: 100%; border-collapse: collapse; }}
.na-table th, .na-table td {{
  padding: 0.95rem 0.9rem;
  text-align: left;
  border-bottom: 1px solid var(--na-border);
}}
.na-empty-row {{ color: var(--na-muted); text-align: center; }}
.na-header-shell {{ position: sticky; top: 0; z-index: 20; padding: 1.25rem 1.25rem 0; }}
.na-header-backdrop {{
  position: absolute;
  inset: 0;
  border-radius: var(--na-radius);
  background: rgba(15, 23, 42, 0.02);
  backdrop-filter: blur(16px);
}}
.na-navbar {{
  position: relative;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
}}
.na-brand {{ font-size: 1rem; font-weight: 900; color: var(--na-surface-text); }}
.na-nav-links {{ display: flex; flex-wrap: wrap; gap: 0.75rem; }}
.na-nav-link {{
  padding: 0.55rem 0.9rem;
  border-radius: 999px;
  color: var(--na-muted);
}}
.na-nav-link.is-active {{ background: var(--na-accent-soft); color: var(--na-primary); }}
.na-tag,
.na-kicker {{
  display: inline-flex;
  align-items: center;
  width: fit-content;
  padding: 0.4rem 0.8rem;
  border-radius: 999px;
  background: var(--na-accent-soft);
  color: var(--na-primary);
  font-size: 0.78rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}}
.na-image-frame,
.na-hero-visual,
.na-split-visual,
.na-auth-visual {{ overflow: hidden; }}
.na-image-frame img,
.na-hero-visual img,
.na-split-visual img,
.na-auth-visual img {{ display: block; width: 100%; height: 100%; object-fit: cover; }}
.na-hero-grid,
.na-split,
.na-auth-shell {{ display: grid; gap: 1.5rem; }}
.na-hero-copy,
.na-split-copy,
.na-auth-body,
.na-copy-block {{ display: flex; flex-direction: column; gap: 1rem; }}
.na-actions {{ display: flex; flex-wrap: wrap; gap: 0.75rem; }}
.na-hero-metrics,
.na-feature-grid,
.na-stat-band {{ display: grid; gap: 1rem; }}
.na-hero-metric,
.na-stat-chip {{
  padding: 1rem;
  border-radius: calc(var(--na-radius) - 6px);
  background: var(--na-subtle);
}}
.na-feature-grid.na-cols-2 {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
.na-feature-grid.na-cols-3 {{ grid-template-columns: repeat(3, minmax(0, 1fr)); }}
.na-feature-grid.na-cols-4 {{ grid-template-columns: repeat(4, minmax(0, 1fr)); }}
.na-feature-item {{ padding: 1.25rem; }}
.na-feature-badge {{ font-size: 0.9rem; color: var(--na-primary); margin-bottom: 0.75rem; }}
.na-feature-description {{ margin: 0.7rem 0 0; color: var(--na-muted); line-height: 1.7; }}
.na-bullets {{
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 0.8rem;
}}
.na-bullets li {{
  display: flex;
  gap: 0.8rem;
  align-items: flex-start;
  line-height: 1.7;
}}
.na-bullets li::before {{
  content: "";
  width: 0.6rem;
  height: 0.6rem;
  margin-top: 0.5rem;
  border-radius: 999px;
  background: var(--na-primary);
  flex: none;
}}
.na-split.is-reverse {{ direction: rtl; }}
.na-split.is-reverse > * {{ direction: ltr; }}
.na-cta {{
  background: linear-gradient(160deg, rgba(15,23,42,0.96), rgba(30,41,59,0.95));
  color: #fff;
}}
.na-cta-title, .na-cta-description {{ color: #fff; }}
.na-cta-description {{ opacity: 0.78; }}
.na-auth-shell {{ align-items: stretch; }}
.na-auth-visual {{
  min-height: 280px;
  background: linear-gradient(145deg, rgba(15,23,42,0.96), rgba(30,41,59,0.95));
}}
.na-inline-link {{ padding: 0; color: var(--na-primary); font-weight: 800; }}
.na-toast {{
  position: fixed;
  right: 1.5rem;
  bottom: 1.5rem;
  padding: 0.85rem 1rem;
  border-radius: 14px;
  background: linear-gradient(135deg, var(--na-primary), var(--na-secondary));
  color: #fff;
  box-shadow: var(--na-shadow);
  z-index: 50;
}}
.na-preview-shell {{ min-height: 100vh; }}
.na-empty-state {{
  width: min(100%, 820px);
  margin: 4rem auto;
  padding: 2rem;
  border-radius: var(--na-radius);
  background: var(--na-surface);
  border: 1px solid var(--na-border);
  color: var(--na-muted);
  box-shadow: var(--na-shadow);
}}
@media (min-width: 900px) {{
  .na-hero-grid {{
    grid-template-columns: minmax(0, 1.05fr) minmax(420px, 0.95fr);
    align-items: center;
  }}
  .na-split,
  .na-auth-shell {{
    grid-template-columns: repeat(2, minmax(0, 1fr));
    align-items: center;
  }}
  .na-hero-metrics,
  .na-stat-band {{ grid-template-columns: repeat(4, minmax(0, 1fr)); }}
}}
@media (max-width: 899px) {{
  .na-feature-grid.na-cols-2,
  .na-feature-grid.na-cols-3,
  .na-feature-grid.na-cols-4 {{ grid-template-columns: 1fr; }}
  .na-page {{ padding: 1.25rem 1rem 3rem; }}
}}
"""


def _build_runtime_js() -> str:
    return """(() => {
  const dataNode = document.getElementById("na-site-data");
  if (!dataNode) return;

  let siteData = null;
  try {
    siteData = JSON.parse(dataNode.textContent || "{}");
  } catch (error) {
    console.error("Failed to parse site data", error);
    return;
  }

  const previewRoot = document.getElementById("na-preview-root");
  const routeMap = siteData.route_map || {};
  const pages = Array.isArray(siteData.pages) ? siteData.pages : [];
  let currentRoute = window.location.hash ? decodeURIComponent(window.location.hash.slice(1)) : (siteData.current_route || siteData.default_route || "/");
  let toastTimer = null;

  function showToast(message) {
    const existing = document.querySelector(".na-toast");
    if (existing) existing.remove();
    const toast = document.createElement("div");
    toast.className = "na-toast";
    toast.textContent = message;
    document.body.appendChild(toast);
    if (toastTimer) window.clearTimeout(toastTimer);
    toastTimer = window.setTimeout(() => toast.remove(), 2200);
  }

  function bindInteractions(scope) {
    scope.querySelectorAll("[data-route]").forEach((element) => {
      element.addEventListener("click", (event) => {
        event.preventDefault();
        const nextRoute = element.getAttribute("data-route");
        if (!nextRoute) return;
        if (siteData.preview) {
          currentRoute = nextRoute;
          window.location.hash = encodeURIComponent(nextRoute);
          renderPreview();
          return;
        }
        const target = routeMap[nextRoute];
        if (target) window.location.href = target;
      });
    });

    scope.querySelectorAll("[data-form-id]").forEach((form) => {
      form.addEventListener("submit", (event) => {
        event.preventDefault();
        showToast(siteData.submit_message || "Submitted successfully");
      });
    });
  }

  function executeInlineScripts(scope) {
    scope.querySelectorAll("script").forEach((oldScript) => {
      const nextScript = document.createElement("script");
      for (const attr of oldScript.attributes) {
        nextScript.setAttribute(attr.name, attr.value);
      }
      nextScript.textContent = oldScript.textContent || "";
      oldScript.replaceWith(nextScript);
    });
  }

  function renderPreview() {
    if (!previewRoot) return;
    const page = pages.find((item) => item.route === currentRoute) || pages[0];
    if (!page) {
      previewRoot.innerHTML = `<div class="na-empty-state">${siteData.empty_message || "No renderable page"}</div>`;
      return;
    }
    document.title = `${siteData.title || "Nano Atoms"} - ${page.name || page.route}`;
    previewRoot.innerHTML = `<div class="na-site-shell">${page.html || ""}</div>`;
    bindInteractions(previewRoot);
    executeInlineScripts(previewRoot);
  }

  if (siteData.preview) {
    renderPreview();
    window.addEventListener("hashchange", () => {
      currentRoute = window.location.hash ? decodeURIComponent(window.location.hash.slice(1)) : (siteData.default_route || "/");
      renderPreview();
    });
    return;
  }

  bindInteractions(document);
})();"""


def _build_metadata_js(app_schema: dict[str, Any], code_bundle: dict[str, Any], site_data: dict[str, Any]) -> str:
    site_meta = {
        "title": site_data.get("title"),
        "default_route": site_data.get("default_route"),
        "route_map": site_data.get("route_map"),
        "pages": [
            {
                "name": page.get("name"),
                "route": page.get("route"),
                "path": page.get("path"),
                "layout": page.get("layout"),
            }
            for page in site_data.get("pages", [])
            if isinstance(page, dict)
        ],
    }
    generation_metadata = {
        "app_id": app_schema.get("app_id"),
        "title": app_schema.get("title"),
        "app_type": app_schema.get("app_type"),
        "content_language": app_schema.get("content_language"),
        "layout_archetype": app_schema.get("layout_archetype"),
        "navigation": app_schema.get("navigation"),
        "design_brief": app_schema.get("design_brief"),
        "ui_theme": app_schema.get("ui_theme"),
    }
    return (
        f"export const generationMetadata = {_json_text(generation_metadata)};\\n\\n"
        f"export const codeBundle = {_json_text(code_bundle)};\\n\\n"
        f"export const siteMeta = {_json_text(site_meta)};\\n"
    )


def _build_page_boot_data(
    title: str,
    language: str,
    current_route: str,
    default_route: str,
    route_map: dict[str, str],
) -> dict[str, Any]:
    return {
        "preview": False,
        "title": title,
        "language": language,
        "current_route": current_route,
        "default_route": default_route,
        "route_map": route_map,
        "submit_message": _localized(language, "提交成功", "Submitted successfully"),
    }


def _build_page_snapshot_html(
    *,
    title: str,
    language: str,
    page_markup: str,
    route_map: dict[str, str],
    default_route: str,
    current_route: str,
    styles_href: str,
    script_src: str,
) -> str:
    boot_data = _build_page_boot_data(
        title=title,
        language=language,
        current_route=current_route,
        default_route=default_route,
        route_map=route_map,
    )
    return f"""<!doctype html>
<html lang="{_escape_attr(language)}">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{_escape_text(title)}</title>
    <link rel="stylesheet" href="{_escape_attr(styles_href)}" />
  </head>
  <body>
    <div class="na-site-shell">
      {page_markup}
    </div>
    <script id="na-site-data" type="application/json">{_json_script(boot_data)}</script>
    <script type="module" src="{_escape_attr(script_src)}"></script>
  </body>
</html>
"""


def _build_index_html(
    title: str,
    language: str,
    page_markup: str,
    route_map: dict[str, str],
    default_route: str,
    current_route: str,
) -> str:
    return _build_page_snapshot_html(
        title=title,
        language=language,
        page_markup=page_markup,
        route_map=route_map,
        default_route=default_route,
        current_route=current_route,
        styles_href="./src/styles.css",
        script_src="./src/app.js",
    )


def _load_nano_ui() -> str:
    """Load Nano UI component library."""
    try:
        return NANO_UI_PATH.read_text(encoding="utf-8")
    except Exception:
        return ""


def _build_import_map() -> str:
    """Build import map for CDN dependencies."""
    return """{
  "imports": {
    "vue": "https://unpkg.com/vue@3.4.21/dist/vue.esm-browser.js",
    "tailwindcss": "https://cdn.jsdelivr.net/npm/tailwindcss@3.4.1/lib/index.js"
  }
}"""


def _build_preview_html(
    title: str,
    language: str,
    styles_css: str,
    runtime_js: str,
    site_data: dict[str, Any],
) -> str:
    preview_payload = {
        "preview": True,
        "title": title,
        "language": language,
        "current_route": site_data.get("default_route") or "/",
        "default_route": site_data.get("default_route") or "/",
        "route_map": site_data.get("route_map") or {},
        "pages": site_data.get("pages") or [],
        "submit_message": _localized(language, "提交成功", "Submitted successfully"),
        "empty_message": _localized(language, "当前没有可渲染页面", "No renderable page"),
    }
    nano_ui_js = _load_nano_ui()
    import_map = _build_import_map()

    return f"""<!doctype html>
<html lang="{_escape_attr(language)}">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{_escape_text(title)}</title>
    <style>{styles_css}</style>
    <script type="importmap">{import_map}</script>
  </head>
  <body>
    <div id="na-preview-root" class="na-preview-shell"></div>
    <script id="na-site-data" type="application/json">{_json_script(preview_payload)}</script>
    <script>{nano_ui_js}</script>
    <script type="module">
      // Expose NanoUI globally
      window.NanoUI = window.NanoUI || {{}};
    </script>
    <script>{runtime_js}</script>
  </body>
</html>
"""


def _build_readme(title: str, prompt: str, pages: list[dict[str, Any]]) -> str:
    page_lines = "\\n".join(
        f"- `{page.get('route')}` -> `{page.get('path')}`"
        for page in pages
        if isinstance(page, dict)
    )
    return f"""# {title}

This folder is a static multi-page export generated by Nano Atoms.

## Structure

- `index.html`: entry page for the generated site
- `pages/*.html`: additional generated pages
- `src/styles.css`: shared site styling
- `src/app.js`: lightweight runtime for navigation and form feedback
- `src/metadata.js`: exported generation metadata and interaction bundle
- `data/generation-metadata.json`: persisted generation metadata snapshot
- `data/code-bundle.json`: bindings and transitions
- `data/site-pages.json`: pre-rendered page snapshots used by preview mode

## Generated Routes

{page_lines or "- `/` -> `index.html`"}

## Original Prompt

{prompt}
"""


def _build_freeform_pending_markup(title: str, page_name: str, language: str) -> str:
    eyebrow = _localized(language, "应用内容仍在完善中", "Application content is still being completed")
    heading = page_name.strip() or title.strip() or _localized(language, "页面", "Page")
    description = _localized(
        language,
        "当前版本暂未完成可预览内容生成。请稍后刷新，或继续发起一次迭代。",
        "This page has not finished generating yet. Refresh later or run another iteration to fill it in.",
    )
    return (
        '<main class="na-page na-freeform-shell">'
        '<section class="na-section na-panel">'
        f'<p class="na-eyebrow">{_escape_text(eyebrow)}</p>'
        f'<h1 class="na-heading">{_escape_text(heading)}</h1>'
        f'<p class="na-text">{_escape_text(description)}</p>'
        "</section>"
        "</main>"
    )


def build_project_artifact(
    prompt: str,
    app_schema: dict[str, Any],
    code_bundle: dict[str, Any],
    freeform_site: dict[str, Any] | None = None,
) -> dict[str, Any]:
    title = str(app_schema.get("title") or "Nano Atoms App")
    package_name = _slugify(title)
    language = _content_language(app_schema)
    pages = app_schema.get("pages") if isinstance(app_schema.get("pages"), list) else []
    runtime_js = _build_runtime_js()
    styles_css = _build_styles_css(app_schema)
    freeform_site = freeform_site if isinstance(freeform_site, dict) else {}
    freeform_css = str(freeform_site.get("global_css") or "").strip()
    freeform_runtime = str(freeform_site.get("runtime_js") or "").strip()
    freeform_pages_raw = freeform_site.get("pages") if isinstance(freeform_site.get("pages"), list) else []
    freeform_pages: dict[str, dict[str, Any]] = {}
    for item in freeform_pages_raw:
        if not isinstance(item, dict):
            continue
        route = _nav_target(str(item.get("route") or "/"))
        freeform_pages[route] = item
    if not freeform_pages:
        raise ValueError("No generated page code was provided for export")
    if freeform_css:
        styles_css = f"{styles_css}\n\n/* Freeform site codegen overrides */\n{freeform_css}\n"
    if freeform_runtime:
        runtime_js = (
            f"{runtime_js}\n\ntry {{\n{freeform_runtime}\n}} "
            'catch (error) { console.error("freeform site enhancement failed", error); }\n'
        )

    rendered_pages: list[dict[str, Any]] = []
    route_map: dict[str, str] = {}
    for index, page in enumerate(page for page in pages if isinstance(page, dict)):
        route = _nav_target(str(page.get("route") or "/"))
        file_path = "index.html" if route == "/" else f"pages/{_page_file_name(route, index)}"
        route_map[route] = file_path
        freeform_page = freeform_pages.get(route) or {}
        rendered_html = _sanitize_freeform_markup(freeform_page.get("body_html") or "").strip()
        if not rendered_html:
            raise ValueError(f"Missing generated page body for route {route}")
        rendered_pages.append(
            {
                "id": str(page.get("id") or f"page-{index + 1}"),
                "name": str(freeform_page.get("title") or page.get("name") or f"Page {index + 1}"),
                "route": route,
                "path": file_path,
                "layout": _infer_layout_archetype(app_schema, page),
                "html": rendered_html,
            }
        )

    if not rendered_pages:
        raise ValueError("No generated pages were rendered for export")

    default_route = rendered_pages[0]["route"]
    site_data = {
        "title": title,
        "language": language,
        "default_route": default_route,
        "route_map": route_map,
        "pages": rendered_pages,
    }

    files: list[dict[str, Any]] = [
        {"path": "README.md", "language": "markdown", "content": _build_readme(title, prompt, rendered_pages)},
        {"path": "src/styles.css", "language": "css", "content": styles_css},
        {"path": "src/app.js", "language": "javascript", "content": runtime_js},
        {
            "path": "src/metadata.js",
            "language": "javascript",
            "content": _build_metadata_js(app_schema, code_bundle, site_data),
        },
        {"path": "data/generation-metadata.json", "language": "json", "content": _json_text({
            "app_id": app_schema.get("app_id"),
            "title": app_schema.get("title"),
            "app_type": app_schema.get("app_type"),
            "content_language": app_schema.get("content_language"),
            "layout_archetype": app_schema.get("layout_archetype"),
            "navigation": app_schema.get("navigation"),
            "design_brief": app_schema.get("design_brief"),
            "site_plan": app_schema.get("site_plan"),
            "ui_theme": app_schema.get("ui_theme"),
            "quality_report": app_schema.get("quality_report"),
        })},
        {"path": "data/code-bundle.json", "language": "json", "content": _json_text(code_bundle)},
        {"path": "data/site-pages.json", "language": "json", "content": _json_text(site_data)},
    ]
    if freeform_site:
        files.append({"path": "data/freeform-site.json", "language": "json", "content": _json_text(freeform_site)})

    for page in rendered_pages:
        path = page["path"]
        if path == "index.html":
            files.append(
                {
                    "path": path,
                    "language": "html",
                    "content": _build_index_html(
                        title=title,
                        language=language,
                        page_markup=page["html"],
                        route_map=route_map,
                        default_route=default_route,
                        current_route=page["route"],
                    ),
                }
            )
        else:
            files.append(
                {
                    "path": path,
                    "language": "html",
                    "content": _build_page_snapshot_html(
                        title=title,
                        language=language,
                        page_markup=page["html"],
                        route_map=route_map,
                        default_route=default_route,
                        current_route=page["route"],
                        styles_href="../src/styles.css",
                        script_src="../src/app.js",
                    ),
                }
            )

    preview_html = _build_preview_html(
        title=title,
        language=language,
        styles_css=styles_css,
        runtime_js=runtime_js,
        site_data=site_data,
    )

    return {
        "format": "site_files_v3",
        "title": title,
        "package_name": package_name,
        "entry": "index.html",
        "code_bundle": code_bundle,
        "files": [{**file, "language": file.get("language") or _infer_language(file["path"])} for file in files],
        "preview_html": preview_html,
    }
