"""Architect agent: turn PRD data into a renderable app schema."""

import json

from langchain_core.messages import HumanMessage, SystemMessage

from .utils import build_app_context, extract_json, make_llm, notify_agent


SYSTEM_PROMPT = """You are a senior application architect focused on first-pass quality.
Return a single JSON object only, with no markdown or commentary.

Schema format:
{
  "app_id": "unique_app_id",
  "title": "Application title",
  "app_type": "application shape such as dashboard, tool, admin, internal, landing, marketing, blog, ecommerce, auth",
  "pages": [
    {
      "id": "page_id",
      "name": "Page name",
      "route": "/route",
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
  ],
  "navigation": [{"label": "Link label", "route": "/route"}],
  "data_models": [{"name": "ModelName", "fields": ["field names"]}]
}

Supported component types:
- Primitive: text, heading, image, button, input, select, table, card, form, modal, tag, navbar, stat-card
- Composite quality blocks: hero, feature-grid, stats-band, split-section, cta-band, auth-card

Composite block expectations:
- hero: title, description, eyebrow, primary_cta_label, primary_cta_route, secondary_cta_label, secondary_cta_route, image_src, image_alt, stats
- feature-grid: title, description, columns, items[{title, description, badge, icon}]
- stats-band: items[{label, value, caption}]
- split-section: eyebrow, title, description, bullets, image_src, image_alt, primary_cta_label, primary_cta_route, secondary_cta_label, secondary_cta_route, reverse
- cta-band: title, description, primary_cta_label, primary_cta_route, secondary_cta_label, secondary_cta_route
- auth-card: title, description, aside_title, aside_text, image_src, image_alt, footer_text, footer_link_label, footer_link_route; it may contain form/input/button children

Supported action types: navigate, submit_form, open_modal, close_modal, set_value

Requirements:
- Infer app_type from the requirement. Do not force it into a fixed shortlist.
- Output a complete schema that can be rendered directly.
- Use composite quality blocks when they improve clarity and polish.
- Prefer fewer, stronger sections over many weak placeholder sections.
- For landing, showcase, campaign, content, and auth flows, avoid flat card stacks as the main structure.
- For dashboards and internal tools, use clear hierarchy, summary bands, filters, and focused content groupings.
- Include image-driven sections only when they add real value.
- All copy should feel specific, product-like, and ready for a believable first preview."""


async def run_architect_agent(state: dict) -> dict:
    cb = state.get("ws_callback")
    await notify_agent(cb, "architect", "running")

    try:
        llm = make_llm(temperature=0.2)
        prd_json = state.get("prd_json")
        if not isinstance(prd_json, dict) or not prd_json:
            raise ValueError("Architect Agent requires a valid PRD payload")

        app_context = build_app_context(state.get("app_type"))
        design_brief = state.get("design_brief")
        response = await llm.ainvoke(
            [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(
                    content=(
                        f"{app_context}\n"
                        f"PRD JSON:\n{json.dumps(prd_json, ensure_ascii=False)}\n\n"
                        f"Design brief:\n{json.dumps(design_brief or {}, ensure_ascii=False)}"
                    )
                ),
            ]
        )

        app_schema = extract_json(response.content)
        if not isinstance(app_schema, dict):
            raise ValueError("Architect Agent expected a JSON object response")

        page_count = len(app_schema.get("pages", []))
        component_count = sum(
            len(page.get("components", []))
            for page in app_schema.get("pages", [])
            if isinstance(page, dict)
        )
        summary = f"Generated {page_count} page(s) and {component_count} component(s)"

        await notify_agent(cb, "architect", "done", summary)
        return {**state, "app_schema": app_schema}

    except Exception as exc:
        message = f"Architect Agent failed: {exc}"
        await notify_agent(cb, "architect", "error", message)
        return {**state, "errors": state.get("errors", []) + [message]}
