"""Design Director agent: derive a visual/experience brief that lifts first-pass quality."""

import json

from langchain_core.messages import HumanMessage, SystemMessage

from .utils import extract_json, make_llm, notify_agent


SYSTEM_PROMPT = """You are a senior design director for AI-generated products.
Return one JSON object only, with no markdown or commentary.

Output format:
{
  "experience_goal": "short statement of the intended user feeling and outcome",
  "primary_user_mindset": "who the page is speaking to right now",
  "visual_direction": "short art direction phrase",
  "layout_archetype": "marketing | editorial | dashboard | centered-auth | workspace | immersive | auto",
  "theme_mode": "light | dark | mixed | auto",
  "color_story": "short phrase describing the palette and contrast",
  "layout_density": "airy | balanced | compact",
  "tone_keywords": ["keyword", "keyword"],
  "style_constraints": ["explicit visual rules to preserve"],
  "section_recommendations": ["hero", "feature-grid"],
  "quality_checklist": ["specific quality rule", "specific quality rule"],
  "avoid_patterns": ["pattern to avoid", "pattern to avoid"]
}

Rules:
- Respect explicit visual directions from the user. If they ask for black, dark, monochrome, glass, neon, brutalist, playful, or editorial, preserve that direction.
- Do not collapse every request into the same bright SaaS style.
- Choose one layout archetype that matches the job of the first page. Blogs and reading-focused products should lean editorial. Marketing and launch pages should lean marketing or immersive. Internal tools, assistants, and operator consoles should lean workspace or dashboard. Only use centered-auth when the main page is truly a sign-in or sign-up flow.
- Recommend sections that make the generated result look intentional and product-ready.
- Keep the brief practical so downstream agents can use it immediately."""


async def run_design_director_agent(state: dict) -> dict:
    cb = state.get("ws_callback")
    await notify_agent(cb, "design_director", "running")

    try:
        prd_json = state.get("prd_json")
        if not isinstance(prd_json, dict) or not prd_json:
            raise ValueError("Design Director requires a valid PRD payload")

        llm = make_llm(temperature=0.35)
        response = await llm.ainvoke(
            [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=f"PRD JSON:\n{json.dumps(prd_json, ensure_ascii=False)}"),
            ]
        )

        design_brief = extract_json(response.content)
        if not isinstance(design_brief, dict):
            raise ValueError("Design Director expected a JSON object response")

        sections = design_brief.get("section_recommendations", [])
        summary = (
            f"{design_brief.get('visual_direction', 'Defined visual direction')}; "
            f"{len(sections) if isinstance(sections, list) else 0} recommended section pattern(s)"
        )
        await notify_agent(cb, "design_director", "done", summary)
        return {**state, "design_brief": design_brief}

    except Exception as exc:
        message = f"Design Director failed: {exc}"
        await notify_agent(cb, "design_director", "error", message)
        return {**state, "errors": state.get("errors", []) + [message]}
