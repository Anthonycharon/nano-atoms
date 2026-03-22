"""Architect agent: turn PRD data into a renderable app schema."""

import json

from langchain_core.messages import HumanMessage, SystemMessage

from .utils import build_app_context, extract_json, make_llm, notify_agent


SYSTEM_PROMPT = """You are a senior application architect.
Return a single JSON object only, with no markdown or commentary.

Schema format:
{
  "app_id": "unique_app_id",
  "title": "Application title",
  "app_type": "application shape, such as dashboard, tool, admin, internal, landing, marketing, blog, ecommerce",
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

Supported component types: text, heading, image, button, input, select, table, card, form, modal, tag, navbar, stat-card
Supported action types: navigate, submit_form, open_modal, close_modal, set_value

Requirements:
- Infer app_type from the requirement. Do not force it into a fixed shortlist.
- Output a complete schema that can be rendered directly.
- When the request implies a visual or promotional experience, include image components for hero sections, covers, product cards, galleries, or featured content.
- For dashboards and internal tools, only include image components when they clearly add value.
- Prefer realistic page structures over placeholder-heavy layouts."""


async def run_architect_agent(state: dict) -> dict:
    cb = state.get("ws_callback")
    await notify_agent(cb, "architect", "running")

    try:
        llm = make_llm(temperature=0.2)
        prd_json = state.get("prd_json")
        if not isinstance(prd_json, dict) or not prd_json:
            raise ValueError("Architect Agent requires a valid PRD payload")

        app_context = build_app_context(state.get("app_type"))
        response = await llm.ainvoke(
            [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(
                    content=f"{app_context}\nPRD JSON:\n{json.dumps(prd_json, ensure_ascii=False)}"
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
