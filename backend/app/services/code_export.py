"""Build a human-readable static project export from schema + code bundle."""

from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import quote


def _slugify(value: str) -> str:
    text = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower())
    return text.strip("-") or "nano-atoms-app"


def _json_text(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


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
    raw_value = str((page or {}).get("layout_archetype") or app_schema.get("layout_archetype") or "").strip().lower()
    if raw_value in {"marketing", "editorial", "dashboard", "centered-auth", "workspace", "immersive"}:
        return raw_value

    design_brief = app_schema.get("design_brief") if isinstance(app_schema.get("design_brief"), dict) else {}
    brief_layout = str(design_brief.get("layout_archetype") or "").strip().lower()
    if brief_layout in {"marketing", "editorial", "dashboard", "centered-auth", "workspace", "immersive"}:
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
  <text x="600" y="592" text-anchor="middle" fill="#2D4C7C" font-size="36" font-family="Arial, sans-serif">{safe_label}</text>
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


def _build_index_html(title: str) -> str:
    return f"""<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{title}</title>
    <link rel="stylesheet" href="./src/styles.css" />
  </head>
  <body>
    <div id="app"></div>
    <script type="module" src="./src/app.js"></script>
  </body>
</html>
"""


def _build_schema_js(app_schema: dict[str, Any], code_bundle: dict[str, Any]) -> str:
    return (
        f"export const appSchema = {_json_text(app_schema)};\n\n"
        f"export const codeBundle = {_json_text(code_bundle)};\n"
    )


def _build_styles_css(app_schema: dict[str, Any]) -> str:
    theme = app_schema.get("ui_theme") or {}
    mode = _infer_theme_mode(theme)
    layout = _infer_layout_archetype(app_schema)
    primary = theme.get("primary_color", "#4f46e5")
    secondary = theme.get("secondary_color", "#c7d2fe")
    background = theme.get("background_color", "#020617" if mode == "dark" else "#ffffff")
    text = theme.get("text_color", "#f8fafc" if mode == "dark" else "#0f172a")
    surface = theme.get("surface_color", "rgba(15,23,42,0.78)" if mode == "dark" else "rgba(255,255,255,0.92)")
    surface_text = theme.get("surface_text_color", "#f8fafc" if mode == "dark" else text)
    border = theme.get("border_color", "rgba(148,163,184,0.18)" if mode == "dark" else "#dbe3f0")
    muted = theme.get("muted_text_color", "rgba(226,232,240,0.72)" if mode == "dark" else "#64748b")
    input_background = theme.get("input_background", "rgba(15,23,42,0.92)" if mode == "dark" else "#ffffff")
    subtle_surface = theme.get("subtle_surface_color", "rgba(30,41,59,0.7)" if mode == "dark" else "rgba(248,250,252,.86)")
    page_background = theme.get(
        "page_background",
        f"radial-gradient(circle at top, #0f172a 0%, {background} 36%, #020617 100%)"
        if mode == "dark"
        else f"radial-gradient(circle at top, #eef4ff 0%, {background} 34%, #ffffff 100%)",
    )
    button_text = theme.get("button_text_color", "#f8fafc" if mode == "dark" else "#ffffff")
    radius = theme.get("border_radius", "16px")
    font_family = theme.get("font_family", '"Segoe UI", "PingFang SC", system-ui, sans-serif')
    layout_widths = {
        "marketing": ("1180px", "780px", "1080px"),
        "editorial": ("960px", "760px", "980px"),
        "dashboard": ("1320px", "860px", "1040px"),
        "centered-auth": ("960px", "700px", "920px"),
        "immersive": ("1480px", "860px", "1120px"),
        "workspace": ("1380px", "860px", "1080px"),
    }
    shell_width, reading_width, auth_width = layout_widths.get(layout, layout_widths["workspace"])
    return f""":root {{
  --color-primary: {primary};
  --color-secondary: {secondary};
  --color-surface: {surface};
  --color-page: {background};
  --color-border: {border};
  --color-muted: {muted};
  --color-text: {text};
  --color-surface-text: {surface_text};
  --color-input-bg: {input_background};
  --color-subtle-surface: {subtle_surface};
  --color-button-text: {button_text};
  --color-accent-soft: {_hex_to_rgba(primary, 0.22 if mode == "dark" else 0.12, "rgba(79,70,229,0.12)")};
  --color-secondary-soft: {_hex_to_rgba(secondary, 0.24 if mode == "dark" else 0.14, "rgba(199,210,254,0.14)")};
  --radius: {radius};
  --shadow: {"0 24px 64px rgba(2,6,23,0.44)" if mode == "dark" else "0 24px 60px rgba(15,23,42,0.12)"};
  --font-sans: {font_family};
  --shell-width: {shell_width};
  --reading-width: {reading_width};
  --auth-width: {auth_width};
}}
* {{ box-sizing: border-box; }}
body {{ margin: 0; font-family: var(--font-sans); background: {page_background}; color: var(--color-text); }}
#app {{ min-height: 100vh; }}
.app-shell {{ min-height: 100vh; }}
.app-shell.layout-dashboard,.app-shell.layout-workspace {{ padding: 32px 24px 80px; }}
.app-shell.layout-editorial {{ padding: 40px 24px 88px; }}
.app-shell.layout-marketing,.app-shell.layout-immersive {{ padding: 0 0 80px; }}
.app-shell.layout-centered-auth {{ min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 32px 24px 80px; }}
.page {{ width: 100%; display: flex; flex-direction: column; gap: 24px; }}
.page.layout-dashboard,.page.layout-workspace {{ max-width: var(--shell-width); margin: 0 auto; }}
.page.layout-editorial {{ max-width: var(--reading-width); margin: 0 auto; }}
.page.layout-centered-auth {{ max-width: var(--auth-width); margin: 0 auto; }}
.page.layout-marketing,.page.layout-immersive {{ max-width: none; margin: 0; }}
.stack,.form,.hero-copy,.split-copy,.auth-body {{ display: flex; flex-direction: column; gap: 14px; }}
.heading {{ margin: 0; font-size: 2rem; line-height: 1.2; color: var(--color-surface-text); }}
.text {{ margin: 0; color: var(--color-muted); line-height: 1.7; }}
.button,.button-primary {{ appearance: none; border: 0; background: linear-gradient(135deg, var(--color-primary), var(--color-secondary)); color: var(--color-button-text); border-radius: 999px; padding: 12px 18px; font: inherit; cursor: pointer; }}
.button-secondary {{ appearance: none; border: 1px solid var(--color-border); background: { "rgba(255,255,255,0.04)" if mode == "dark" else "var(--color-surface)" }; color: var(--color-surface-text); border-radius: 999px; padding: 12px 18px; font: inherit; cursor: pointer; }}
.field-label {{ font-size: .95rem; color: var(--color-muted); }}
.input,.select {{ width: 100%; border: 1px solid var(--color-border); border-radius: var(--radius); padding: 12px 14px; font: inherit; color: var(--color-surface-text); background: var(--color-input-bg); }}
.card,.stat-card,.table-wrap,.navbar,.hero-card,.feature-card,.stats-card-wrap,.split-card,.cta-card,.auth-card-frame {{ background: var(--color-surface); border: 1px solid var(--color-border); border-radius: calc(var(--radius) + 10px); box-shadow: var(--shadow); }}
.card,.stat-card,.table-wrap,.navbar,.feature-card,.stats-card-wrap,.split-card,.cta-card {{ padding: 24px; }}
.navbar,.hero-card,.feature-card,.stats-card-wrap,.split-card,.cta-card {{ width: min(100%, var(--shell-width)); margin: 0 auto; }}
.auth-card-frame {{ width: min(100%, var(--auth-width)); margin: 0 auto; }}
.navbar {{ display: flex; align-items: center; justify-content: space-between; gap: 16px; }}
.navbar-links {{ display: flex; gap: 12px; flex-wrap: wrap; }}
.navbar-link {{ color: var(--color-muted); text-decoration: none; }}
.tag {{ display: inline-flex; align-items: center; padding: 6px 10px; border-radius: 999px; background: var(--color-accent-soft); color: var(--color-primary); font-size: .85rem; }}
.table {{ width: 100%; border-collapse: collapse; }}
.table th,.table td {{ border-bottom: 1px solid var(--color-border); padding: 12px 10px; text-align: left; }}
.hero-card,.split-grid,.auth-grid {{ display: grid; gap: 28px; }}
.hero-eyebrow,.section-eyebrow {{ display: inline-flex; width: fit-content; padding: 6px 12px; border-radius: 999px; background: var(--color-secondary-soft); color: var(--color-primary); font-size: 12px; font-weight: 700; letter-spacing: .16em; text-transform: uppercase; }}
.hero-title,.section-title,.cta-title,.auth-title {{ margin: 0; font-weight: 900; line-height: 1.05; }}
.hero-title {{ font-size: clamp(2.8rem,5vw,4.5rem); }}
.section-title,.auth-title,.cta-title {{ font-size: clamp(2rem,4vw,3rem); color: var(--color-surface-text); }}
.hero-description,.section-description,.cta-description,.auth-description {{ margin: 0; line-height: 1.75; color: var(--color-muted); }}
.hero-actions,.section-actions,.cta-actions {{ display: flex; flex-wrap: wrap; gap: 12px; margin-top: 12px; }}
.hero-visual,.split-visual,.auth-visual {{ overflow: hidden; border-radius: calc(var(--radius) + 8px); background: var(--color-subtle-surface); }}
.hero-visual img,.split-visual img,.auth-visual img,.image {{ display: block; width: 100%; height: 100%; object-fit: cover; }}
.hero-stats,.stats-grid,.feature-grid-items {{ display: grid; gap: 12px; }}
.hero-stats,.stats-grid {{ grid-template-columns: repeat(2,minmax(0,1fr)); }}
.hero-stat,.stats-card {{ border: 1px solid var(--color-border); border-radius: calc(var(--radius) + 4px); background: var(--color-subtle-surface); padding: 16px; }}
.feature-item {{ border: 1px solid var(--color-border); border-radius: calc(var(--radius) + 4px); background: var(--color-subtle-surface); padding: 18px; }}
.feature-item-title {{ margin: 0; font-size: 1.05rem; font-weight: 800; }}
.feature-item-description {{ margin: 10px 0 0; color: var(--color-muted); line-height: 1.65; }}
.split-bullets {{ margin: 12px 0 0; padding: 0; list-style: none; }}
.split-bullets li {{ display: flex; gap: 12px; align-items: flex-start; margin-top: 10px; line-height: 1.7; }}
.split-bullets li::before {{ content: ""; width: 10px; height: 10px; border-radius: 999px; background: var(--color-primary); margin-top: 9px; flex: none; }}
.cta-card {{ background: #0f172a; color: white; }}
.cta-description {{ color: rgba(255,255,255,.74); }}
.auth-card-frame {{ overflow: hidden; }}
.auth-visual {{ min-height: 280px; background: #0f172a; }}
.auth-body {{ padding: 24px; }}
.auth-footer {{ margin-top: 16px; color: var(--color-muted); }}
.auth-link {{ border: 0; background: transparent; color: var(--color-primary); font: inherit; font-weight: 700; cursor: pointer; }}
.pager {{ position: fixed; bottom: 24px; left: 50%; transform: translateX(-50%); display: flex; gap: 8px; background: var(--color-surface); border: 1px solid var(--color-border); border-radius: 999px; padding: 8px 10px; box-shadow: var(--shadow); }}
.pager-dot {{ width: 10px; height: 10px; border: 0; border-radius: 999px; background: #cbd5e1; cursor: pointer; }}
.pager-dot.is-active {{ width: 28px; background: linear-gradient(135deg, var(--color-primary), var(--color-secondary)); }}
.toast {{ position: fixed; right: 24px; bottom: 24px; padding: 12px 16px; background: #16a34a; color: #fff; border-radius: 14px; box-shadow: var(--shadow); }}
.modal {{ position: fixed; inset: 0; background: rgba(15,23,42,.42); display: flex; align-items: center; justify-content: center; padding: 24px; }}
.modal-card {{ width: min(560px,100%); background: var(--color-surface); border-radius: calc(var(--radius) + 8px); padding: 24px; box-shadow: var(--shadow); }}
.empty-state {{ max-width: 720px; margin: 64px auto; background: var(--color-surface); border: 1px dashed var(--color-border); border-radius: calc(var(--radius) + 8px); padding: 32px; text-align: center; color: var(--color-muted); }}
@media (min-width: 768px) {{
  .hero-card {{ grid-template-columns: 1.05fr .95fr; }}
  .split-grid {{ grid-template-columns: repeat(2,minmax(0,1fr)); align-items: center; }}
  .auth-grid {{ grid-template-columns: .92fr 1.08fr; }}
  .feature-grid-items.cols-2 {{ grid-template-columns: repeat(2,minmax(0,1fr)); }}
  .feature-grid-items.cols-3 {{ grid-template-columns: repeat(3,minmax(0,1fr)); }}
  .feature-grid-items.cols-4 {{ grid-template-columns: repeat(4,minmax(0,1fr)); }}
  .hero-stats,.stats-grid {{ grid-template-columns: repeat(4,minmax(0,1fr)); }}
}}
"""


def _build_app_js() -> str:
    return """import { appSchema, codeBundle } from "./schema.js";

const root = document.getElementById("app");
const state = { ...(codeBundle.initial_state || {}) };
const formData = {};
const modalState = {};
let currentRoute = appSchema.pages?.[0]?.route || "/";
let toastTimer = null;
const fallbackImage = "__IMAGE_PLACEHOLDER__";

function getCurrentPage(){ return appSchema.pages.find((page) => page.route === currentRoute) || appSchema.pages?.[0]; }
function normalizeLayoutArchetype(value, fallback = "workspace"){ const text = String(value || "").trim().toLowerCase(); return ["marketing","editorial","dashboard","centered-auth","workspace","immersive"].includes(text) ? text : fallback; }
function getLayoutArchetype(page){ return normalizeLayoutArchetype(page?.layout_archetype || appSchema.layout_archetype || appSchema.design_brief?.layout_archetype || appSchema.app_type, "workspace"); }
function getText(node, fallback = ""){ return String(node?.props?.text ?? node?.props?.children ?? node?.props?.label ?? fallback); }
function getFormId(node, parentFormId){ return node?.props?.form_id || parentFormId || node?.id; }
function getStringArray(value){ if(Array.isArray(value)) return value.map((item) => String(item)); if(typeof value === "string" && value.trim()) return value.split(/[,\n|/]+/).map((item) => item.trim()).filter(Boolean); return []; }
function getFeatureItems(value){ if(!Array.isArray(value)) return []; return value.map((item, index) => typeof item === "string" ? { title: item, description: "" } : { title: String(item?.title || item?.label || `Feature ${index + 1}`), description: String(item?.description || item?.text || ""), badge: String(item?.badge || ""), icon: String(item?.icon || "") }); }
function getStatItems(value){ if(!Array.isArray(value)) return []; return value.filter((item) => item && typeof item === "object").map((item, index) => ({ label: String(item?.label || `Metric ${index + 1}`), value: String(item?.value || item?.number || "--"), caption: String(item?.caption || item?.change || "") })); }
function getImageSrc(value){ return typeof value === "string" && value.trim() ? value.trim() : fallbackImage; }
function showToast(message){ const existing = document.querySelector(".toast"); if(existing) existing.remove(); const toast = document.createElement("div"); toast.className = "toast"; toast.textContent = message; document.body.appendChild(toast); clearTimeout(toastTimer); toastTimer = setTimeout(() => toast.remove(), 2200); }
function followTransitions(triggerId){ const next = codeBundle.page_transitions?.find((item) => item.trigger_component === triggerId); if(next){ const target = appSchema.pages.find((page) => page.id === next.to_page); if(target){ currentRoute = target.route; render(); } } }
function submitForm(formId){ const handler = codeBundle.form_handlers?.find((item) => item.form_id === formId); showToast(handler?.submit_action === "save_local" ? "Form saved" : "Form submitted"); followTransitions(formId); }
function handleAction(action, fallbackId){ if(!action) return; if(action.type === "navigate" && action.payload?.route){ currentRoute = action.payload.route; render(); return; } if(action.type === "submit_form"){ submitForm(action.payload?.form_id || fallbackId); return; } if(action.type === "set_value" && action.payload?.key){ state[action.payload.key] = action.payload.value; render(); return; } if(action.type === "open_modal"){ modalState[action.payload?.modal_id || fallbackId] = true; render(); return; } if(action.type === "close_modal"){ modalState[action.payload?.modal_id || fallbackId] = false; render(); } }
function createButton(label, route, className = "button-primary"){ const button = document.createElement("button"); button.className = className; button.type = "button"; button.textContent = String(label || "Continue"); button.addEventListener("click", () => { if(route){ currentRoute = String(route); render(); } }); return button; }
function createFieldWrapper(labelText){ const wrapper = document.createElement("div"); wrapper.className = "field"; if(labelText){ const label = document.createElement("label"); label.className = "field-label"; label.textContent = labelText; wrapper.appendChild(label); } return wrapper; }

function renderNode(node, parentFormId){
  switch(node.type){
    case "heading": { const el = document.createElement("h2"); el.className = "heading"; el.textContent = getText(node, "Heading"); return el; }
    case "text": { const el = document.createElement("p"); el.className = "text"; el.textContent = getText(node); return el; }
    case "button": { const button = document.createElement("button"); button.className = "button"; button.type = "button"; button.textContent = getText(node, "Button"); button.addEventListener("click", () => (node.actions || []).forEach((action) => handleAction(action, parentFormId || node.id))); return button; }
    case "input": { const formId = getFormId(node, parentFormId); const fieldName = node.props?.name || node.id; const wrapper = createFieldWrapper(node.props?.label); const input = document.createElement("input"); input.className = "input"; input.type = String(node.props?.type || "text"); input.placeholder = String(node.props?.placeholder || ""); input.value = formData[formId]?.[fieldName] || ""; input.addEventListener("input", (event) => { formData[formId] = formData[formId] || {}; formData[formId][fieldName] = event.target.value; }); wrapper.appendChild(input); return wrapper; }
    case "select": { const formId = getFormId(node, parentFormId); const fieldName = node.props?.name || node.id; const wrapper = createFieldWrapper(node.props?.label); const select = document.createElement("select"); select.className = "select"; const placeholder = document.createElement("option"); placeholder.value = ""; placeholder.textContent = "Select"; select.appendChild(placeholder); (Array.isArray(node.props?.options) ? node.props.options : []).forEach((value) => { const option = document.createElement("option"); option.value = String(value); option.textContent = String(value); select.appendChild(option); }); select.value = formData[formId]?.[fieldName] || ""; select.addEventListener("change", (event) => { formData[formId] = formData[formId] || {}; formData[formId][fieldName] = event.target.value; }); wrapper.appendChild(select); return wrapper; }
    case "form": { const form = document.createElement("form"); form.className = "form"; form.addEventListener("submit", (event) => { event.preventDefault(); submitForm(node.id); }); (node.children || []).forEach((child) => form.appendChild(renderNode(child, node.id))); return form; }
    case "card": { const card = document.createElement("section"); card.className = "card stack"; if(node.props?.title){ const title = document.createElement("h3"); title.className = "card-title"; title.textContent = String(node.props.title); card.appendChild(title); } if(Array.isArray(node.children) && node.children.length){ node.children.forEach((child) => card.appendChild(renderNode(child, parentFormId))); } else if(node.props?.content){ const text = document.createElement("p"); text.className = "text"; text.textContent = String(node.props.content); card.appendChild(text); } return card; }
    case "stat-card": { const card = document.createElement("section"); card.className = "stat-card"; card.innerHTML = `<p class="stat-label">${String(node.props?.label || "Metric")}</p><p class="stat-value">${String(node.props?.value || "0")}</p>${node.props?.change ? `<p class="stat-change">${String(node.props.change)}</p>` : ""}`; return card; }
    case "table": { const wrap = document.createElement("div"); wrap.className = "table-wrap"; const table = document.createElement("table"); table.className = "table"; const columns = Array.isArray(node.props?.columns) ? node.props.columns : []; const rows = Array.isArray(node.props?.rows) ? node.props.rows : []; table.innerHTML = `<thead><tr>${columns.map((column) => `<th>${String(column)}</th>`).join("")}</tr></thead><tbody>${rows.map((row) => `<tr>${columns.map((column) => `<td>${String(row?.[column] ?? "")}</td>`).join("")}</tr>`).join("")}</tbody>`; wrap.appendChild(table); return wrap; }
    case "navbar": { const nav = document.createElement("nav"); nav.className = "navbar"; const title = document.createElement("strong"); title.textContent = String(node.props?.title || appSchema.title || "App"); nav.appendChild(title); const links = document.createElement("div"); links.className = "navbar-links"; (Array.isArray(node.props?.links) ? node.props.links : []).forEach((item) => { const link = document.createElement("a"); link.className = "navbar-link"; link.href = "#"; link.textContent = String(item?.label || item?.text || "Link"); link.addEventListener("click", (event) => { event.preventDefault(); if(item?.route){ currentRoute = item.route; render(); } }); links.appendChild(link); }); nav.appendChild(links); return nav; }
    case "tag": { const tag = document.createElement("span"); tag.className = "tag"; tag.textContent = getText(node, "Tag"); return tag; }
    case "image": { const image = document.createElement("img"); image.className = "image"; image.src = String(node.props?.src || fallbackImage); image.alt = String(node.props?.alt || getText(node, "image")); image.addEventListener("error", () => { image.src = fallbackImage; }); return image; }
    case "hero": { const section = document.createElement("section"); section.className = "hero"; const card = document.createElement("div"); card.className = "hero-card"; const copy = document.createElement("div"); copy.className = "hero-copy"; if(node.props?.eyebrow){ const eyebrow = document.createElement("div"); eyebrow.className = "hero-eyebrow"; eyebrow.textContent = String(node.props.eyebrow); copy.appendChild(eyebrow); } const title = document.createElement("h1"); title.className = "hero-title"; title.textContent = String(node.props?.title || "Hero title"); copy.appendChild(title); if(node.props?.description){ const desc = document.createElement("p"); desc.className = "hero-description"; desc.textContent = String(node.props.description); copy.appendChild(desc); } const actions = document.createElement("div"); actions.className = "hero-actions"; if(node.props?.primary_cta_label) actions.appendChild(createButton(node.props.primary_cta_label, node.props.primary_cta_route, "button-primary")); if(node.props?.secondary_cta_label) actions.appendChild(createButton(node.props.secondary_cta_label, node.props.secondary_cta_route, "button-secondary")); if(actions.children.length) copy.appendChild(actions); const stats = getStatItems(node.props?.stats); if(stats.length){ const statsWrap = document.createElement("div"); statsWrap.className = "hero-stats"; stats.forEach((item) => { const stat = document.createElement("div"); stat.className = "hero-stat"; stat.innerHTML = `<div class="hero-stat-value">${item.value}</div><div class="hero-stat-label">${item.label}</div>${item.caption ? `<div class="hero-stat-caption">${item.caption}</div>` : ""}`; statsWrap.appendChild(stat); }); copy.appendChild(statsWrap); } const visual = document.createElement("div"); visual.className = "hero-visual"; const image = document.createElement("img"); image.src = getImageSrc(node.props?.image_src); image.alt = String(node.props?.image_alt || ""); image.addEventListener("error", () => { image.src = fallbackImage; }); visual.appendChild(image); card.append(copy, visual); section.appendChild(card); return section; }
    case "feature-grid": { const section = document.createElement("section"); section.className = "feature-grid"; const card = document.createElement("div"); card.className = "feature-card"; if(node.props?.title){ const title = document.createElement("h2"); title.className = "section-title"; title.textContent = String(node.props.title); card.appendChild(title); } if(node.props?.description){ const desc = document.createElement("p"); desc.className = "section-description"; desc.textContent = String(node.props.description); card.appendChild(desc); } const itemsWrap = document.createElement("div"); const columns = Math.max(2, Math.min(Number(node.props?.columns || 3), 4)); itemsWrap.className = `feature-grid-items cols-${columns}`; getFeatureItems(node.props?.items).forEach((item) => { const feature = document.createElement("article"); feature.className = "feature-item"; feature.innerHTML = `<h3 class="feature-item-title">${item.title}</h3>${item.description ? `<p class="feature-item-description">${item.description}</p>` : ""}`; itemsWrap.appendChild(feature); }); card.appendChild(itemsWrap); section.appendChild(card); return section; }
    case "stats-band": { const section = document.createElement("section"); section.className = "stats-band"; const card = document.createElement("div"); card.className = "stats-card-wrap"; const grid = document.createElement("div"); grid.className = "stats-grid"; getStatItems(node.props?.items).forEach((item) => { const stat = document.createElement("div"); stat.className = "stats-card"; stat.innerHTML = `<div class="stats-value">${item.value}</div><div class="stats-label">${item.label}</div>${item.caption ? `<div class="stats-caption">${item.caption}</div>` : ""}`; grid.appendChild(stat); }); card.appendChild(grid); section.appendChild(card); return section; }
    case "split-section": { const section = document.createElement("section"); section.className = "split-section"; const card = document.createElement("div"); card.className = "split-card"; const grid = document.createElement("div"); grid.className = "split-grid"; const copy = document.createElement("div"); copy.className = "split-copy"; if(node.props?.eyebrow){ const eyebrow = document.createElement("div"); eyebrow.className = "section-eyebrow"; eyebrow.textContent = String(node.props.eyebrow); copy.appendChild(eyebrow); } const title = document.createElement("h2"); title.className = "section-title"; title.textContent = String(node.props?.title || "Section title"); copy.appendChild(title); if(node.props?.description){ const desc = document.createElement("p"); desc.className = "section-description"; desc.textContent = String(node.props.description); copy.appendChild(desc); } const bullets = getStringArray(node.props?.bullets); if(bullets.length){ const list = document.createElement("ul"); list.className = "split-bullets"; bullets.forEach((item) => { const li = document.createElement("li"); li.textContent = item; list.appendChild(li); }); copy.appendChild(list); } const actions = document.createElement("div"); actions.className = "section-actions"; if(node.props?.primary_cta_label) actions.appendChild(createButton(node.props.primary_cta_label, node.props.primary_cta_route, "button-primary")); if(node.props?.secondary_cta_label) actions.appendChild(createButton(node.props.secondary_cta_label, node.props.secondary_cta_route, "button-secondary")); if(actions.children.length) copy.appendChild(actions); const visual = document.createElement("div"); visual.className = "split-visual"; const image = document.createElement("img"); image.src = getImageSrc(node.props?.image_src); image.alt = String(node.props?.image_alt || ""); image.addEventListener("error", () => { image.src = fallbackImage; }); visual.appendChild(image); if(node.props?.reverse) grid.append(visual, copy); else grid.append(copy, visual); card.appendChild(grid); section.appendChild(card); return section; }
    case "cta-band": { const section = document.createElement("section"); section.className = "cta-band"; const card = document.createElement("div"); card.className = "cta-card"; const title = document.createElement("h2"); title.className = "cta-title"; title.textContent = String(node.props?.title || "Ready to move faster?"); card.appendChild(title); if(node.props?.description){ const desc = document.createElement("p"); desc.className = "cta-description"; desc.textContent = String(node.props.description); card.appendChild(desc); } const actions = document.createElement("div"); actions.className = "cta-actions"; if(node.props?.primary_cta_label) actions.appendChild(createButton(node.props.primary_cta_label, node.props.primary_cta_route, "button-primary")); if(node.props?.secondary_cta_label) actions.appendChild(createButton(node.props.secondary_cta_label, node.props.secondary_cta_route, "button-secondary")); if(actions.children.length) card.appendChild(actions); section.appendChild(card); return section; }
    case "auth-card": { const section = document.createElement("section"); section.className = "auth-card"; const frame = document.createElement("div"); frame.className = "auth-card-frame auth-grid"; const visual = document.createElement("div"); visual.className = "auth-visual"; const image = document.createElement("img"); image.src = getImageSrc(node.props?.image_src); image.alt = String(node.props?.image_alt || ""); image.addEventListener("error", () => { image.src = fallbackImage; }); visual.appendChild(image); const body = document.createElement("div"); body.className = "auth-body"; const title = document.createElement("h2"); title.className = "auth-title"; title.textContent = String(node.props?.title || "Welcome back"); body.appendChild(title); if(node.props?.description){ const desc = document.createElement("p"); desc.className = "auth-description"; desc.textContent = String(node.props.description); body.appendChild(desc); } (node.children || []).forEach((child) => body.appendChild(renderNode(child, parentFormId))); if(node.props?.footer_text){ const footer = document.createElement("div"); footer.className = "auth-footer"; footer.textContent = String(node.props.footer_text) + " "; if(node.props?.footer_link_label){ const link = document.createElement("button"); link.className = "auth-link"; link.type = "button"; link.textContent = String(node.props.footer_link_label); link.addEventListener("click", () => { if(node.props?.footer_link_route){ currentRoute = String(node.props.footer_link_route); render(); } }); footer.appendChild(link); } body.appendChild(footer); } frame.append(visual, body); section.appendChild(frame); return section; }
    case "modal": { const visible = modalState[node.id]; const placeholder = document.createElement("div"); if(!visible) return placeholder; placeholder.className = "modal"; const card = document.createElement("div"); card.className = "modal-card stack"; (node.children || []).forEach((child) => card.appendChild(renderNode(child, parentFormId))); placeholder.appendChild(card); return placeholder; }
    default: { const fallback = document.createElement("pre"); fallback.className = "text"; fallback.textContent = `[Unsupported component: ${node.type}]`; return fallback; }
  }
}

function renderPager(){ const pager = document.createElement("div"); pager.className = "pager"; appSchema.pages.forEach((page) => { const dot = document.createElement("button"); dot.className = `pager-dot ${page.route === currentRoute ? "is-active" : ""}`; dot.title = page.name; dot.addEventListener("click", () => { currentRoute = page.route; render(); }); pager.appendChild(dot); }); return pager; }
function render(){ root.innerHTML = ""; const page = getCurrentPage(); if(!page){ root.innerHTML = '<div class="empty-state">No renderable page in schema.</div>'; return; } const layout = getLayoutArchetype(page); const shell = document.createElement("div"); shell.className = `app-shell layout-${layout}`; const pageEl = document.createElement("main"); pageEl.className = `page layout-${layout}`; page.components.forEach((node) => pageEl.appendChild(renderNode(node))); shell.appendChild(pageEl); root.appendChild(shell); if((appSchema.pages || []).length > 1){ root.appendChild(renderPager()); } }
render();
""".replace("__IMAGE_PLACEHOLDER__", _image_placeholder_data_uri())


def _build_readme(title: str, prompt: str) -> str:
    return f"""# {title}

This folder is a static export generated by Nano Atoms.

## Files

- `index.html`: entry page
- `src/styles.css`: page styles and theme variables
- `src/schema.js`: generated schema and interaction bundle
- `src/app.js`: runtime renderer

## Original Prompt

{prompt}
"""


def build_project_artifact(
    prompt: str,
    app_schema: dict[str, Any],
    code_bundle: dict[str, Any],
) -> dict[str, Any]:
    title = app_schema.get("title") or "Nano Atoms App"
    package_name = _slugify(title)
    quality_report = app_schema.get("quality_report")

    files = [
        {"path": "README.md", "language": "markdown", "content": _build_readme(title, prompt)},
        {"path": "index.html", "language": "html", "content": _build_index_html(title)},
        {"path": "src/styles.css", "language": "css", "content": _build_styles_css(app_schema)},
        {"path": "src/schema.js", "language": "javascript", "content": _build_schema_js(app_schema, code_bundle)},
        {"path": "src/app.js", "language": "javascript", "content": _build_app_js()},
        {"path": "data/app-schema.json", "language": "json", "content": _json_text(app_schema)},
        {"path": "data/code-bundle.json", "language": "json", "content": _json_text(code_bundle)},
    ]
    if isinstance(quality_report, dict):
        files.append(
            {
                "path": "data/quality-report.json",
                "language": "json",
                "content": _json_text(quality_report),
            }
        )

    return {
        "format": "project_files_v1",
        "title": title,
        "package_name": package_name,
        "entry": "index.html",
        "code_bundle": code_bundle,
        "quality_report": quality_report,
        "files": [
            {**file, "language": file.get("language") or _infer_language(file["path"])}
            for file in files
        ],
    }
