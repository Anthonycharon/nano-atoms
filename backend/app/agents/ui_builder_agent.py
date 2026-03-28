"""UI builder agent: generate the visual theme for the current schema."""

import json

from langchain_core.messages import HumanMessage, SystemMessage

from .utils import build_app_context, extract_json, make_llm, notify_agent


SYSTEM_PROMPT = """You are a senior UI designer focused on first-pass quality.
Return one JSON object only, with no markdown or commentary.

Output format:
{
  "theme_mode": "light | dark | mixed",
  "primary_color": "#6366f1",
  "secondary_color": "#a5b4fc",
  "background_color": "#ffffff",
  "text_color": "#111827",
  "surface_color": "rgba(...) or #hex",
  "surface_text_color": "#111827",
  "border_color": "rgba(...) or #hex",
  "muted_text_color": "rgba(...) or #hex",
  "input_background": "rgba(...) or #hex",
  "subtle_surface_color": "rgba(...) or #hex",
  "button_text_color": "#ffffff",
  "page_background": "valid CSS color or gradient",
  "font_family": "\"Plus Jakarta Sans\", sans-serif",
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
- Respect the user's explicit visual direction first. If they ask for black, dark, monochrome, neon, brutalist, luxury, glass, or playful, keep that direction.
- Do not default every request to a bright SaaS palette.
- Make the visual system reinforce the chosen layout archetype instead of forcing every app into the same neutral SaaS treatment.
- Use theme tokens that make both the preview renderer and exported code feel consistent.
- Keep contrast readable in desktop and mobile previews.
- Make auth, landing, showcase, and content pages noticeably more expressive when the brief asks for it."""


async def run_ui_builder_agent(state: dict) -> dict:
    cb = state.get("ws_callback")
    await notify_agent(cb, "ui_builder", "running")

    try:
        app_schema = state.get("app_schema")
        site_plan = state.get("site_plan")
        if not isinstance(app_schema, dict) or not app_schema.get("pages"):
            raise ValueError("UI Builder Agent requires a valid compatibility schema")
        if not isinstance(site_plan, dict) or not site_plan.get("pages"):
            raise ValueError("UI Builder Agent requires a valid site plan")

        llm = make_llm(temperature=0.45)
        app_context = build_app_context(state.get("app_type"))
        design_brief = state.get("design_brief")
        prd_json = state.get("prd_json")
        page_names = [page["name"] for page in site_plan.get("pages", []) if isinstance(page, dict) and page.get("name")]
        response = await llm.ainvoke(
            [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(
                    content=(
                        f"{app_context}\n"
                        "Site plan summary:\n"
                        f"{json.dumps({'title': site_plan.get('title'), 'pages': page_names, 'layout_archetype': site_plan.get('layout_archetype')}, ensure_ascii=False)}\n\n"
                        "PRD JSON:\n"
                        f"{json.dumps(prd_json or {}, ensure_ascii=False)}\n\n"
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
            f"mode {ui_theme.get('theme_mode', 'auto')}, "
            f"canvas {ui_theme.get('canvas_mode', 'balanced')}"
        )

        await notify_agent(cb, "ui_builder", "done", summary)
        return {**state, "ui_theme": ui_theme}

    except Exception as exc:
        message = f"UI Builder Agent failed: {exc}"
        await notify_agent(cb, "ui_builder", "error", message)
        return {**state, "errors": state.get("errors", []) + [message]}
