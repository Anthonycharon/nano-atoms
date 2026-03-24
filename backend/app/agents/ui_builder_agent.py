"""UI builder agent: generate the visual theme for the current schema."""

import json

from langchain_core.messages import HumanMessage, SystemMessage

from .utils import build_app_context, extract_json, make_llm, notify_agent


SYSTEM_PROMPT = """You are a senior UI designer focused on first-pass quality.
Return one JSON object only, with no markdown or commentary.

Output format:
{
  "primary_color": "#6366f1",
  "secondary_color": "#a5b4fc",
  "background_color": "#ffffff",
  "text_color": "#111827",
  "font_family": "\"Plus Jakarta Sans\", \"Inter\", sans-serif",
  "border_radius": "18px",
  "spacing_unit": 5,
  "canvas_mode": "soft | contrast | editorial | spotlight",
  "surface_mode": "flat | layered | glass",
  "density": "airy | balanced | compact",
  "accent_style": "solid | gradient",
  "shadow_strength": "soft | medium | strong",
  "component_styles": {
    "component_id": {
      "className": "extra Tailwind className"
    }
  }
}

Rules:
- Match the design brief rather than outputting a generic admin palette.
- Favor bright, polished, product-ready themes.
- Use typography and spacing choices that strengthen hierarchy.
- Push the visual direction further for marketing, showcase, content, and auth experiences.
- The theme must remain readable and production-looking in both desktop and mobile previews."""


async def run_ui_builder_agent(state: dict) -> dict:
    cb = state.get("ws_callback")
    await notify_agent(cb, "ui_builder", "running")

    try:
        app_schema = state.get("app_schema")
        if not isinstance(app_schema, dict) or not app_schema.get("pages"):
            raise ValueError("UI Builder Agent requires a valid app schema")

        llm = make_llm(temperature=0.4)
        app_context = build_app_context(state.get("app_type"))
        design_brief = state.get("design_brief")
        page_names = [page["name"] for page in app_schema.get("pages", [])]
        response = await llm.ainvoke(
            [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(
                    content=(
                        f"{app_context}\n"
                        "Schema summary:\n"
                        f"{json.dumps({'title': app_schema.get('title'), 'pages': page_names}, ensure_ascii=False)}\n\n"
                        "Design brief:\n"
                        f"{json.dumps(design_brief or {}, ensure_ascii=False)}"
                    )
                ),
            ]
        )

        ui_theme = extract_json(response.content)
        if not isinstance(ui_theme, dict):
            raise ValueError("UI Builder Agent expected a JSON object response")
        summary = (
            f"Primary {ui_theme.get('primary_color', 'N/A')}, "
            f"canvas {ui_theme.get('canvas_mode', 'balanced')}"
        )

        await notify_agent(cb, "ui_builder", "done", summary)
        return {**state, "ui_theme": ui_theme}

    except Exception as exc:
        message = f"UI Builder Agent failed: {exc}"
        await notify_agent(cb, "ui_builder", "error", message)
        return {**state, "errors": state.get("errors", []) + [message]}
