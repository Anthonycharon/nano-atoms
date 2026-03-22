"""Build a human-readable static project export from schema + code bundle."""

from __future__ import annotations

import json
import re
from urllib.parse import quote
from typing import Any


def _slugify(value: str) -> str:
    text = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower())
    return text.strip("-") or "nano-atoms-app"


def _json_text(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


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
    primary = theme.get("primary_color", "#4f46e5")
    secondary = theme.get("secondary_color", "#c7d2fe")
    background = theme.get("background_color", "#ffffff")
    text = theme.get("text_color", "#0f172a")
    radius = theme.get("border_radius", "16px")
    font_family = theme.get("font_family", '"Segoe UI", "PingFang SC", system-ui, sans-serif')

    return f""":root {{
  --color-primary: {primary};
  --color-secondary: {secondary};
  --color-surface: #ffffff;
  --color-page: {background};
  --color-border: #dbe3f0;
  --color-muted: #64748b;
  --color-text: {text};
  --radius: {radius};
  --shadow: 0 18px 40px rgba(15, 23, 42, 0.08);
  --font-sans: {font_family};
}}

* {{
  box-sizing: border-box;
}}

body {{
  margin: 0;
  font-family: var(--font-sans);
  background: linear-gradient(180deg, #f8fbff 0%, var(--color-page) 100%);
  color: var(--color-text);
}}

#app {{
  min-height: 100vh;
}}

.app-shell {{
  min-height: 100vh;
  padding: 32px;
}}

.page {{
  max-width: 1120px;
  margin: 0 auto;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: calc(var(--radius) + 8px);
  box-shadow: var(--shadow);
  padding: 32px;
}}

.stack {{
  display: flex;
  flex-direction: column;
  gap: 16px;
}}

.heading {{
  margin: 0;
  font-size: 2rem;
  line-height: 1.2;
}}

.text {{
  margin: 0;
  color: var(--color-muted);
  line-height: 1.7;
}}

.button {{
  appearance: none;
  border: 0;
  background: var(--color-primary);
  color: white;
  border-radius: var(--radius);
  padding: 12px 18px;
  font: inherit;
  cursor: pointer;
  box-shadow: 0 12px 24px rgba(79, 70, 229, 0.18);
}}

.field,
.form {{
  display: flex;
  flex-direction: column;
  gap: 10px;
}}

.field-label {{
  font-size: 0.95rem;
  color: var(--color-muted);
}}

.input,
.select {{
  width: 100%;
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  padding: 12px 14px;
  font: inherit;
  color: var(--color-text);
  background: #fff;
}}

.card,
.stat-card,
.table-wrap,
.navbar {{
  background: #fff;
  border: 1px solid var(--color-border);
  border-radius: calc(var(--radius) + 4px);
  padding: 20px;
}}

.card-title {{
  margin: 0 0 12px;
  font-size: 1.05rem;
}}

.stat-label {{
  color: var(--color-muted);
  margin: 0 0 4px;
}}

.stat-value {{
  margin: 0;
  font-size: 2rem;
  font-weight: 700;
}}

.stat-change {{
  margin-top: 8px;
  color: #16a34a;
  font-size: 0.85rem;
}}

.table {{
  width: 100%;
  border-collapse: collapse;
}}

.table th,
.table td {{
  border-bottom: 1px solid var(--color-border);
  padding: 12px 10px;
  text-align: left;
}}

.table th {{
  color: var(--color-muted);
  font-weight: 600;
}}

.navbar {{
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}}

.navbar-links {{
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}}

.navbar-link {{
  color: var(--color-muted);
  text-decoration: none;
}}

.tag {{
  display: inline-flex;
  align-items: center;
  padding: 6px 10px;
  border-radius: 999px;
  background: #eef2ff;
  color: #4338ca;
  font-size: 0.85rem;
}}

.image {{
  max-width: 100%;
  border-radius: calc(var(--radius) + 2px);
}}

.pager {{
  position: fixed;
  bottom: 24px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  gap: 8px;
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid var(--color-border);
  border-radius: 999px;
  padding: 8px 10px;
  box-shadow: var(--shadow);
}}

.pager-dot {{
  width: 10px;
  height: 10px;
  border: 0;
  border-radius: 999px;
  background: #cbd5e1;
  cursor: pointer;
}}

.pager-dot.is-active {{
  width: 28px;
  background: var(--color-primary);
}}

.toast {{
  position: fixed;
  right: 24px;
  bottom: 24px;
  padding: 12px 16px;
  background: #16a34a;
  color: #fff;
  border-radius: 14px;
  box-shadow: var(--shadow);
}}

.modal {{
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.42);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}}

.modal-card {{
  width: min(560px, 100%);
  background: white;
  border-radius: calc(var(--radius) + 8px);
  padding: 24px;
  box-shadow: var(--shadow);
}}

.empty-state {{
  max-width: 720px;
  margin: 64px auto;
  background: white;
  border: 1px dashed var(--color-border);
  border-radius: calc(var(--radius) + 8px);
  padding: 32px;
  text-align: center;
  color: var(--color-muted);
}}

@media (max-width: 768px) {{
  .app-shell {{
    padding: 16px;
  }}

  .page {{
    padding: 20px;
  }}
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

function getCurrentPage() {
  return appSchema.pages.find((page) => page.route === currentRoute) || appSchema.pages?.[0];
}

function getText(node, fallback = "") {
  return String(node?.props?.text ?? node?.props?.children ?? node?.props?.label ?? fallback);
}

function getFormId(node, parentFormId) {
  return node?.props?.form_id || parentFormId || node?.id;
}

function showToast(message) {
  const existing = document.querySelector(".toast");
  if (existing) existing.remove();
  const toast = document.createElement("div");
  toast.className = "toast";
  toast.textContent = message;
  document.body.appendChild(toast);
  window.clearTimeout(toastTimer);
  toastTimer = window.setTimeout(() => toast.remove(), 2200);
}

function followTransitions(triggerId) {
  const next = codeBundle.page_transitions?.find(
    (item) => item.trigger_component === triggerId
  );
  if (next) {
    const target = appSchema.pages.find((page) => page.id === next.to_page);
    if (target) {
      currentRoute = target.route;
      render();
    }
  }
}

function submitForm(formId) {
  const handler = codeBundle.form_handlers?.find((item) => item.form_id === formId);
  if (handler?.submit_action === "save_local") {
    showToast("Form saved");
  } else {
    showToast("Form submitted");
  }
  followTransitions(formId);
}

function handleAction(action, fallbackId) {
  if (!action) return;
  if (action.type === "navigate" && action.payload?.route) {
    currentRoute = action.payload.route;
    render();
    return;
  }
  if (action.type === "submit_form") {
    submitForm(action.payload?.form_id || fallbackId);
    return;
  }
  if (action.type === "set_value" && action.payload?.key) {
    state[action.payload.key] = action.payload.value;
    render();
    return;
  }
  if (action.type === "open_modal") {
    modalState[action.payload?.modal_id || fallbackId] = true;
    render();
    return;
  }
  if (action.type === "close_modal") {
    modalState[action.payload?.modal_id || fallbackId] = false;
    render();
  }
}

function createFieldWrapper(labelText) {
  const wrapper = document.createElement("div");
  wrapper.className = "field";
  if (labelText) {
    const label = document.createElement("label");
    label.className = "field-label";
    label.textContent = labelText;
    wrapper.appendChild(label);
  }
  return wrapper;
}

function renderNode(node, parentFormId) {
  switch (node.type) {
    case "heading": {
      const el = document.createElement("h2");
      el.className = "heading";
      el.textContent = getText(node, "Heading");
      return el;
    }
    case "text": {
      const el = document.createElement("p");
      el.className = "text";
      el.textContent = getText(node);
      return el;
    }
    case "button": {
      const button = document.createElement("button");
      button.className = "button";
      button.type = "button";
      button.textContent = getText(node, "Button");
      button.addEventListener("click", () => {
        (node.actions || []).forEach((action) => handleAction(action, parentFormId || node.id));
      });
      return button;
    }
    case "input": {
      const formId = getFormId(node, parentFormId);
      const fieldName = node.props?.name || node.id;
      const wrapper = createFieldWrapper(node.props?.label);
      const input = document.createElement("input");
      input.className = "input";
      input.type = String(node.props?.type || "text");
      input.placeholder = String(node.props?.placeholder || "");
      input.value = formData[formId]?.[fieldName] || "";
      input.addEventListener("input", (event) => {
        formData[formId] = formData[formId] || {};
        formData[formId][fieldName] = event.target.value;
      });
      wrapper.appendChild(input);
      return wrapper;
    }
    case "select": {
      const formId = getFormId(node, parentFormId);
      const fieldName = node.props?.name || node.id;
      const wrapper = createFieldWrapper(node.props?.label);
      const select = document.createElement("select");
      select.className = "select";
      const placeholder = document.createElement("option");
      placeholder.value = "";
      placeholder.textContent = "Select";
      select.appendChild(placeholder);
      const options = Array.isArray(node.props?.options) ? node.props.options : [];
      options.forEach((value) => {
        const option = document.createElement("option");
        option.value = String(value);
        option.textContent = String(value);
        select.appendChild(option);
      });
      select.value = formData[formId]?.[fieldName] || "";
      select.addEventListener("change", (event) => {
        formData[formId] = formData[formId] || {};
        formData[formId][fieldName] = event.target.value;
      });
      wrapper.appendChild(select);
      return wrapper;
    }
    case "form": {
      const form = document.createElement("form");
      form.className = "form";
      form.addEventListener("submit", (event) => {
        event.preventDefault();
        submitForm(node.id);
      });
      (node.children || []).forEach((child) => {
        form.appendChild(renderNode(child, node.id));
      });
      return form;
    }
    case "card": {
      const card = document.createElement("section");
      card.className = "card stack";
      if (node.props?.title) {
        const title = document.createElement("h3");
        title.className = "card-title";
        title.textContent = String(node.props.title);
        card.appendChild(title);
      }
      if (Array.isArray(node.children) && node.children.length > 0) {
        node.children.forEach((child) => card.appendChild(renderNode(child, parentFormId)));
      } else if (node.props?.content) {
        const text = document.createElement("p");
        text.className = "text";
        text.textContent = String(node.props.content);
        card.appendChild(text);
      }
      return card;
    }
    case "stat-card": {
      const card = document.createElement("section");
      card.className = "stat-card";
      card.innerHTML = `
        <p class="stat-label">${String(node.props?.label || "Metric")}</p>
        <p class="stat-value">${String(node.props?.value || "0")}</p>
        ${node.props?.change ? `<p class="stat-change">${String(node.props.change)}</p>` : ""}
      `;
      return card;
    }
    case "table": {
      const wrap = document.createElement("div");
      wrap.className = "table-wrap";
      const table = document.createElement("table");
      table.className = "table";
      const columns = Array.isArray(node.props?.columns) ? node.props.columns : [];
      const rows = Array.isArray(node.props?.rows) ? node.props.rows : [];
      table.innerHTML = `
        <thead>
          <tr>${columns.map((column) => `<th>${String(column)}</th>`).join("")}</tr>
        </thead>
        <tbody>
          ${rows
            .map(
              (row) => `<tr>${columns
                .map((column) => `<td>${String(row?.[column] ?? "")}</td>`)
                .join("")}</tr>`
            )
            .join("")}
        </tbody>
      `;
      wrap.appendChild(table);
      return wrap;
    }
    case "navbar": {
      const nav = document.createElement("nav");
      nav.className = "navbar";
      const title = document.createElement("strong");
      title.textContent = String(node.props?.title || appSchema.title || "App");
      nav.appendChild(title);
      const links = document.createElement("div");
      links.className = "navbar-links";
      const items = Array.isArray(node.props?.links) ? node.props.links : [];
      items.forEach((item) => {
        const link = document.createElement("a");
        link.className = "navbar-link";
        link.href = "#";
        link.textContent = String(item?.label || item?.text || "Link");
        link.addEventListener("click", (event) => {
          event.preventDefault();
          if (item?.route) {
            currentRoute = item.route;
            render();
          }
        });
        links.appendChild(link);
      });
      nav.appendChild(links);
      return nav;
    }
    case "tag": {
      const tag = document.createElement("span");
      tag.className = "tag";
      tag.textContent = getText(node, "Tag");
      return tag;
    }
    case "image": {
      const image = document.createElement("img");
      image.className = "image";
      image.src = String(node.props?.src || fallbackImage);
      image.alt = String(node.props?.alt || getText(node, "image"));
      image.addEventListener("error", () => {
        image.src = fallbackImage;
      });
      return image;
    }
    case "modal": {
      const visible = modalState[node.id];
      const placeholder = document.createElement("div");
      if (!visible) return placeholder;
      placeholder.className = "modal";
      const card = document.createElement("div");
      card.className = "modal-card stack";
      (node.children || []).forEach((child) => card.appendChild(renderNode(child, parentFormId)));
      placeholder.appendChild(card);
      return placeholder;
    }
    default: {
      const fallback = document.createElement("pre");
      fallback.className = "text";
      fallback.textContent = `[Unsupported component: ${node.type}]`;
      return fallback;
    }
  }
}

function renderPager() {
  const pager = document.createElement("div");
  pager.className = "pager";
  appSchema.pages.forEach((page) => {
    const dot = document.createElement("button");
    dot.className = `pager-dot ${page.route === currentRoute ? "is-active" : ""}`;
    dot.title = page.name;
    dot.addEventListener("click", () => {
      currentRoute = page.route;
      render();
    });
    pager.appendChild(dot);
  });
  return pager;
}

function render() {
  root.innerHTML = "";
  const page = getCurrentPage();
  if (!page) {
    root.innerHTML = '<div class="empty-state">No renderable page in schema.</div>';
    return;
  }

  const shell = document.createElement("div");
  shell.className = "app-shell";
  const pageEl = document.createElement("main");
  pageEl.className = "page stack";
  page.components.forEach((node) => pageEl.appendChild(renderNode(node)));
  shell.appendChild(pageEl);
  root.appendChild(shell);

  if ((appSchema.pages || []).length > 1) {
    root.appendChild(renderPager());
  }
}

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

## Notes

- The export is derived from the platform's structured schema and interaction bundle.
- It mirrors the generated app as plain HTML, CSS, and JavaScript for inspection and handoff.
"""


def build_project_artifact(
    prompt: str,
    app_schema: dict[str, Any],
    code_bundle: dict[str, Any],
) -> dict[str, Any]:
    title = app_schema.get("title") or "Nano Atoms App"
    package_name = _slugify(title)

    files = [
        {
            "path": "README.md",
            "language": "markdown",
            "content": _build_readme(title, prompt),
        },
        {
            "path": "index.html",
            "language": "html",
            "content": _build_index_html(title),
        },
        {
            "path": "src/styles.css",
            "language": "css",
            "content": _build_styles_css(app_schema),
        },
        {
            "path": "src/schema.js",
            "language": "javascript",
            "content": _build_schema_js(app_schema, code_bundle),
        },
        {
            "path": "src/app.js",
            "language": "javascript",
            "content": _build_app_js(),
        },
        {
            "path": "data/app-schema.json",
            "language": "json",
            "content": _json_text(app_schema),
        },
        {
            "path": "data/code-bundle.json",
            "language": "json",
            "content": _json_text(code_bundle),
        },
    ]

    return {
        "format": "project_files_v1",
        "title": title,
        "package_name": package_name,
        "entry": "index.html",
        "code_bundle": code_bundle,
        "files": [
            {
                **file,
                "language": file.get("language") or _infer_language(file["path"]),
            }
            for file in files
        ],
    }
